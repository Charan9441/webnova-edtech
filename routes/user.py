from flask import Blueprint, jsonify, g
from utils.decorators import auth_required
from utils.helpers import get_json
from services.firebase_service import firebase_service


bp = Blueprint("user", __name__, url_prefix="/api/user")


@bp.get("/me")
@auth_required
def me():
	user = firebase_service.get_user(g.user_id)
	return jsonify(user), 200


@bp.put("/me")
@auth_required
def update_me():
	body = get_json()
	updates = {k: v for k, v in body.items() if k in ("username", "avatar")}
	user = firebase_service.update_user(g.user_id, updates)
	return jsonify(user), 200


@bp.get("/stats")
@auth_required
def stats():
	data = firebase_service.get_user_stats(g.user_id)
	return jsonify(data), 200


@bp.get("/progress")
@auth_required
def progress():
	data = firebase_service.get_user_progress(g.user_id)
	return jsonify(data), 200

