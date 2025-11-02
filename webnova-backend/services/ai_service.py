from __future__ import annotations

import json
import os
import google.generativeai as genai
from config import Config
from utils.errors import APIError


PROMPT_TEMPLATE = (
	"""
Generate exactly 5 multiple-choice questions about {subject}.

Difficulty Level: {difficulty} (1-5 scale)
User's Previous Score: {lastScore}%

Adjust question difficulty:
- If lastScore < 60%: Make easier (level 1-2)
- If lastScore 60-80%: Keep moderate (level 2-3)
- If lastScore > 80%: Make harder (level 3-4)

Requirements:
- Questions should progressively increase in difficulty
- Provide 4 plausible options (1 correct, 3 distractors)
- Include clear explanations for correct answers
- Topics should vary (not all on same subtopic)
- Make questions practical, not trivial

Return ONLY valid JSON (no markdown, no extra text):
{
  "questions": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correctAnswer": "A",
      "explanation": "...",
      "difficulty": 2,
      "topic": "..."
    }
  ]
}
	"""
)


class AIService:

	def __init__(self):
		self._api_key = os.getenv("GOOGLE_API_KEY", "")
		self.model = None

	def _ensure_model(self):
		if not self.model:
			api_key = self._api_key or os.getenv("GOOGLE_API_KEY", "")
			if not api_key:
				raise APIError("GOOGLE_API_KEY not configured", 500)
			genai.configure(api_key=api_key)
			self.model = genai.GenerativeModel("gemini-pro")

	def generate_quiz(self, subject: str, difficulty: int, last_score: float) -> dict:
		if Config.DEMO_MODE:
			data = {
				"questions": [
					{
						"question": "What is the time complexity of binary search?",
						"options": ["O(n)", "O(n log n)", "O(log n)", "O(1)"],
						"correctAnswer": "O(log n)",
						"explanation": "Binary search halves the space each step.",
						"difficulty": 4,
						"topic": "Algorithms",
					},
					{
						"question": "Which is NOT a Python built-in?",
						"options": ["len()", "append()", "type()", "range()"],
						"correctAnswer": "append()",
						"explanation": "append is a list method.",
						"difficulty": 3,
						"topic": "Python",
					},
					{"question": "What does PEP stand for?", "options": ["Python Enhancement Proposal", "Python Easy Package", "Performance Eval Plan", "Package Entry Point"], "correctAnswer": "Python Enhancement Proposal", "explanation": "", "difficulty": 2, "topic": "Python"},
					{"question": "Select mutable type:", "options": ["tuple", "str", "list", "frozenset"], "correctAnswer": "list", "explanation": "", "difficulty": 2, "topic": "Python"},
					{"question": "Which keyword for context managers?", "options": ["with", "using", "do", "defer"], "correctAnswer": "with", "explanation": "", "difficulty": 2, "topic": "Python"},
				]
			}
			self._validate(data)
			return data
		self._ensure_model()
		prompt = PROMPT_TEMPLATE.format(subject=subject, difficulty=difficulty, lastScore=last_score)
		try:
			resp = self.model.generate_content(prompt)
			text = resp.text or "{}"
			data = self._parse_json(text)
			self._validate(data)
			return data
		except APIError:
			raise
		except Exception as e:
			raise APIError("AI generation failed", 502) from e

	def _parse_json(self, text: str) -> dict:
		try:
			return json.loads(text)
		except json.JSONDecodeError:
			# Try to salvage JSON
			start = text.find("{")
			end = text.rfind("}")
			if start != -1 and end != -1 and end > start:
				return json.loads(text[start : end + 1])
			raise APIError("Invalid AI JSON response", 502)

	def _validate(self, data: dict) -> None:
		if "questions" not in data or not isinstance(data["questions"], list):
			raise APIError("AI response missing questions", 502)
		if len(data["questions"]) != 5:
			raise APIError("AI must return exactly 5 questions", 502)
		for q in data["questions"]:
			if not all(k in q for k in ("question", "options", "correctAnswer", "explanation")):
				raise APIError("Invalid question format", 502)
			if not isinstance(q["options"], list) or len(q["options"]) != 4:
				raise APIError("Each question must have 4 options", 502)


ai_service = AIService()

