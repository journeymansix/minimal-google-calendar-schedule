from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import os
import pickle
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def save_credentials(creds, file_path='token.pickle'):
    """
    Save credentials to a file for reuse.
    """
    with open(file_path, 'wb') as token_file:
        pickle.dump(creds, token_file)

def load_credentials(file_path='token.pickle'):
    """
    Load credentials from a file if they exist.
    """
    if os.path.exists(file_path):
        with open(file_path, 'rb') as token_file:
            creds = pickle.load(token_file)
        if creds and creds.valid:
            return creds
        elif creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                return None
            save_credentials(creds, file_path)
            return creds
    return None

def read_calendar_id(file_path='calendar_id.txt'):
    """
    Read the calendar ID from a file.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return None
    with open(file_path, 'r') as file:
        return file.read().strip()

def generate_pdf(events, output_file='schedule.pdf'):
    """
    Generate a PDF file with the event schedule.
    """
    c = canvas.Canvas(output_file, pagesize=letter)
    c.setFont("Helvetica", 12)  # Set the font to 12pt Helvetica
    width, height = letter
    y_position = height - 50  # Start near the top of the page

    # Event details
    for event in events:
        line = f"{event['formatted_time']} - {event['summary']}"
        c.drawString(50, y_position, line)
        y_position -= 20  # Space between lines

        # Add a page break if necessary
        if y_position < 50:
            c.showPage()
            c.setFont("Helvetica", 12)  # Reset font after a page break
            y_position = height - 50

    c.save()
    print(f"Schedule saved as {output_file}")

def get_minimal_schedule(days=14, target_calendar_id=None, generate_pdf_flag=False, output_file='schedule.pdf'):
    """
    Fetch and display a schedule from Google Calendar for a specific number of days.
    """
    creds = load_credentials()
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            'google_api_oauth_credentials.json',
            SCOPES
        )
        creds = flow.run_local_server(
            port=0, open_browser=False, authorization_prompt_message='Please visit this URL to authorize: {url}'
        )
        save_credentials(creds)

    service = build('calendar', 'v3', credentials=creds)

    if not target_calendar_id:
        print("No target calendar ID provided. Please specify the calendarId.")
        return

    now = datetime.now()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId=target_calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return

    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start:  # This is a datetime
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            formatted_time = start_time.strftime('%A, %Y-%m-%d %I:%M %p')
        else:  # This is a date
            start_time = datetime.fromisoformat(start)
            formatted_time = start_time.strftime('%A, %Y-%m-%d') + " (all day)"

        formatted_events.append({
            'formatted_time': formatted_time,
            'summary': event['summary'],
        })

    # Print schedule to console
    for event in formatted_events:
        print(f"{event['formatted_time']} - {event['summary']}\n")

    # Optionally generate PDF
    if generate_pdf_flag:
        generate_pdf(formatted_events, output_file)

if __name__ == '__main__':
    calendar_id_file = 'calendar_id.txt'
    target_calendar_id = read_calendar_id(calendar_id_file)

    if target_calendar_id:
        get_minimal_schedule(
            days=14,  # Default to 14 days
            target_calendar_id=target_calendar_id,
            generate_pdf_flag=True,  # Enable PDF generation by default
            output_file='schedule.pdf'
        )
