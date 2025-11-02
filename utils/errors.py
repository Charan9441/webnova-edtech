from flask import jsonify


class APIError(Exception):

	status_code = 400

	def __init__(self, message: str, status_code: int | None = None):
		super().__init__(message)
		if status_code is not None:
			self.status_code = status_code
		self.message = message


class AuthError(APIError):

	status_code = 401


class ForbiddenError(APIError):

	status_code = 403


class NotFoundError(APIError):

	status_code = 404


def register_error_handlers(app):

	@app.errorhandler(APIError)
	def handle_api_error(err: APIError):
		response = {"error": err.message}
		return jsonify(response), err.status_code

	@app.errorhandler(404)
	def handle_404(_):
		return jsonify({"error": "Not found"}), 404

	@app.errorhandler(405)
	def handle_405(_):
		return jsonify({"error": "Method not allowed"}), 405

	@app.errorhandler(Exception)
	def handle_unexpected(err: Exception):
		# In production, avoid leaking internals
		return jsonify({"error": "Internal server error"}), 500

