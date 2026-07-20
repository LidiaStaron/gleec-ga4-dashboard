"""
Pulls key metrics from a GA4 property using a service account and writes
the results to data/latest.json, plus appends a snapshot to data/history.json.

Required environment variables:
  GA4_PROPERTY_ID          - numeric GA4 property ID (e.g. 435670861)
  GOOGLE_APPLICATION_CREDS - path to the service account JSON key file
"""

import json
import os
from datetime import datetime, timezone

from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

PROPERTY_ID = os.environ["GA4_PROPERTY_ID"]
CREDS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDS", "service-account.json")

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def get_client():
    creds = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=SCOPES
    )
    return BetaAnalyticsDataClient(credentials=creds)


def fetch_summary(client):
    """Totals for the last 7 days: users, sessions, pageviews."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
        ],
    )
    response = client.run_report(request)
    if not response.rows:
        return {"activeUsers": 0, "sessions": 0, "screenPageViews": 0}

    row = response.rows[0]
    return {
        "activeUsers": int(row.metric_values[0].value),
        "sessions": int(row.metric_values[1].value),
        "screenPageViews": int(row.metric_values[2].value),
    }


def fetch_daily_trend(client):
    """Daily active users for the last 14 days, for a simple trend line."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="14daysAgo", end_date="today")],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="activeUsers")],
        order_bys=[{"dimension": {"dimension_name": "date"}}],
    )
    response = client.run_report(request)
    return [
        {"date": row.dimension_values[0].value, "activeUsers": int(row.metric_values[0].value)}
        for row in response.rows
    ]


def fetch_top_pages(client):
    """Top 5 pages by views over the last 7 days."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        order_bys=[{"metric": {"metric_name": "screenPageViews"}, "desc": True}],
        limit=5,
    )
    response = client.run_report(request)
    return [
        {"page": row.dimension_values[0].value, "views": int(row.metric_values[0].value)}
        for row in response.rows
    ]


def main():
    client = get_client()

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "property_id": PROPERTY_ID,
        "summary_last_7_days": fetch_summary(client),
        "daily_trend_14_days": fetch_daily_trend(client),
        "top_pages_last_7_days": fetch_top_pages(client),
    }

    os.makedirs("data", exist_ok=True)

    with open("data/latest.json", "w") as f:
        json.dump(payload, f, indent=2)

    # Append a lightweight snapshot to history for a longer-run trend if wanted later
    history_path = "data/history.json"
    history = []
    if os.path.exists(history_path):
        with open(history_path) as f:
            history = json.load(f)
    history.append(
        {
            "updated_at": payload["updated_at"],
            "summary": payload["summary_last_7_days"],
        }
    )
    history = history[-500:]  # keep file bounded
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    print("GA4 data fetched and written to data/latest.json")


if __name__ == "__main__":
    main()
