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


def fetch_summary(client, start="7daysAgo"):
    """Totals for a given date range: users, sessions, pageviews."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date="today")],
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


def fetch_daily_trend(client, days=28):
    """Daily active users for the last N days, for the trend line."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="activeUsers")],
        order_bys=[{"dimension": {"dimension_name": "date"}}],
    )
    response = client.run_report(request)
    return [
        {"date": row.dimension_values[0].value, "activeUsers": int(row.metric_values[0].value)}
        for row in response.rows
    ]


def fetch_top_pages(client, start="7daysAgo"):
    """Top 5 pages by views over the given date range."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date="today")],
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


def fetch_top_countries(client, start="7daysAgo"):
    """Top 8 countries/cities by active users over the given date range."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date="today")],
        dimensions=[Dimension(name="country"), Dimension(name="city")],
        metrics=[Metric(name="activeUsers")],
        order_bys=[{"metric": {"metric_name": "activeUsers"}, "desc": True}],
        limit=8,
    )
    response = client.run_report(request)
    return [
        {
            "country": row.dimension_values[0].value,
            "city": row.dimension_values[1].value,
            "activeUsers": int(row.metric_values[0].value),
        }
        for row in response.rows
    ]


def fetch_device_breakdown(client, start="7daysAgo"):
    """Sessions by device category over the given date range."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date="today")],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="sessions")],
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}],
    )
    response = client.run_report(request)
    return [
        {"device": row.dimension_values[0].value, "sessions": int(row.metric_values[0].value)}
        for row in response.rows
    ]


def fetch_traffic_sources(client, start="28daysAgo"):
    """Sessions by default channel group (Organic, Direct, Referral, Paid, Social, etc.)."""
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date="today")],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}],
    )
    response = client.run_report(request)
    return [
        {"channel": row.dimension_values[0].value, "sessions": int(row.metric_values[0].value)}
        for row in response.rows
    ]


def main():
    client = get_client()

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "property_id": PROPERTY_ID,
        "summary_last_7_days": fetch_summary(client, start="7daysAgo"),
        "summary_last_28_days": fetch_summary(client, start="28daysAgo"),
        "daily_trend_28_days": fetch_daily_trend(client, days=28),
        "top_pages_last_28_days": fetch_top_pages(client, start="28daysAgo"),
        "top_locations_last_28_days": fetch_top_countries(client, start="28daysAgo"),
        "device_breakdown_last_28_days": fetch_device_breakdown(client, start="28daysAgo"),
        "traffic_sources_last_28_days": fetch_traffic_sources(client, start="28daysAgo"),
    }

    os.makedirs("data", exist_ok=True)

    with open("data/latest.json", "w") as f:
        json.dump(payload, f, indent=2)

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
    history = history[-500:]
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    print("GA4 data fetched and written to data/latest.json")


if __name__ == "__main__":
    main()
