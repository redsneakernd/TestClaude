"""
Webex REST API client for call queue monitoring.

Required OAuth scopes:
  spark-admin:telephony_config_read  — list queues and agents
  spark-admin:calling_cdr_read       — Detailed Call History (CDR) via analytics endpoint
  analytics:read_all                 — Reports API (longer-range historical reports)

Personal Access Tokens from developer.webex.com include all scopes for your own org.
"""

import io
import zipfile
from typing import Optional

import pandas as pd
import requests

WEBEX_BASE = "https://webexapis.com/v1"
ANALYTICS_BASE = "https://analytics.webexapis.com/v1"


class WebexAPI:
    """Thin wrapper around Webex REST APIs for call queue monitoring."""

    def __init__(self, access_token: str):
        self._sess = requests.Session()
        self._sess.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get(self, base: str, path: str, params: Optional[dict] = None) -> dict:
        r = self._sess.get(f"{base}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _get_paginated(self, base: str, path: str, items_key: str, params: Optional[dict] = None) -> list[dict]:
        """Follow Link-header pagination and return all items."""
        items: list[dict] = []
        url: Optional[str] = f"{base}{path}"
        first = True
        while url:
            r = self._sess.get(url, params=params if first else None, timeout=30)
            r.raise_for_status()
            items.extend(r.json().get(items_key, []))
            first = False
            url = None
            link_header = r.headers.get("Link", "")
            if 'rel="next"' in link_header:
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        url = part[part.find("<") + 1 : part.find(">")]
                        break
        return items

    def _post(self, path: str, payload: dict) -> dict:
        r = self._sess.post(f"{WEBEX_BASE}{path}", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> None:
        r = self._sess.delete(f"{WEBEX_BASE}{path}", timeout=30)
        r.raise_for_status()

    # ── Auth / Identity ───────────────────────────────────────────────────

    def get_me(self) -> dict:
        """Validate token and return the current user's profile."""
        return self._get(WEBEX_BASE, "/people/me")

    # ── Call Queues ───────────────────────────────────────────────────────

    def list_queues(self, org_id: Optional[str] = None) -> list[dict]:
        """Return all call queues across all locations.
        Requires: spark-admin:telephony_config_read
        """
        params: dict = {"max": 1000}
        if org_id:
            params["orgId"] = org_id
        return self._get_paginated(WEBEX_BASE, "/telephony/config/queues", "queues", params)

    def list_queue_agents(
        self,
        queue_id: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> list[dict]:
        """Return agents assigned to queues (optionally filtered by queue or location).
        Requires: spark-admin:telephony_config_read
        """
        params: dict = {"max": 1000}
        if queue_id:
            params["queueId"] = queue_id
        if location_id:
            params["locationId"] = location_id
        return self._get_paginated(WEBEX_BASE, "/telephony/config/queues/agents", "agents", params)

    def list_available_agents(
        self,
        queue_id: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> list[dict]:
        """Return agents currently available (not on a call).
        Requires: spark-admin:telephony_config_read
        """
        params: dict = {"max": 1000}
        if queue_id:
            params["queueId"] = queue_id
        if location_id:
            params["locationId"] = location_id
        return self._get_paginated(
            WEBEX_BASE,
            "/telephony/config/queues/agents/availableAgents",
            "agents",
            params,
        )

    # ── Detailed Call History (CDR) ───────────────────────────────────────

    def get_call_history(
        self,
        start_time: str,
        end_time: str,
        locations: Optional[list[str]] = None,
    ) -> list[dict]:
        """Pull Detailed Call History (CDR) from the analytics endpoint.

        Constraints (Webex API limitation):
          - start_time must be at least 5 minutes in the past
          - end_time cannot be more than 48 hours before now

        Args:
            start_time: ISO-8601, e.g. "2024-04-01T00:00:00.000Z"
            end_time:   ISO-8601, e.g. "2024-04-01T23:59:59.999Z"
            locations:  Optional list of location IDs to filter

        Requires: spark-admin:calling_cdr_read
        Also requires the admin to have the
        "Webex Calling Detailed Call History API access" role enabled in Control Hub.
        """
        params: dict = {"startTime": start_time, "endTime": end_time}
        if locations:
            params["locations"] = ",".join(locations)

        items: list[dict] = []
        url: Optional[str] = f"{ANALYTICS_BASE}/cdr_feed"
        first = True
        while url:
            r = self._sess.get(url, params=params if first else None, timeout=60)
            r.raise_for_status()
            items.extend(r.json().get("items", []))
            first = False
            url = None
            link_header = r.headers.get("Link", "")
            if 'rel="next"' in link_header:
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        url = part[part.find("<") + 1 : part.find(">")]
                        break
        return items

    # ── Reports API (async, longer date ranges) ───────────────────────────

    def list_report_templates(self) -> list[dict]:
        """List all available report templates.
        Requires: analytics:read_all
        """
        return self._get(WEBEX_BASE, "/report-templates").get("items", [])

    def create_report(
        self,
        template_id: int,
        start_date: str,
        end_date: str,
        site_url: Optional[str] = None,
    ) -> str:
        """Kick off an async report generation. Returns the report ID.

        Args:
            template_id: Integer ID from list_report_templates()
            start_date:  "YYYY-MM-DD"
            end_date:    "YYYY-MM-DD"
            site_url:    Required only for Webex Meetings reports

        Requires: analytics:read_all
        """
        payload: dict = {
            "templateId": template_id,
            "startDate": start_date,
            "endDate": end_date,
        }
        if site_url:
            payload["siteUrl"] = site_url
        result = self._post("/reports", payload)
        return str(result.get("Id") or result.get("id") or result.get("reportId") or "")

    def get_report(self, report_id: str) -> dict:
        """Get report status. When status == 'done', downloadURL is populated.
        Requires: analytics:read_all
        """
        return self._get(WEBEX_BASE, f"/reports/{report_id}")

    def list_reports(self) -> list[dict]:
        """List all previously generated reports.
        Requires: analytics:read_all
        """
        return self._get(WEBEX_BASE, "/reports").get("items", [])

    def delete_report(self, report_id: str) -> None:
        """Delete a report (org limit: 50 reports at a time).
        Requires: analytics:read_all
        """
        self._delete(f"/reports/{report_id}")

    def download_report(self, download_url: str) -> pd.DataFrame:
        """Download a completed report (ZIP or CSV) and return as a DataFrame."""
        r = self._sess.get(download_url, timeout=120)
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "")
        if "zip" in content_type or download_url.lower().endswith(".zip"):
            zf = zipfile.ZipFile(io.BytesIO(r.content))
            csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            return pd.read_csv(io.BytesIO(zf.read(csv_name)))
        return pd.read_csv(io.StringIO(r.text))
