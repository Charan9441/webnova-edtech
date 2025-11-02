from flask import Blueprint, jsonify
from utils.helpers import get_json
from utils.errors import APIError
from services.firebase_service import firebase_service
from config import Config
from utils.demo_data import DEMO_PASSWORDS, get_demo_user_by_email


bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/signup")
def signup():
	body = get_json(["email", "password", "username"])
	if Config.DEMO_MODE:
		# In demo mode, just return the demo user if email matches, else echo a fake user
		demo = get_demo_user_by_email(body["email"]) or {
			"userId": f"uid-{body['username']}",
			"email": body["email"],
			"username": body["username"],
			"avatar": "🧠",
			"currentStreak": 0,
			"longestStreak": 0,
			"totalPoints": 0,
			"level": 1,
		}
		return jsonify({"userId": demo["userId"], "token": f"demo-{demo['userId']}", "user": demo}), 201
	user = firebase_service.create_auth_user(
		email=body["email"], password=body["password"], username=body["username"]
	)
	return jsonify(user), 201


@bp.post("/login")
def login():
	body = get_json(["email", "password"])
	if Config.DEMO_MODE:
		pw = DEMO_PASSWORDS.get(body["email"]) or ""
		if pw and pw == body["password"]:
			demo = get_demo_user_by_email(body["email"]) or {}
			return jsonify({"userId": demo.get("userId"), "token": f"demo-{demo.get('userId')}", "user": demo}), 200
		return jsonify({"error": "Invalid credentials"}), 401
	try:
		result = firebase_service.login_with_password(
			body["email"], body["password"]
		)
		return jsonify(result), 200
	except APIError as e:
		raise e


@bp.get("/verify")
def verify():
	body = firebase_service.verify_bearer_token()
	return jsonify({"valid": bool(body.get("uid"))}), 200


@bp.post("/logout")
def logout():
	# Stateless JWT; client should discard token. Optionally revoke tokens by uid
	body = firebase_service.verify_bearer_token(optional=True)
	uid = body.get("uid")
	if uid:
		firebase_service.revoke_refresh_tokens(uid)
	return jsonify({"success": True}), 200

