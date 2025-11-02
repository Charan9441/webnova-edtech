from flask import Flask, jsonify
from flask_cors import CORS
from config import Config

# Import blueprints lazily to avoid circular imports if any
from routes.auth import bp as auth_bp
from routes.quiz import bp as quiz_bp
from routes.user import bp as user_bp
from routes.leaderboard import bp as leaderboard_bp
from routes.streak import bp as streak_bp
from utils.errors import register_error_handlers


def create_app() -> Flask:
	app = Flask(__name__)
	app.config.from_object(Config)

	CORS(
		app,
		resources=Config.CORS_RESOURCES,
		supports_credentials=Config.CORS_SUPPORTS_CREDENTIALS,
		allow_headers=Config.CORS_ALLOW_HEADERS,
	)

	# Register blueprints
	app.register_blueprint(auth_bp)
	app.register_blueprint(quiz_bp)
	app.register_blueprint(user_bp)
	app.register_blueprint(leaderboard_bp)
	app.register_blueprint(streak_bp)

	# Error handlers
	register_error_handlers(app)

	@app.get("/health")
	def health() -> tuple[dict, int]:
		return {"status": "ok"}, 200

	return app


app = create_app()


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)

