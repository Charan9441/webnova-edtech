const functions = require('firebase-functions');
const admin = require('firebase-admin');
const { DateTime } = require('luxon');

if (!admin.apps.length) {
	admin.initializeApp();
}

const db = admin.firestore();

function todayStr() { return DateTime.utc().toISODate(); }

// 1) Daily Streak Reset (23:59 UTC)
exports.dailyStreakReset = functions.pubsub.schedule('59 23 * * *').onRun(async () => {
	const usersRef = db.collection('users');
	const snap = await usersRef.get();
	const today = todayStr();
	const batch = db.batch();
	snap.forEach(doc => {
		const u = doc.data() || {};
		const last = u.lastQuizCompletedDateString;
		if (last !== today && !u.streakFrozen) {
			batch.update(doc.ref, { currentStreak: 0 });
			// Optional: record broken streak in /streaks
		}
	});
	await batch.commit();
	return null;
});

// 2) On Quiz Submitted (userProgress)
exports.onQuizSubmitted = functions.firestore
	.document('userProgress/{userId}/items/{progressId}')
	.onCreate(async (snap, context) => {
		const data = snap.data();
		const userId = context.params.userId;
		const userRef = db.collection('users').doc(userId);
		const userSnap = await userRef.get();
		const user = userSnap.data() || {};

		const score = data.score || 0;
		const pointsEarned = data.pointsEarned || 0;
		const correct = Math.round((score / 100) * (data.totalQuestions || 5));

		// Update user counters
		const updates = {
			totalQuizzesCompleted: (user.totalQuizzesCompleted || 0) + 1,
			totalPoints: (user.totalPoints || 0) + pointsEarned,
			totalQuestionsAnswered: (user.totalQuestionsAnswered || 0) + (data.totalQuestions || 5),
			lastActiveAt: admin.firestore.FieldValue.serverTimestamp(),
			averageScore: Number((((user.averageScore || 0) * (user.totalQuizzesCompleted || 0) + score) / ((user.totalQuizzesCompleted || 0) + 1)).toFixed(2))
		};
		await userRef.set(updates, { merge: true });

		// Update streaks (same-day completion increments)
		const ds = db.collection('dailyStats').doc(userId).collection('days').doc(todayStr());
		await ds.set({
			userId,
			date: todayStr(),
			dateTimestamp: admin.firestore.FieldValue.serverTimestamp(),
			quizzesCompleted: admin.firestore.FieldValue.increment(1),
			questionsAnswered: admin.firestore.FieldValue.increment(data.totalQuestions || 5),
			pointsEarned: admin.firestore.FieldValue.increment(pointsEarned),
			bestScore: admin.firestore.FieldValue.increment(0),
			version: 1
		}, { merge: true });

		// Streak increment logic
		const today = todayStr();
		const incrementStreak = (user.lastQuizCompletedDateString !== today);
		if (incrementStreak) {
			const newStreak = (user.currentStreak || 0) + 1;
			await userRef.set({
				currentStreak: newStreak,
				longestStreak: Math.max(user.longestStreak || 0, newStreak),
				lastQuizCompletedDate: admin.firestore.FieldValue.serverTimestamp(),
				lastQuizCompletedDateString: today
			}, { merge: true });
		}

		// Queue leaderboard update
		await db.collection('leaderboards').doc('daily').collection('users').doc(userId).set({
			userId,
			username: user.username || '',
			avatar: user.avatar || '',
			pointsToday: admin.firestore.FieldValue.increment(pointsEarned),
			totalPoints: (user.totalPoints || 0) + pointsEarned,
			currentStreak: (user.currentStreak || 0),
			lastUpdatedAt: admin.firestore.FieldValue.serverTimestamp(),
			period: 'daily'
		}, { merge: true });

		// Badge checks (simplified hook)
		await exports.checkAndAwardBadgesTask(userId);
		return null;
	});

// 3) Check and Award Badges (utility)
exports.checkAndAwardBadgesTask = async function(userId) {
	const userRef = db.collection('users').doc(userId);
	const user = (await userRef.get()).data() || {};
	const badges = await db.collection('badges').get();
	const owned = new Set((user.badgesEarned || []).map(b => b.badgeId));
	const batch = db.batch();
	badges.forEach(doc => {
		const b = doc.data();
		if (owned.has(b.badgeId)) return;
		const type = b.criteria?.type;
		const cond = b.criteria?.condition || {};
		let qualifies = false;
		if (type === 'streak' && (user.currentStreak || 0) >= (cond.streak || 0)) qualifies = true;
		if (type === 'score' && (user.averageScore || 0) >= (cond.minScore || 0)) qualifies = true;
		if (type === 'volume' && (user.totalQuizzesCompleted || 0) >= (cond.quizzesCompleted || 0)) qualifies = true;
		if (!qualifies) return;
		const entry = {
			badgeId: b.badgeId,
			badgeName: b.name,
			unlockedAt: admin.firestore.FieldValue.serverTimestamp(),
			rarity: b.rarity || 'common'
		};
		batch.update(userRef, {
			badgesEarned: admin.firestore.FieldValue.arrayUnion(entry),
			totalBadgesEarned: admin.firestore.FieldValue.increment(1),
			totalPoints: admin.firestore.FieldValue.increment(b.points || 0)
		});
	});
	await batch.commit();
};

// 4) Leaderboard Refresh (hourly)
exports.refreshLeaderboards = functions.pubsub.schedule('0 * * * *').onRun(async () => {
	const periods = ['daily', 'weekly', 'all-time'];
	for (const p of periods) {
		const ref = db.collection('leaderboards').doc(p).collection('users');
		const snap = await ref.orderBy(p === 'daily' ? 'pointsToday' : 'totalPoints', 'desc').get();
		let rank = 0; const batch = db.batch();
		snap.forEach(doc => { rank += 1; batch.update(doc.ref, { rank, lastUpdatedAt: admin.firestore.FieldValue.serverTimestamp() }); });
		await batch.commit();
	}
	return null;
});

// 5) Derived Fields Update (on user update)
exports.updateDerivedFields = functions.firestore
	.document('users/{userId}')
	.onWrite(async (change, context) => {
		const userId = context.params.userId;
		const after = change.after.exists ? change.after.data() : null;
		if (!after) return null;
		const level = Math.max(1, Math.floor((after.totalPoints || 0) / 100) + 1);
		const inLevel = (after.totalPoints || 0) % 100;
		await change.after.ref.set({
			currentLevel: level,
			pointsInCurrentLevel: inLevel,
			lastDataRefresh: admin.firestore.FieldValue.serverTimestamp()
		}, { merge: true });
		return null;
	});

// 6) Streak Reminders (daily 08:00 UTC)
exports.sendStreakReminders = functions.pubsub.schedule('0 8 * * *').onRun(async () => {
	const users = await db.collection('users').where('currentStreak', '>', 0).get();
	const today = todayStr();
	const batch = db.batch();
	users.forEach(doc => {
		const u = doc.data() || {};
		if (u.lastQuizCompletedDateString !== today) {
			const nref = db.collection('notifications').doc(doc.id).collection('items').doc();
			batch.set(nref, {
				type: 'streak_reminder',
				title: 'Keep your streak alive! 🔥',
				message: 'Complete a quiz today to continue your streak.',
				createdAt: admin.firestore.FieldValue.serverTimestamp(),
				deliveryMethod: 'in-app',
				delivered: true,
				deliveredAt: admin.firestore.FieldValue.serverTimestamp()
			});
		}
	});
	await batch.commit();
	return null;
});

// 7) Session Timeout (every 5 minutes)
exports.handleSessionTimeout = functions.pubsub.schedule('every 5 minutes').onRun(async () => {
	const now = DateTime.utc();
	const sessions = await db.collectionGroup('userSessions').where('isActive', '==', true).get();
	const batch = db.batch();
	sessions.forEach(doc => {
		const s = doc.data() || {};
		const last = s.lastActivityAt?.toDate ? DateTime.fromJSDate(s.lastActivityAt.toDate()) : null;
		if (last && now.diff(last, 'minutes').minutes > 30) {
			batch.update(doc.ref, { isActive: false, endedAt: admin.firestore.FieldValue.serverTimestamp() });
		}
	});
	await batch.commit();
	return null;
});

// 8) Subject Mastery (hook on quiz submit)
exports.updateSubjectMastery = async function(userId, subject) {
	// Placeholder for extended analytics; kept minimal here
	return null;
};

