from datetime import datetime
import pytz

# Use consistent timezone across the app
EASTERN = pytz.timezone('America/New_York')


def get_now():
    """Return the current datetime in US/Eastern timezone."""
    return datetime.now(EASTERN)
