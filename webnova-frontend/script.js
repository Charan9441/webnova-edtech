/* Config */
const BASE_URL = (window.__API_BASE__ || 'http://localhost:5000');

/* State */
const state = {
	user: null,
	token: null,
	quiz: null,
	quizProgress: { index: 0, answers: [] },
	leaderboard: { period: 'daily', items: [] },
};

/* Utilities */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
function toast(message, type = 'success') {
	const node = document.createElement('div');
	node.className = `toast ${type}`;
	node.textContent = message;
	$('#toasts').appendChild(node);
	setTimeout(() => node.remove(), 4000);
}
function setLoading(btn, loading) {
	btn.classList.toggle('loading', !!loading);
	btn.disabled = !!loading;
}
function saveSession() {
	localStorage.setItem('webnova:user', JSON.stringify(state.user));
	if (state.token) localStorage.setItem('webnova:token', state.token);
}
function loadSession() {
	try {
		state.user = JSON.parse(localStorage.getItem('webnova:user')) || null;
		state.token = localStorage.getItem('webnova:token');
	} catch (_) {}
}
function authHeaders() {
	return state.token ? { 'Authorization': `Bearer ${state.token}` } : {};
}
function formatNumber(n) {
	return (n || 0).toLocaleString();
}
function nowTime() {
	const d = new Date();
	return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/* Routing */
function routeTo(page) {
	const app = $('#app');
	app.dataset.route = page;
	$$('.page').forEach(p => p.classList.toggle('active', p.dataset.page === page));
	$$('[data-nav]').forEach(b => b.classList.toggle('active', b.dataset.nav === page));
	if (page !== 'auth') $('.page-auth').classList.add('hidden');
	else $('.page-auth').classList.remove('hidden');
}

/* Particles */
function initParticles() {
	const canvas = $('#bg-particles'); if (!canvas) return;
	const ctx = canvas.getContext('2d');
	let W, H; function resize(){ W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; } resize();
	window.addEventListener('resize', resize);
	const pts = Array.from({length: 60}, () => ({ x: Math.random()*W, y: Math.random()*H, r: Math.random()*2+0.5, vx: (Math.random()-0.5)*0.3, vy:(Math.random()-0.5)*0.3 }));
	(function loop(){
		ctx.clearRect(0,0,W,H);
		ctx.fillStyle = 'rgba(255,255,255,0.25)';
		pts.forEach(p => { p.x+=p.vx; p.y+=p.vy; if(p.x<0||p.x>W)p.vx*=-1; if(p.y<0||p.y>H)p.vy*=-1; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fill(); });
		requestAnimationFrame(loop);
	})();
}

/* Auth */
async function login(email, password) {
	const btn = $('.btn-login'); setLoading(btn, true);
	try {
		const res = await fetch(`${BASE_URL}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) });
		if (!res.ok) throw new Error('Login failed');
		const data = await res.json();
		state.user = data.user; state.token = data.token; saveSession();
		toast('Welcome back!', 'success');
		hydrateHeader();
		await loadDashboard();
		routeTo('dashboard');
	} catch (e) {
		toast(e.message || 'Login error', 'error');
	} finally { setLoading(btn, false); }
}
async function signup(username, email, password) {
	const btn = $('.btn-signup'); setLoading(btn, true);
	try {
		const res = await fetch(`${BASE_URL}/api/auth/signup`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, email, password }) });
		if (!res.ok) throw new Error('Signup failed');
		const data = await res.json();
		state.user = data.user; state.token = data.token; saveSession();
		toast('Account created!', 'success');
		hydrateHeader();
		await loadDashboard();
		routeTo('dashboard');
	} catch (e) { toast(e.message || 'Signup error', 'error'); } finally { setLoading(btn, false); }
}
function logout() {
	state.user = null; state.token = null; localStorage.removeItem('webnova:user'); localStorage.removeItem('webnova:token');
	routeTo('auth');
}

/* Dashboard */
async function loadDashboard() {
	try {
		const [meRes, statsRes, lbRes] = await Promise.all([
			fetch(`${BASE_URL}/api/user/me`, { headers: { ...authHeaders() } }),
			fetch(`${BASE_URL}/api/user/stats`, { headers: { ...authHeaders() } }),
			fetch(`${BASE_URL}/api/leaderboard/daily`)
		]);
		if (meRes.ok) { state.user = await meRes.json(); }
		if (statsRes.ok) { const stats = await statsRes.json(); renderDashboard(stats); }
		if (lbRes.ok) { const items = await lbRes.json(); renderLeaderboardPreview(items); }
	} catch (_) { /* silent */ }
}
function renderDashboard(stats) {
	$('#streak-value').textContent = `${stats.streak ?? 0}`;
	$('#stat-points').textContent = formatNumber(stats.totalPoints ?? 0);
	$('#stat-level').textContent = formatNumber(stats.level ?? 1);
	const rp = $('#recent-quizzes'); rp.innerHTML = '';
	const recent = [
		{ title: 'Python Basics', score: 85, time: '4m 30s' },
		{ title: 'Flask APIs', score: 92, time: '6m 10s' },
		{ title: 'Data Types', score: 60, time: '5m 01s' },
	];
	recent.forEach(r => {
		const li = document.createElement('li');
		const badge = r.score>=80? 'lime' : r.score>=60? 'yellow' : 'red';
		li.innerHTML = `<span>${r.title}</span><span class="badge-score ${badge}">${r.score}%</span><span>${r.time}</span>`;
		rp.appendChild(li);
	});
}
function renderLeaderboardPreview(items) {
	const c = $('#lb-preview'); c.innerHTML = '';
	(items || []).slice(0,5).forEach((u,i)=>{
		const li = document.createElement('li');
		li.innerHTML = `<span>#${i+1}</span><span>${u.username||'User'}</span><span>${formatNumber(u.points||0)}</span><span>🔥 ${u.streak||0}</span>`;
		c.appendChild(li);
	});
}

/* Quiz */
async function startQuiz(subject='Python', difficulty=2, lastScore=80){
	try{
		const res = await fetch(`${BASE_URL}/api/quiz/generate`, { method:'POST', headers:{ 'Content-Type':'application/json', ...authHeaders() }, body: JSON.stringify({ subject, difficulty, lastScore }) });
		if(!res.ok) throw new Error('Failed to generate quiz');
		const data = await res.json();
		state.quiz = data; state.quizProgress = { index: 0, answers: [] };
		renderQuiz(); routeTo('quiz');
	}catch(e){ toast(e.message,'error'); }
}
function renderQuiz(){
	if(!state.quiz) return;
	const idx = state.quizProgress.index; const total = state.quiz.questions.length;
	$('#quiz-title').textContent = state.quiz.subject || 'Quiz';
	$('#q-count').textContent = `${String(idx+1).padStart(2,'0')}/${String(total).padStart(2,'0')}`;
	$('#quiz-progress').textContent = `${idx+1}/${total}`;
	$('#quiz-progress-bar').style.width = `${((idx)/total)*100}%`;
	const q = state.quiz.questions[idx];
	$('#q-text').textContent = q.question;
	const ans = $('#answers'); ans.innerHTML='';
	q.options.forEach((opt,i)=>{
		const b = document.createElement('button');
		b.className='answer'; b.textContent = opt; b.setAttribute('type','button');
		b.addEventListener('click',()=> selectAnswer(i));
		ans.appendChild(b);
	});
	$('#btn-submit-answer').disabled = true;
}
let selectedIndex = null;
function selectAnswer(i){
	selectedIndex = i;
	$$('.answer').forEach((b,idx)=>{ b.classList.toggle('selected', idx===i); });
	$('#btn-submit-answer').disabled = false;
}
async function submitAnswer(){
	const idx = state.quizProgress.index; if(selectedIndex==null) return;
	state.quizProgress.answers[idx] = state.quiz.questions[idx].options[selectedIndex];
	// Visual feedback
	$$('.answer').forEach((b,bi)=>{
		const correct = state.quiz.questions[idx].correctAnswer === state.quiz.questions[idx].options[bi];
		b.classList.add(bi===selectedIndex? (correct?'correct':'wrong') : 'disabled');
	});
	await new Promise(r=>setTimeout(r, 800));
	// Advance or submit whole quiz
	if(idx < state.quiz.questions.length-1){
		state.quizProgress.index++; selectedIndex=null; renderQuiz();
	}else{
		submitQuiz();
	}
}
async function submitQuiz(){
	try{
		const answers = state.quizProgress.answers;
		const res = await fetch(`${BASE_URL}/api/quiz/submit`, { method:'POST', headers:{ 'Content-Type':'application/json', ...authHeaders() }, body: JSON.stringify({ quizId: state.quiz.quizId || state.quiz.id || state.quiz.quizId, answers }) });
		if(!res.ok) throw new Error('Submit failed');
		const data = await res.json();
		renderResults(data); routeTo('results');
	}catch(e){ toast(e.message,'error'); }
}

/* Results */
function renderResults(result){
	const pct = result.score || 0;
	$('#result-head').textContent = pct>=80? 'Great Job! 🎉' : pct>=60? 'Nice Work! 💪' : 'Good Effort! 🚀';
	$('#points-earned').textContent = `+${formatNumber(result.pointsEarned||0)} points`;
	$('#streak-status').textContent = `Streak: ${result.streakIncremented? 'continued 🔥' : 'not continued'}`;
	// circle
	const svg = $('#score-svg'); svg.innerHTML='';
	const c = document.createElementNS('http://www.w3.org/2000/svg','circle'); c.setAttribute('cx','60'); c.setAttribute('cy','60'); c.setAttribute('r','54'); c.setAttribute('stroke','rgba(255,255,255,0.12)'); c.setAttribute('stroke-width','10'); c.setAttribute('fill','none'); svg.appendChild(c);
	const prog = document.createElementNS('http://www.w3.org/2000/svg','circle'); prog.setAttribute('cx','60'); prog.setAttribute('cy','60'); prog.setAttribute('r','54'); prog.setAttribute('stroke','#39ff14'); prog.setAttribute('stroke-width','10'); prog.setAttribute('fill','none'); prog.setAttribute('stroke-linecap','round'); prog.setAttribute('transform','rotate(-90 60 60)'); prog.style.strokeDasharray = `${2*Math.PI*54}`; prog.style.strokeDashoffset = `${2*Math.PI*54}`; svg.appendChild(prog);
	let cur = 0; const target = pct; const step = ()=>{ cur += Math.max(1, Math.round((target-cur)/10)); const frac = Math.min(cur, target)/100; prog.style.strokeDashoffset = `${(1-frac)*2*Math.PI*54}`; $('#score-text').textContent = `${Math.min(cur,target)}/100`; if(cur<target) requestAnimationFrame(step); }; requestAnimationFrame(step);
	const list = $('#results-list'); list.innerHTML='';
	(state.quiz?.questions||[]).forEach((q,i)=>{
		const it = document.createElement('div'); it.className = 'item';
		const your = state.quizProgress.answers[i];
		it.innerHTML = `<div><strong>Q${i+1}.</strong> ${q.question}</div><div>Your: <strong>${your||'-'}</strong> • Correct: <strong>${q.correctAnswer}</strong></div><div class="muted">${q.explanation||''}</div>`;
		list.appendChild(it);
	});
}

/* Leaderboard */
async function loadLeaderboard(period='daily'){
	state.leaderboard.period = period;
	$$('.page-leaderboard .tab').forEach(t=> t.classList.toggle('active', t.dataset.period===period));
	try{
		const res = await fetch(`${BASE_URL}/api/leaderboard/${period}`);
		const items = res.ok? await res.json(): [];
		renderLeaderboard(items);
		const rankRes = state.token? await fetch(`${BASE_URL}/api/leaderboard/rank`, { headers: { ...authHeaders() } }): null;
		if(rankRes && rankRes.ok){ const meta = await rankRes.json(); $('#rank-meta').textContent = `Your Rank: #${meta.currentRank} out of ${formatNumber(meta.totalUsers)}`; }
	}catch(_){/* */}
}
function renderLeaderboard(items){
	const body = $('#lb-body'); body.innerHTML='';
	(items||[]).forEach((u,i)=>{
		const tr = document.createElement('tr');
		const badge = i===0? '🥇' : i===1? '🥈' : i===2? '🥉' : '';
		tr.innerHTML = `<td>${i+1} ${badge}</td><td>${u.username||'User'}</td><td>${formatNumber(u.points||0)}</td><td>🔥 ${u.streak||0}</td><td>${Math.random()>0.5?'↑':'↓'}</td>`;
		body.appendChild(tr);
	});
}

/* Profile */
function loadProfile(){
	const stats = [
		{ label: 'Total Points', value: formatNumber(state.user?.totalPoints||0) },
		{ label: 'Current Streak', value: formatNumber(state.user?.currentStreak||0) },
		{ label: 'Longest Streak', value: formatNumber(state.user?.longestStreak||0) },
		{ label: 'Quizzes', value: '—' },
		{ label: 'Avg Score', value: '—' },
	];
	const grid = $('#profile-stats'); grid.innerHTML='';
	stats.forEach(s=>{ const c = document.createElement('div'); c.className='card'; c.innerHTML = `<div class="stat-title">${s.label}</div><div class="stat-value">${s.value}</div>`; grid.appendChild(c); });
	const badges = $('#badges'); badges.innerHTML='';
	Array.from({length:8}).forEach((_,i)=>{ const b = document.createElement('div'); b.className='badge'; b.textContent = `#${i+1}`; badges.appendChild(b); });
}

/* Header hydration */
function hydrateHeader(){
	$('#greeting-name').textContent = state.user?.username || 'Learner';
	$('#current-time').textContent = nowTime();
}

/* Events */
function bindEvents(){
	// Auth tabs
	$$('.auth-toggle .tab').forEach(t=> t.addEventListener('click',()=>{
		$$('.auth-toggle .tab').forEach(b=> b.classList.remove('active')); t.classList.add('active');
		const mode = t.dataset.tab; $('#login-form').classList.toggle('hidden', mode!=='login'); $('#signup-form').classList.toggle('hidden', mode!=='signup');
	}));
	$('#login-form').addEventListener('submit',(e)=>{ e.preventDefault(); const f = e.target; login(f.email.value.trim(), f.password.value.trim()); });
	$('#signup-form').addEventListener('submit',(e)=>{ e.preventDefault(); const f = e.target; signup(f.username.value.trim(), f.email.value.trim(), f.password.value.trim()); });
	$('#btn-logout')?.addEventListener('click', logout);
	$('#btn-start-quiz')?.addEventListener('click', ()=> startQuiz());
	$('#btn-continue')?.addEventListener('click', ()=> startQuiz());
	$('#btn-exit-quiz')?.addEventListener('click', ()=> routeTo('dashboard'));
	$('#btn-submit-answer')?.addEventListener('click', submitAnswer);
	$$('[data-nav]').forEach(b=> b.addEventListener('click',()=>{
		routeTo(b.dataset.nav);
		if(b.dataset.nav==='leaderboard') loadLeaderboard(state.leaderboard.period);
		if(b.dataset.nav==='profile') loadProfile();
	}));
	$$('.page-leaderboard .tab').forEach(t=> t.addEventListener('click',()=> loadLeaderboard(t.dataset.period)));
	setInterval(()=> $('#current-time') && ($('#current-time').textContent = nowTime()), 60000);
}

/* Init */
function init(){
	loadSession(); bindEvents(); initParticles(); hydrateHeader();
	if(state.user && state.token){ $('.page-auth').classList.add('hidden'); routeTo('dashboard'); loadDashboard(); }
	else { routeTo('auth'); }
}

document.addEventListener('DOMContentLoaded', init);

