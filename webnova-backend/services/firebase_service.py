from __future__ import annotations

import json
import os
import requests
from dataclasses import dataclass
from datetime import timedelta

import firebase_admin
from firebase_admin import credentials, firestore, auth as fb_auth

from utils.errors import APIError
from utils.helpers import utc_now
from config import Config
from utils.demo_data import (
	DEMO_USERS_BY_ID,
	DEMO_USERS_BY_EMAIL,
	DEMO_LEADERBOARD_DAILY,
	DEMO_PROGRESS,
	get_demo_user,
	get_demo_user_by_email,
)


@dataclass
class _Collections:
	USERS: str = "users"
	QUIZZES: str = "quizzes"
	PROGRESS: str = "progress"
	LEADERBOARD: str = "leaderboard"


class FirebaseService:

	def __init__(self):
		self.db = None
		self._initialized = False
		self._firebase_web_api_key = os.getenv("FIREBASE_WEB_API_KEY", "")

	def _init_admin(self):
		if not firebase_admin._apps:  # type: ignore[attr-defined]
			cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
			try:
				cred = credentials.Certificate(cred_path)
				firebase_admin.initialize_app(cred)
			except Exception as e:
				raise APIError("Firebase credentials missing or invalid", 500) from e

	def _ensure_init(self):
		if not self._initialized:
			self._init_admin()
			self.db = firestore.client()
			self._initialized = True

	# ---------- Auth ----------
	def create_auth_user(self, email: str, password: str, username: str) -> dict:
		if Config.DEMO_MODE:
			user = get_demo_user_by_email(email) or {
				"userId": f"uid-{username}",
				"email": email,
				"username": username,
				"avatar": "🧠",
				"currentStreak": 0,
				"longestStreak": 0,
				"totalPoints": 0,
				"level": 1,
			}
			return {"userId": user["userId"], "token": f"demo-{user['userId']}", "user": user}
		self._ensure_init()
		try:
			user = fb_auth.create_user(email=email, password=password, display_name=username)
			# Seed user doc
			user_doc = {
				"email": email,
				"username": username,
				"avatar": "",
				"currentStreak": 0,
				"longestStreak": 0,
				"totalPoints": 0,
				"level": 1,
				"lastQuizDate": None,
				"createdAt": utc_now(),
				"streakFrozen": False,
			}
			self.db.collection(_Collections.USERS).document(user.uid).set(user_doc)
			# Issue a custom token for immediate login if needed
			custom_token = fb_auth.create_custom_token(user.uid)
			return {"userId": user.uid, "token": custom_token.decode(), "user": {"uid": user.uid, **user_doc}}
		except Exception as e:
			raise APIError("Failed to create user", 400) from e

	def login_with_password(self, email: str, password: str) -> dict:
		if Config.DEMO_MODE:
			user = get_demo_user_by_email(email)
			if not user:
				raise APIError("Invalid credentials", 401)
			return {"userId": user["userId"], "token": f"demo-{user['userId']}", "user": user}
		if not self._firebase_web_api_key:
			raise APIError("Login not configured on server. Use client SDK or set FIREBASE_WEB_API_KEY.", 501)
		endpoint = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self._firebase_web_api_key}"
		resp = requests.post(endpoint, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
		if resp.status_code != 200:
			raise APIError("Invalid credentials", 401)
		data = resp.json()
		user = self.get_user(data.get("localId"))
		return {"userId": data.get("localId"), "token": data.get("idToken"), "user": user}

	def verify_bearer_token(self, optional: bool = False) -> dict:
		if Config.DEMO_MODE:
			from flask import request
			header = request.headers.get("Authorization", "")
			if header.startswith("Bearer demo-"):
				uid = header.split("demo-", 1)[1]
				return {"uid": uid}
			if optional:
				return {}
			raise APIError("Unauthorized", 401)
		self._ensure_init()
		from flask import request
		header = request.headers.get("Authorization", "")
		if not header.startswith("Bearer "):
			if optional:
				return {}
			raise APIError("Missing or invalid Authorization header", 401)
		token = header.split(" ", 1)[1].strip()
		try:
			return fb_auth.verify_id_token(token)
		except Exception:
			raise APIError("Unauthorized", 401)

	def revoke_refresh_tokens(self, uid: str) -> None:
		self._ensure_init()
		fb_auth.revoke_refresh_tokens(uid)

	# ---------- Users ----------
	def get_user(self, user_id: str) -> dict:
		if Config.DEMO_MODE:
			user = get_demo_user(user_id)
			if not user:
				raise APIError("User not found", 404)
			return user
		self._ensure_init()
		doc = self.db.collection(_Collections.USERS).document(user_id).get()
		if not doc.exists:
			raise APIError("User not found", 404)
		data = doc.to_dict() or {}
		return {"userId": user_id, **data}

	def update_user(self, user_id: str, updates: dict) -> dict:
		if Config.DEMO_MODE:
			user = get_demo_user(user_id)
			if not user:
				raise APIError("User not found", 404)
			user.update(updates)
			return user
		self._ensure_init()
		self.db.collection(_Collections.USERS).document(user_id).update(updates)
		return self.get_user(user_id)

	def get_user_stats(self, user_id: str) -> dict:
		user = self.get_user(user_id)
		# Aggregate basics
		return {
			"streak": user.get("currentStreak", 0),
			"longestStreak": user.get("longestStreak", 0),
			"totalPoints": user.get("totalPoints", 0),
			"level": user.get("level", 1),
			"quizzesCompleted": len(DEMO_PROGRESS.get(user_id, [])) if Config.DEMO_MODE else self._count_user_quizzes(user_id),
			"avgScore": (
				(round(sum(i.get("score", 0) for i in DEMO_PROGRESS.get(user_id, [])) / max(1, len(DEMO_PROGRESS.get(user_id, []))), 2))
				if Config.DEMO_MODE else self._avg_user_score(user_id)
			),
		}

	def get_user_progress(self, user_id: str) -> dict:
		if Config.DEMO_MODE:
			items = DEMO_PROGRESS.get(user_id, [])
		else:
			self._ensure_init()
			progress_ref = self.db.collection(_Collections.PROGRESS).document(user_id).collection("items")
			snaps = progress_ref.order_by("completedAt", direction=firestore.Query.DESCENDING).limit(50).get()
			items = [s.to_dict() for s in snaps]
		return {"items": items}

	def _count_user_quizzes(self, user_id: str) -> int:
		self._ensure_init()
		progress_ref = self.db.collection(_Collections.PROGRESS).document(user_id).collection("items")
		return len(progress_ref.get())

	def _avg_user_score(self, user_id: str) -> float:
		self._ensure_init()
		progress_ref = self.db.collection(_Collections.PROGRESS).document(user_id).collection("items")
		snaps = progress_ref.get()
		if not snaps:
			return 0.0
		scores = [s.to_dict().get("score", 0) for s in snaps]
		return round(sum(scores) / max(1, len(scores)), 2)

	# ---------- Quizzes ----------
	def save_quiz(self, user_id: str, quiz: dict, meta: dict) -> dict:
		if Config.DEMO_MODE:
			data = {
				"userId": user_id,
				"questions": quiz["questions"],
				"subject": meta.get("subject"),
				"difficulty": meta.get("difficulty"),
				"createdAt": utc_now(),
				"expiresAt": utc_now(),
			}
			return {"id": "demo-quiz", "data": data}
		self._ensure_init()
		data = {
			"userId": user_id,
			"questions": quiz["questions"],
			"subject": meta.get("subject"),
			"difficulty": meta.get("difficulty"),
			"createdAt": utc_now(),
			"expiresAt": utc_now() + timedelta(hours=24),
		}
		doc_ref = self.db.collection(_Collections.QUIZZES).document()
		doc_ref.set(data)
		return {"id": doc_ref.id, "data": data}

	def get_quiz(self, quiz_id: str) -> dict:
		if Config.DEMO_MODE:
			return {"quizId": quiz_id, "questions": []}
		self._ensure_init()
		doc = self.db.collection(_Collections.QUIZZES).document(quiz_id).get()
		if not doc.exists:
			raise APIError("Quiz not found", 404)
		return {"quizId": quiz_id, **(doc.to_dict() or {})}

	def store_quiz_result(self, user_id: str, quiz_id: str, grading: dict) -> dict:
		if Config.DEMO_MODE:
			user = get_demo_user(user_id)
			if user:
				user["totalPoints"] = user.get("totalPoints", 0) + grading["pointsEarned"]
				if grading["streakIncremented"]:
					user["currentStreak"] = user.get("currentStreak", 0) + 1
			return {
				"score": grading["score"],
				"totalQuestions": grading["totalQuestions"],
				"pointsEarned": grading["pointsEarned"],
				"streakIncremented": grading["streakIncremented"],
				"correct": grading["correct"],
				"message": grading["message"],
			}
		self._ensure_init()
		# Save progress
		progress_root = self.db.collection(_Collections.PROGRESS).document(user_id)
		progress_item = progress_root.collection("items").document(quiz_id)
		payload = {
			"score": grading["score"],
			"pointsEarned": grading["pointsEarned"],
			"streakIncremented": grading["streakIncremented"],
			"completedAt": utc_now(),
			"answers": grading["answers"],
		}
		progress_item.set(payload)

		# Update user totals
		user_ref = self.db.collection(_Collections.USERS).document(user_id)
		user = user_ref.get().to_dict() or {}
		current_streak = user.get("currentStreak", 0)
		longest = user.get("longestStreak", 0)
		if grading["streakIncremented"]:
			current_streak += 1
			longest = max(longest, current_streak)
		user_update = {
			"totalPoints": user.get("totalPoints", 0) + grading["pointsEarned"],
			"currentStreak": current_streak,
			"longestStreak": longest,
			"lastQuizDate": utc_now(),
		}
		user_ref.update(user_update)

		# Leaderboard
		self._update_leaderboards(user_id, user.get("username", ""), user.get("avatar", ""), user_update)

		return {
			"score": grading["score"],
			"totalQuestions": grading["totalQuestions"],
			"pointsEarned": grading["pointsEarned"],
			"streakIncremented": grading["streakIncremented"],
			"correct": grading["correct"],
			"message": grading["message"],
		}

	# ---------- Leaderboards ----------
	def _update_leaderboards(self, user_id: str, username: str, avatar: str, update: dict):
		self._ensure_init()
		for period in ("daily", "weekly", "all-time"):
			lb_ref = self.db.collection(_Collections.LEADERBOARD).document(period)
			lb_ref.set({"updatedAt": utc_now()}, merge=True)
			lb_ref.collection("users").document(user_id).set({
				"username": username,
				"avatar": avatar,
				"points": update.get("totalPoints", 0),
				"streak": update.get("currentStreak", 0),
			})

	def get_leaderboard(self, period: str) -> list[dict]:
		if Config.DEMO_MODE:
			return DEMO_LEADERBOARD_DAILY
		self._ensure_init()
		users_ref = self.db.collection(_Collections.LEADERBOARD).document(period).collection("users")
		snaps = users_ref.order_by("points", direction=firestore.Query.DESCENDING).limit(10).get()
		items = []
		for idx, s in enumerate(snaps, start=1):
			row = s.to_dict() or {}
			items.append({
				"rank": idx,
				"username": row.get("username", ""),
				"points": row.get("points", 0),
				"streak": row.get("streak", 0),
				"avatar": row.get("avatar", ""),
			})
		return items

	def get_friends_leaderboard(self, user_id: str) -> list[dict]:
		# Placeholder: return only current user's rank
		return self.get_user_rank(user_id)

	def get_user_rank(self, user_id: str) -> dict:
		if Config.DEMO_MODE:
			items = DEMO_LEADERBOARD_DAILY
			rank = next((r["rank"] for r in items if r["username"] == (get_demo_user(user_id) or {}).get("username")), 3)
			return {"currentRank": rank, "totalUsers": 2847, "pointsToNextRank": 100}
		self._ensure_init()
		users_ref = self.db.collection(_Collections.LEADERBOARD).document("all-time").collection("users")
		snaps = users_ref.order_by("points", direction=firestore.Query.DESCENDING).get()
		rank = None
		for idx, s in enumerate(snaps, start=1):
			if s.id == user_id:
				rank = idx
				points = s.to_dict().get("points", 0)
				break
			
		total = len(snaps)
		points_to_next = 0
		if rank and rank > 1:
			prev = snaps[rank - 2].to_dict()
			points_to_next = max(0, prev.get("points", 0) - points)
		return {"currentRank": rank or total, "totalUsers": total, "pointsToNextRank": points_to_next}

	# ---------- Streaks ----------
	def get_streak_status(self, user_id: str) -> dict:
		self._ensure_init()
		user = self.get_user(user_id)
		last = user.get("lastQuizDate")
		return {
			"currentStreak": user.get("currentStreak", 0),
			"longestStreak": user.get("longestStreak", 0),
			"lastCompletedDate": str(last) if last else None,
			"daysUntilBreak": 1,  # simplified for demo
		}

	def freeze_streak(self, user_id: str) -> dict:
		self._ensure_init()
		user = self.get_user(user_id)
		points = user.get("totalPoints", 0)
		if points < 50:
			raise APIError("Not enough points", 400)
		self.update_user(user_id, {"totalPoints": points - 50, "streakFrozen": True})
		return {"success": True, "pointsUsed": 50}

	def daily_streak_check(self) -> None:
		# Placeholder: would iterate users and reset if missed
		pass


firebase_service = FirebaseService()

