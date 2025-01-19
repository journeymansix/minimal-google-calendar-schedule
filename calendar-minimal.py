from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def list_calendars(service):
    """
    List all calendars and their IDs.
    """
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get('items', [])
    print("Available calendars:")
    for calendar in calendars:
        print(f"Name: {calendar['summary']}, ID: {calendar['id']}")

def read_calendar_id(file_path='calendar_id.txt'):
    """
    Reads the calendar ID from a file.
    Args:
        file_path (str): Path to the file containing the calendar ID.
    Returns:
        str: The calendar ID if the file exists and is readable, None otherwise.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return None
    with open(file_path, 'r') as file:
        return file.read().strip()

def get_minimal_schedule(days=7, target_calendar_id=None):
    """
    Get a minimal schedule from a specific Google Calendar for specified number of days.
    Returns just the essential info: day of week, date, time, and event name.

    Args:
        days (int): Number of days to look ahead (default 7)
        target_calendar_id (str): ID of the calendar to filter by
    """
    # OAuth 2.0 flow to get credentials
    flow = InstalledAppFlow.from_client_secrets_file(
        'google_api_oauth_credentials.json',
        SCOPES
    )
    creds = flow.run_local_server(
        port=0, open_browser=False, authorization_prompt_message='Please visit this URL to authorize: {url}'
    )

    # Build the service
    service = build('calendar', 'v3', credentials=creds)

    # Uncomment the line below to list available calendars and find their IDs
    list_calendars(service)

    # Set the calendar ID
    if not target_calendar_id:
        print("No target calendar ID provided. Please specify the calendarId.")
        return

    # Get time bounds
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days)).isoformat() + 'Z'

    # Call the Calendar API
    events_result = service.events().list(
        calendarId=target_calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    # Print minimal schedule
    if not events:
        print('No upcoming events found.')

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # Convert to datetime object for formatting
        if 'T' in start:  # This is a datetime
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            print(f"{start_time.strftime('%A, %Y-%m-%d %H:%M')} - {event['summary']}")
        else:  # This is a date
            start_time = datetime.fromisoformat(start)
            print(f"{start_time.strftime('%A, %Y-%m-%d')} (all day) - {event['summary']}")

if __name__ == '__main__':
    # Read calendar ID from a file
    calendar_id_file = 'calendar_id.txt'
    target_calendar_id = read_calendar_id(calendar_id_file)
    get_minimal_schedule(days=7, target_calendar_id=target_calendar_id)
