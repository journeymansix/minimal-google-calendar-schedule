from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os
import pickle
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
INCLUDE_KEYWORDS = ['Commitments', 'GGR']  # Customize this list


def save_credentials(creds, file_path='token.pickle'):
    with open(file_path, 'wb') as token_file:
        pickle.dump(creds, token_file)


def load_credentials(file_path='token.pickle'):
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


def get_all_calendar_ids(service, keywords=None):
    calendar_ids = []
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_entry in calendar_list['items']:
            summary = calendar_entry.get('summary', '(no title)')
            if not keywords or any(k.lower() in summary.lower() for k in keywords):
                calendar_ids.append({
                    'id': calendar_entry['id'],
                    'summary': summary
                })
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    return calendar_ids


def get_combined_schedule(service, days=30, calendar_ids=None):
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days)).isoformat() + 'Z'
    combined_events = []

    for cal in calendar_ids:
        events_result = service.events().list(
            calendarId=cal['id'],
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted_time = start_time.strftime('%Y-%m-%d %I:%M %p')
            else:
                # Convert date-only to offset-aware
                start_time = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
                formatted_time = start_time.strftime('%Y-%m-%d') + " (all day)"

            combined_events.append({
                'start_time': start_time,
                'formatted_time': formatted_time,
                'summary': event.get('summary', '(no title)')
            })

    combined_events.sort(key=lambda x: x['start_time'])
    return combined_events


def group_events_by_day(events):
    """
    Returns a list of (day_string, [event_line, ...]) tuples sorted by date.
    """
    grouped = defaultdict(list)
    for event in events:
        event_date = event['start_time'].date()
        day_str = event['start_time'].strftime("%A, %B %d, %Y")
        if 'all day' in event['formatted_time']:
            time_str = ''
        else:
            time_str = event['start_time'].strftime('%I:%M %p')
        line = f"{time_str} {event['summary']}".strip()
        grouped[day_str].append((event['start_time'], line))

    sorted_days = []
    for day_str, items in grouped.items():
        sorted_lines = [line for _, line in sorted(items, key=lambda x: x[0])]
        day_date = items[0][0].date()
        sorted_days.append((day_date, day_str, sorted_lines))

    sorted_days.sort(key=lambda x: x[0])  # sort by date
    return [(day_str, lines) for _, day_str, lines in sorted_days]


def generate_rtf(events, output_file='schedule.rtf'):
    grouped = group_events_by_day(events)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(r"{\rtf1\ansi\deff0\n")
        f.write(r"{\fonttbl{\f0\fswiss Helvetica;}}\n")
        f.write(r"\f0\fs24\n")

        for date_str, lines in grouped:
            f.write(r"\b " + date_str.replace('\\', r'\\') + r"\b0\line\n")
            for line in lines:
                line = line.replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}')
                f.write(line + r"\line\n")
            f.write(r"\line\n")  # space between day groups

        f.write("}")
    print(f"Schedule saved as {output_file}")


def generate_pdf(events, output_file='schedule.pdf'):
    grouped = group_events_by_day(events)
    c = canvas.Canvas(output_file, pagesize=letter)
    c.setFont("Helvetica", 12)
    width, height = letter
    y_position = height - 40
    line_spacing = 14

    for date_str, lines in grouped:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, date_str)
        y_position -= line_spacing
        c.setFont("Helvetica", 12)
        for line in lines:
            c.drawString(70, y_position, line)
            y_position -= line_spacing
            if y_position < 40:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - 40
        y_position -= line_spacing

    c.save()
    print(f"Schedule saved as {output_file}")


def generate_txt(events, output_file='schedule.txt'):
    grouped = group_events_by_day(events)
    with open(output_file, 'w', encoding='utf-8') as f:
        for date_str, lines in grouped:
            f.write(date_str + '\n')
            for line in lines:
                f.write("  " + line + '\n')
            f.write('\n')
    print(f"Schedule saved as {output_file}")


def generate_output(events, format='pdf', output_file='schedule'):
    output_file = f"{output_file}.{format}"
    if format == 'pdf':
        generate_pdf(events, output_file)
    elif format == 'rtf':
        generate_rtf(events, output_file)
    elif format == 'txt':
        generate_txt(events, output_file)
    else:
        raise ValueError(f"Unsupported format: {format}")


if __name__ == '__main__':
    creds = load_credentials()
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            'google_api_oauth_credentials.json', SCOPES)
        creds = flow.run_local_server(port=0, open_browser=False)
        save_credentials(creds)

    service = build('calendar', 'v3', credentials=creds)
    calendar_ids = get_all_calendar_ids(service, keywords=INCLUDE_KEYWORDS)

    if not calendar_ids:
        print(f"No calendars found matching keywords: {INCLUDE_KEYWORDS}")
    else:
        events = get_combined_schedule(service, days=30, calendar_ids=calendar_ids)

        for event in events:
            print(f"{event['formatted_time']} - {event['summary']}")

        # Change format and filename here:
        generate_output(events, format='txt', output_file='schedule')
