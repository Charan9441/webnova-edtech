from __future__ import annotations

from datetime import datetime, timezone, timedelta


def _dt(hours_ago: int = 0):
	return datetime.now(timezone.utc) - timedelta(hours=hours_ago)


DEMO_USERS_BY_EMAIL = {
	"demo@webnova.ai": {
		"userId": "uid-demo",
		"email": "demo@webnova.ai",
		"username": "QuizMaster",
		"avatar": "🧠",
		"currentStreak": 12,
		"longestStreak": 25,
		"totalPoints": 2850,
		"level": 18,
		"lastQuizDate": _dt(2),
		"createdAt": _dt(1000),
		"streakFrozen": False,
	},
	"alice@webnova.ai": {
		"userId": "uid-alice",
		"email": "alice@webnova.ai",
		"username": "AliceLeads",
		"avatar": "🎯",
		"currentStreak": 15,
		"longestStreak": 20,
		"totalPoints": 3200,
		"level": 19,
		"lastQuizDate": _dt(5),
		"createdAt": _dt(1200),
		"streakFrozen": False,
	},
	"bob@webnova.ai": {
		"userId": "uid-bob",
		"email": "bob@webnova.ai",
		"username": "BobTheBuilder",
		"avatar": "⚡",
		"currentStreak": 8,
		"longestStreak": 12,
		"totalPoints": 2100,
		"level": 14,
		"lastQuizDate": _dt(8),
		"createdAt": _dt(1300),
		"streakFrozen": False,
	},
	"charlie@webnova.ai": {
		"userId": "uid-charlie",
		"email": "charlie@webnova.ai",
		"username": "CodeChampion",
		"avatar": "💻",
		"currentStreak": 12,
		"longestStreak": 18,
		"totalPoints": 2950,
		"level": 17,
		"lastQuizDate": _dt(20),
		"createdAt": _dt(1400),
		"streakFrozen": False,
	},
	"diana@webnova.ai": {
		"userId": "uid-diana",
		"email": "diana@webnova.ai",
		"username": "DianaWins",
		"avatar": "🏆",
		"currentStreak": 20,
		"longestStreak": 30,
		"totalPoints": 4500,
		"level": 24,
		"lastQuizDate": _dt(1),
		"createdAt": _dt(1600),
		"streakFrozen": False,
	},
	"evan@webnova.ai": {
		"userId": "uid-evan",
		"email": "evan@webnova.ai",
		"username": "SpeedLearner",
		"avatar": "🚀",
		"currentStreak": 5,
		"longestStreak": 9,
		"totalPoints": 1200,
		"level": 10,
		"lastQuizDate": _dt(30),
		"createdAt": _dt(1000),
		"streakFrozen": False,
	},
}


DEMO_PASSWORDS = {
	"demo@webnova.ai": "DemoWebNova@2025!",
	"alice@webnova.ai": "AliceQuiz@2025!",
	"bob@webnova.ai": "BobLearns@2025!",
	"charlie@webnova.ai": "CharlieCode@2025!",
	"diana@webnova.ai": "DianaAI@2025!",
	"evan@webnova.ai": "EvanQuick@2025!",
}


DEMO_USERS_BY_ID = {u["userId"]: u for u in DEMO_USERS_BY_EMAIL.values()}


DEMO_LEADERBOARD_DAILY = [
	{ "rank": 1, "username": "DianaWins", "points": 4500, "streak": 20, "avatar": "🏆" },
	{ "rank": 2, "username": "CodeChampion", "points": 2950, "streak": 12, "avatar": "💻" },
	{ "rank": 3, "username": "QuizMaster", "points": 2850, "streak": 12, "avatar": "🧠" },
	{ "rank": 4, "username": "AliceLeads", "points": 3200, "streak": 15, "avatar": "🎯" },
	{ "rank": 5, "username": "BobTheBuilder", "points": 2100, "streak": 8, "avatar": "⚡" },
]


DEMO_PROGRESS = {
	"uid-demo": [
		{"quizId": "q1", "score": 90, "pointsEarned": 35, "completedAt": _dt(2)},
		{"quizId": "q2", "score": 85, "pointsEarned": 28, "completedAt": _dt(2)},
		{"quizId": "q3", "score": 80, "pointsEarned": 32, "completedAt": _dt(26)},
	]
}


def get_demo_user_by_email(email: str) -> dict | None:
	return DEMO_USERS_BY_EMAIL.get(email)


def get_demo_user(user_id: str) -> dict | None:
	return DEMO_USERS_BY_ID.get(user_id)

