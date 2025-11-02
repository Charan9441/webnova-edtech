from __future__ import annotations

from datetime import datetime, timezone
from flask import request
from utils.errors import APIError


def utc_now() -> datetime:
	return datetime.now(timezone.utc)


def get_json(required: list[str] | None = None) -> dict:
	data = request.get_json(silent=True) or {}
	if required:
		missing = [k for k in required if k not in data]
		if missing:
			raise APIError(f"Missing fields: {', '.join(missing)}", 400)
	return data

