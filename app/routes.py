import os
import json
import uuid
import requests
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, render_template, make_response
import pytz
from .utils import load_data, save_data, get_suggestions, get_now

main_routes = Blueprint("main_routes", __name__)

NUTRITIONIX_ENDPOINT = "https://trackapi.nutritionix.com/v2/natural/nutrients"
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
    APP_ID = os.environ.get("NUTRITIONIX_APP_ID")
    API_KEY = os.environ.get("NUTRITIONIX_API_KEY")
    HEADERS = {'x-app-id': APP_ID, 'x-app-key': API_KEY}
    api_configured = bool(APP_ID and API_KEY)
    user_id = get_user_id()
    error_message = None
    all_data = load_data(user_id)

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
                today_str = get_now().strftime('%Y-%m-%d')
                log_for_today = all_data.get(today_str, [])
                log_for_today.append({
                    'food': food_name,
                    'carbs': carbs_val,
                    'serving_qty': float(serving_qty) if serving_qty else None,
                    'serving_unit': serving_unit
                })
                all_data[today_str] = log_for_today
                save_data(user_id, all_data)
        else:
            query = request.form.get('food_query')
            if query:
                try:
                    if not api_configured:
                        raise ValueError("Nutritionix keys missing — use manual entry below.")

                    response = requests.post(NUTRITIONIX_ENDPOINT, headers=HEADERS, json={'query': query})
                    response.raise_for_status()
                    result = response.json()

                    if not result.get('foods'):
                        error_message = "Couldn't find that food. Please try again."
                    else:
                        today_str = get_now().strftime('%Y-%m-%d')
                        log_for_today = all_data.get(today_str, [])

                        # Extract carb data for each food item returned
                        for item in result.get('foods', []):
                            log_for_today.append({
                                'food': item.get('food_name'),
                                'carbs': item.get('nf_total_carbohydrate', 0),
                                'serving_qty': item.get('serving_qty'),
                                'serving_unit': item.get('serving_unit')
                            })

                        all_data[today_str] = log_for_today
                        save_data(user_id, all_data)

                except requests.exceptions.RequestException:
                    error_message = "Could not connect to nutrition service."
                except ValueError as e:
                    error_message = str(e)

    # Get food log and carb totals for the displayed date
    food_log_for_display_date = all_data.get(display_date, [])
    total_carbs = sum(item['carbs'] for item in food_log_for_display_date)

    # Calculate 7-day average carbs
    past_7_dates = [
        (get_now() - timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(7)
    ]
    carbs_last_7_days = [
        sum(item['carbs'] for item in all_data.get(date, []))
        for date in past_7_dates
    ]
    average_7_days = round(sum(carbs_last_7_days) / 7, 1)

    # Format display date nicely
    display_date_obj = datetime.strptime(display_date, '%Y-%m-%d')
    display_date_formatted = display_date_obj.strftime('%A, %B %d, %Y')

    suggestions = get_suggestions(all_data)

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
        api_configured=api_configured
    ))
    response.set_cookie('user_id', user_id, max_age=60 * 60 * 24 * 365)
    return response


@main_routes.route('/history')
def history():
    """
    View a list of all tracked dates for the current user.
    """
    user_id = get_user_id()
    all_data = load_data(user_id)
    sorted_dates = sorted(all_data.keys(), reverse=True)
    response = make_response(render_template('history.html', dates=sorted_dates))
    response.set_cookie('user_id', user_id, max_age=60 * 60 * 24 * 365)
    return response


@main_routes.route('/undo')
def undo():
    """
    Remove the most recent entry from today's food log.
    """
    user_id = get_user_id()
    all_data = load_data(user_id)
    today_str = get_now().strftime('%Y-%m-%d')
    if today_str in all_data and all_data[today_str]:
        all_data[today_str].pop()
        save_data(user_id, all_data)
    return redirect(url_for('main_routes.index'))


@main_routes.route('/clear/<date_str>')
def clear_day(date_str):
    """
    Completely delete all food logs for a specific date.
    """
    user_id = get_user_id()
    all_data = load_data(user_id)
    if date_str in all_data:
        del all_data[date_str]
        save_data(user_id, all_data)
    return redirect(url_for('main_routes.history'))


@main_routes.route('/delete/<date_str>/<int:item_index>')
def delete_item(date_str, item_index):
    """
    Delete a single item from the food log of a given date.
    """
    user_id = get_user_id()
    all_data = load_data(user_id)
    if date_str in all_data and 0 <= item_index < len(all_data[date_str]):
        all_data[date_str].pop(item_index)
        save_data(user_id, all_data)
    return redirect(url_for('main_routes.index', date_str=date_str))
