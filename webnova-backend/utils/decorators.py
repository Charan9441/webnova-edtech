from functools import wraps
from flask import request, g
from utils.errors import AuthError
from config import Config

try:
	from firebase_admin import auth as fb_auth
except Exception:  # firebase not initialized yet in tests
	fb_auth = None


def auth_required(fn):
	@wraps(fn)
	def wrapper(*args, **kwargs):
		header = request.headers.get("Authorization", "")
		if not header.startswith("Bearer "):
			# Allow demo token format
			if Config.DEMO_MODE and header.startswith("Demo "):
				g.user_id = header.split(" ", 1)[1].strip()
				return fn(*args, **kwargs)
			raise AuthError("Missing or invalid Authorization header")
		token = header.split(" ", 1)[1].strip()
		try:
			if fb_auth is None:
				raise AuthError("Auth not available")
			decoded = fb_auth.verify_id_token(token)
			g.user_id = decoded.get("uid")
			if not g.user_id:
				raise AuthError("Invalid token")
		except AuthError:
			raise
		except Exception:
			raise AuthError("Unauthorized")
		return fn(*args, **kwargs)

	return wrapper

