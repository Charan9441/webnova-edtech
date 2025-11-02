from flask import Blueprint, jsonify, g
from utils.decorators import auth_required
from utils.helpers import get_json
from services.ai_service import ai_service
from services.firebase_service import firebase_service
from services.scoring_service import scoring_service


bp = Blueprint("quiz", __name__, url_prefix="/api/quiz")


@bp.post("/generate")
@auth_required
def generate_quiz():
	body = get_json(["subject", "difficulty", "lastScore"])
	quiz = ai_service.generate_quiz(
		subject=body["subject"],
		difficulty=int(body["difficulty"]),
		last_score=float(body["lastScore"]),
	)
	quiz_doc = firebase_service.save_quiz(user_id=g.user_id, quiz=quiz, meta={
		"subject": body["subject"],
		"difficulty": int(body["difficulty"]),
	})
	return jsonify({"quizId": quiz_doc["id"], **quiz_doc["data"]}), 201


@bp.post("/submit")
@auth_required
def submit_quiz():
	body = get_json(["quizId", "answers"])
	quiz = firebase_service.get_quiz(body["quizId"])  # includes correct answers
	grading = scoring_service.grade_quiz(quiz, body["answers"])
	update = firebase_service.store_quiz_result(
		user_id=g.user_id,
		quiz_id=body["quizId"],
		grading=grading,
	)
	return jsonify(update), 200


@bp.get("/<quiz_id>")
@auth_required
def get_quiz(quiz_id: str):
	data = firebase_service.get_quiz(quiz_id)
	return jsonify(data), 200

