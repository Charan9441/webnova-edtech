function handleLogin() {
	const email = document.getElementById("email").value;
	const password = document.getElementById("password").value;
	
	const DEMO_CREDS = {
		"demo@webnova.ai": "DemoWebNova@2025!",
		"alice@webnova.ai": "AliceQuiz@2025!",
		"bob@webnova.ai": "BobLearns@2025!"
	};
	
	if (DEMO_CREDS[email] === password) {
		console.log("✅ Login successful!");
		localStorage.setItem("loggedInUser", email);
		window.location.href = "dashboard.html";
	} else {
		alert("❌ Invalid credentials");
	}
}

