import os


class Config:

	SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")
	ENV = os.getenv("FLASK_ENV", "production")
	DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
	FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
	PORT = int(os.getenv("PORT", "5000"))

	FIREBASE_CREDENTIALS_PATH = os.getenv(
		"FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json"
	)
	GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
	DEMO_MODE = os.getenv("DEMO_MODE", "False").lower() == "true"

	CORS_RESOURCES = {r"/api/*": {"origins": [FRONTEND_URL]}}
	CORS_SUPPORTS_CREDENTIALS = True
	CORS_ALLOW_HEADERS = [
		"Content-Type",
		"Authorization",
		"X-Requested-With",
	]

