from __future__ import annotations

from dataclasses import dataclass
from typing import List
from utils.helpers import utc_now


@dataclass
class ScoringRules:

	base_points_per_correct: int = 5
	difficulty_multiplier: float = 1.5


class ScoringService:

	def __init__(self, rules: ScoringRules | None = None):
		self.rules = rules or ScoringRules()

	def grade_quiz(self, quiz: dict, answers: List[str]) -> dict:
		questions = quiz.get("questions", [])
		total = len(questions)
		correct_flags: List[bool] = []
		correct_count = 0
		for i, q in enumerate(questions):
			correct = (answers[i] if i < len(answers) else None) == q.get("correctAnswer")
			correct_flags.append(bool(correct))
			if correct:
				correct_count += 1
		score = int(round((correct_count / max(1, total)) * 100))
		avg_difficulty = int(quiz.get("difficulty", 3))
		points = int(correct_count * self.rules.base_points_per_correct * (1 + (avg_difficulty - 1) * (self.rules.difficulty_multiplier - 1)))
		streak_incremented = score >= 60
		message = "Great job!" if streak_incremented else "Keep practicing!"
		return {
			"score": score,
			"totalQuestions": total,
			"pointsEarned": points,
			"streakIncremented": streak_incremented,
			"correct": correct_flags,
			"answers": answers,
			"message": message,
			"completedAt": utc_now().isoformat(),
		}


scoring_service = ScoringService()

