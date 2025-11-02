from flask import Blueprint, jsonify, g
from utils.decorators import auth_required
from services.firebase_service import firebase_service


bp = Blueprint("streak", __name__, url_prefix="/api/streak")


@bp.get("/status")
@auth_required
def status():
	return jsonify(firebase_service.get_streak_status(g.user_id)), 200


@bp.post("/freeze")
@auth_required
def freeze():
	return jsonify(firebase_service.freeze_streak(g.user_id)), 200


@bp.get("/daily-check")
def daily_check():
	# This endpoint is intended for scheduled invocation
	firebase_service.daily_streak_check()
	return jsonify({"success": True}), 200

