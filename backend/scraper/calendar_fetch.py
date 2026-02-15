"""Google Calendar API fetch — stub for local development."""


def build_calendar_service(oauth_token: dict):
    """Build a Google Calendar API service client."""
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=oauth_token.get("access_token"),
        refresh_token=oauth_token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("calendar", "v3", credentials=creds)


async def fetch_events(service, days_ahead: int = 14) -> list:
    """Fetch upcoming calendar events."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])
    except Exception as e:
        print(f"[calendar] Failed to fetch events: {e}")
        return []
