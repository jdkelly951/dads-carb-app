import os
import uuid
import requests
from datetime import datetime, timedelta, date
from flask import Blueprint, request, redirect, url_for, render_template, make_response
import pytz
from .utils import get_now
from .db import (
    fetch_logs_for_date,
    insert_log,
    delete_latest_for_date,
    delete_by_index,
    clear_day as clear_day_db,
    list_dates,
    get_totals_for_dates,
    get_top_foods,
)

main_routes = Blueprint("main_routes", __name__)

API_NINJAS_ENDPOINT = "https://api.api-ninjas.com/v1/nutrition"
EASTERN = pytz.timezone('America/New_York')


def get_user_id():
    """Retrieve or assign a unique user ID using browser cookies."""
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id


@main_routes.route('/', methods=['GET', 'POST'])
@main_routes.route('/day/<date_str>', methods=['GET'])
def index(date_str=None):
    """
    Main entry point for logging and viewing carb data.
    - Handles food entry via POST requests.
    - Displays log for the selected or current date.
    """
    API_NINJAS_KEY = os.environ.get("API_NINJAS_KEY")
    api_configured = bool(API_NINJAS_KEY)
    user_id = get_user_id()
    error_message = None
    # Check DB availability (friendly UI if missing)
    db_error = None
    try:
        # noop query for health via listing dates
        list_dates(user_id)
    except Exception as e:
        db_error = str(e)

    # Determine which date to display
    if date_str is None:
        display_date = get_now().strftime('%Y-%m-%d')
        viewing_today = True
    else:
        display_date = date_str
        viewing_today = (display_date == get_now().strftime('%Y-%m-%d'))

    if request.method == 'POST':
        # Redirect POSTs to another day to the main page (only today is editable)
        if not viewing_today:
            return redirect(url_for('main_routes.index'))

        form_mode = request.form.get('mode', 'auto')

        # Manual entry fallback (doesn't need Nutritionix keys)
        if form_mode == 'manual':
            food_name = request.form.get('manual_food')
            carbs = request.form.get('manual_carbs')
            serving_qty = request.form.get('manual_serving_qty') or None
            serving_unit = request.form.get('manual_serving_unit') or None

            try:
                carbs_val = float(carbs) if carbs not in (None, "") else None
            except ValueError:
                carbs_val = None

            if not food_name or carbs_val is None:
                error_message = "Please provide a food name and carb grams."
            else:
                today = get_now().date()
                insert_log(user_id, today, food_name, carbs_val, float(serving_qty) if serving_qty else None, serving_unit)
        else:
            query = request.form.get('food_query')
            if query:
                try:
                    if not api_configured:
                        raise ValueError("API key missing — use manual entry below.")

                    response = requests.get(
                        API_NINJAS_ENDPOINT,
                        headers={'X-Api-Key': API_NINJAS_KEY},
                        params={'query': query},
                        timeout=8
                    )
                    response.raise_for_status()
                    result = response.json()

                    foods = result.get('items') or []
                    if not foods:
                        error_message = "Couldn't find that food. Please try again."
                    else:
                        today = get_now().date()

                        for item in foods:
                            carbs_val = item.get('carbohydrates_total_g') or item.get('carbs_total_g') or 0
                            insert_log(
                                user_id,
                                today,
                                item.get('name'),
                                carbs_val,
                                item.get('serving_size_g'),
                                'g'
                            )

                except requests.exceptions.HTTPError as e:
                    if e.response is not None:
                        try:
                            resp_msg = e.response.json()
                        except Exception:
                            resp_msg = e.response.text[:200]
                        error_message = f"Nutrition API error {e.response.status_code}: {resp_msg}"
                    else:
                        error_message = "Nutrition API HTTP error."
                except requests.exceptions.RequestException:
                    error_message = "Could not connect to nutrition service."
                except ValueError as e:
                    error_message = str(e)

    # Get food log and carb totals for the displayed date
    display_date_obj = datetime.strptime(display_date, '%Y-%m-%d').date()
    food_log_for_display_date = []
    total_carbs = 0
    try:
        food_log_for_display_date = fetch_logs_for_date(user_id, display_date_obj)
        total_carbs = sum(float(item['carbs']) for item in food_log_for_display_date)
    except Exception as e:
        if not db_error:
            db_error = str(e)

    # Calculate 7-day average carbs
    past_7_dates = [
        (get_now() - timedelta(days=i)).date()
        for i in range(7)
    ]
    past_7_str = [d.isoformat() for d in past_7_dates]
    totals_map = get_totals_for_dates(user_id, past_7_dates) if not db_error else {}
    carbs_last_7_days = [totals_map.get(d, 0) for d in past_7_str]
    average_7_days = round(sum(carbs_last_7_days) / 7, 1)

    # Format display date nicely
    display_date_formatted = display_date_obj.strftime('%A, %B %d, %Y')

    suggestions = get_top_foods(user_id) if not db_error else []

    # Render the main page and set persistent cookie
    response = make_response(render_template(
        'index.html',
        food_log=food_log_for_display_date,
        total_carbs=total_carbs,
        average_7_days=average_7_days,
        display_date_str=display_date_formatted,
        display_date_raw=display_date,
        viewing_today=viewing_today,
        error=error_message,
        suggestions=suggestions,
        api_configured=api_configured,
        db_error=db_error
    ))
    response.set_cookie('user_id', user_id, max_age=60 * 60 * 24 * 365)
    return response


@main_routes.route('/history')
def history():
    """
    View a list of all tracked dates for the current user.
    """
    user_id = get_user_id()
    try:
        sorted_dates = list_dates(user_id)
    except Exception:
        sorted_dates = []
    response = make_response(render_template('history.html', dates=sorted_dates))
    response.set_cookie('user_id', user_id, max_age=60 * 60 * 24 * 365)
    return response


@main_routes.route('/undo')
def undo():
    """
    Remove the most recent entry from today's food log.
    """
    user_id = get_user_id()
    today = get_now().date()
    delete_latest_for_date(user_id, today)
    return redirect(url_for('main_routes.index'))


@main_routes.route('/clear/<date_str>')
def clear_day(date_str):
    """
    Completely delete all food logs for a specific date.
    """
    user_id = get_user_id()
    try:
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        clear_day_db(user_id, entry_date)
    except Exception:
        pass
    return redirect(url_for('main_routes.history'))


@main_routes.route('/delete/<date_str>/<int:item_index>')
def delete_item(date_str, item_index):
    """
    Delete a single item from the food log of a given date.
    """
    user_id = get_user_id()
    try:
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        delete_by_index(user_id, entry_date, item_index)
    except Exception:
        pass
    return redirect(url_for('main_routes.index', date_str=date_str))
