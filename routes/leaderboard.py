from flask import Blueprint, jsonify, g
from utils.decorators import auth_required
from services.firebase_service import firebase_service


bp = Blueprint("leaderboard", __name__, url_prefix="/api/leaderboard")


@bp.get("/daily")
def daily():
	return jsonify(firebase_service.get_leaderboard("daily")), 200


@bp.get("/weekly")
def weekly():
	return jsonify(firebase_service.get_leaderboard("weekly")), 200


@bp.get("/all-time")
def all_time():
	return jsonify(firebase_service.get_leaderboard("all-time")), 200


@bp.get("/friends")
@auth_required
def friends():
	# Assuming friends list stored on user doc later; placeholder ranks self only
	return jsonify(firebase_service.get_friends_leaderboard(g.user_id)), 200


@bp.get("/rank")
@auth_required
def rank():
	return jsonify(firebase_service.get_user_rank(g.user_id)), 200

