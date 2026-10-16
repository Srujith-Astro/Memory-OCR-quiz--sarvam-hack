// MemoryRecall - Frontend Application Logic

let state = {
  currentView: 'home',
  dashboard: null,
  notes: [],
  filteredNotes: [],
  selectedSubject: '',
  reviewQueue: [],
  currentCardIndex: 0,
  isCardFlipped: false,
  sessionXp: 0,
  quizzes: [],
  currentQuiz: null,
  uploadedImage: null,
  generatedPackage: null,
  activeNoteId: null,
  theme: 'dark'
};

// Initialize Application on Page Load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadDashboard();
  setupKeyboardShortcuts();
  if (window.lucide) {
    window.lucide.createIcons();
  }
});

// ================= THEME MANAGEMENT =================
function initTheme() {
  const savedTheme = localStorage.getItem('mr_theme') || 'dark';
  applyTheme(savedTheme);
}

function toggleTheme() {
  const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
  applyTheme(newTheme);
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ theme: newTheme })
  }).catch(() => {});
}

function applyTheme(theme) {
  state.theme = theme;
  localStorage.setItem('mr_theme', theme);
  const icon = document.getElementById('theme-icon');
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
    document.body.classList.remove('bg-slate-50', 'text-slate-900');
    document.body.classList.add('bg-slate-950', 'text-slate-100');
    if (icon) icon.setAttribute('data-lucide', 'sun');
  } else {
    document.documentElement.classList.remove('dark');
    document.body.classList.remove('bg-slate-950', 'text-slate-100');
    document.body.classList.add('bg-slate-50', 'text-slate-900');
    if (icon) icon.setAttribute('data-lucide', 'moon');
  }
  if (window.lucide) window.lucide.createIcons();
}

// ================= NAVIGATION =================
function navigateView(viewName) {
  state.currentView = viewName;

  // Hide all views
  const views = ['home', 'knowledge', 'review', 'quizzes', 'progress', 'settings'];
  views.forEach(v => {
    const el = document.getElementById(`view-${v}`);
    if (el) el.classList.add('hidden');
  });

  // Show active view
  const activeEl = document.getElementById(`view-${viewName}`);
  if (activeEl) activeEl.classList.remove('hidden');

  // Update desktop sidebar buttons
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.classList.remove('bg-emerald-500/10', 'text-emerald-400', 'font-semibold');
    btn.classList.add('text-slate-400');
  });
  const activeNavBtn = document.getElementById(`nav-btn-${viewName}`);
  if (activeNavBtn) {
    activeNavBtn.classList.remove('text-slate-400');
    activeNavBtn.classList.add('bg-emerald-500/10', 'text-emerald-400', 'font-semibold');
  }

  // Load specific view data
  if (viewName === 'home') loadDashboard();
  if (viewName === 'knowledge') loadNotes();
  if (viewName === 'review') loadReviewQueue();
  if (viewName === 'quizzes') loadQuizzes();
  if (viewName === 'progress') loadProgress();
  if (viewName === 'settings') loadSettings();

  if (window.lucide) window.lucide.createIcons();
}

// ================= DASHBOARD & HOME =================
async function loadDashboard() {
  try {
    const res = await fetch('/api/dashboard');
    const data = await res.json();
    state.dashboard = data;
    renderDashboard(data);
  } catch (err) {
    console.error('Failed to load dashboard:', err);
  }
}

function renderDashboard(d) {
  // Top bar & Sidebar stats
  document.getElementById('top-xp-count').textContent = d.xp;
  document.getElementById('top-streak-count').textContent = d.streak_count;

  document.getElementById('sb-level-title').textContent = d.level_title;
  document.getElementById('sb-level-num').textContent = `Lvl ${d.level}`;
  document.getElementById('sb-xp-text').textContent = `${d.xp} XP`;
  document.getElementById('sb-next-xp').textContent = `${d.next_xp} XP`;

  const xpProgress = Math.min(100, Math.round(((d.xp - d.base_xp) / (d.next_xp - d.base_xp)) * 100));
  document.getElementById('sb-xp-bar').style.width = `${Math.max(5, xpProgress)}%`;

  // Home metrics
  document.getElementById('stat-cards-due').textContent = d.cards_due;
  document.getElementById('stat-new-cards').textContent = d.new_cards;
  document.getElementById('stat-streak').textContent = d.streak_count;
  document.getElementById('hero-due-count').textContent = `${d.cards_due} due`;

  document.getElementById('stat-goal-done').textContent = d.cards_reviewed_today;
  document.getElementById('stat-goal-target').textContent = d.daily_goal;
  const goalPercent = Math.min(100, Math.round((d.cards_reviewed_today / d.daily_goal) * 100));
  document.getElementById('stat-goal-bar').style.width = `${goalPercent}%`;

  // Review nav badge
  const dueBadge = document.getElementById('nav-badge-due');
  const mobBadge = document.getElementById('mob-badge-due');
  if (d.cards_due > 0) {
    dueBadge.textContent = d.cards_due;
    dueBadge.classList.remove('hidden');
    mobBadge.classList.remove('hidden');
  } else {
    dueBadge.classList.add('hidden');
    mobBadge.classList.add('hidden');
  }

  // Weekly Activity Chart
  renderWeeklyChart(d.weekly_activity);

  // Weak Topics
  renderWeakTopics(d.weak_topics);

  // Recent Notes
  renderRecentNotes(d.recent_notes);

  if (window.lucide) window.lucide.createIcons();
}

function renderWeeklyChart(activity) {
  const container = document.getElementById('weekly-chart');
  container.innerHTML = '';
  const maxCount = Math.max(5, ...activity.map(a => a.count));

  activity.forEach(a => {
    const heightPercent = Math.max(12, Math.round((a.count / maxCount) * 100));
    const isToday = a.date === new Date().toISOString().split('T')[0];
    const col = document.createElement('div');
    col.className = 'flex flex-col items-center gap-1.5 flex-1 h-full justify-end';
    col.innerHTML = `
      <span class="text-[10px] text-slate-500 font-bold">${a.count}</span>
      <div class="w-full max-w-[28px] rounded-t-lg transition-all duration-500 ${isToday ? 'bg-gradient-to-t from-emerald-600 to-teal-400 shadow-md shadow-emerald-500/20' : 'bg-slate-800'}" style="height: ${heightPercent}%"></div>
      <span class="text-[11px] ${isToday ? 'text-emerald-400 font-bold' : 'text-slate-400'}">${a.day}</span>
    `;
    container.appendChild(col);
  });
}

function renderWeakTopics(topics) {
  const container = document.getElementById('weak-topics-list');
  if (!topics || topics.length === 0) {
    container.innerHTML = `
      <div class="text-xs text-slate-400 text-center py-6 flex flex-col items-center gap-2">
        <i data-lucide="shield-check" class="w-6 h-6 text-emerald-400"></i>
        <span>High retention across all active topics!</span>
      </div>
    `;
    return;
  }

  container.innerHTML = topics.map(t => `
    <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
      <div>
        <div class="font-bold text-slate-200">${escapeHtml(t.subject)}</div>
        <div class="text-[10px] text-slate-500">${t.card_count} flashcards</div>
      </div>
      <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Needs Review</span>
    </div>
  `).join('');
}

function renderRecentNotes(notes) {
  const container = document.getElementById('home-recent-notes');
  if (!notes || notes.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 py-4 col-span-2 text-center">No notes captured yet. Click "Add Knowledge" to begin!</div>`;
    return;
  }

  container.innerHTML = notes.map(n => `
    <div onclick="viewNoteDetail(${n.id})" class="p-3.5 rounded-2xl bg-slate-950/60 hover:bg-slate-850/80 border border-slate-800/80 transition-all cursor-pointer flex items-center justify-between group">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl ${n.source_type === 'image' ? 'bg-orange-500/10 text-orange-400' : 'bg-emerald-500/10 text-emerald-400'} flex items-center justify-center shrink-0">
          <i data-lucide="${n.source_type === 'image' ? 'camera' : 'file-text'}" class="w-4 h-4"></i>
        </div>
        <div>
          <div class="font-bold text-xs text-slate-200 group-hover:text-emerald-400 transition-colors">${escapeHtml(n.title)}</div>
          <div class="text-[10px] text-slate-500 flex items-center gap-2 mt-0.5">
            <span>${escapeHtml(n.subject)}</span>
            <span>•</span>
            <span>${n.is_demo ? '<span class="text-blue-400">Sample Deck</span>' : 'My Note'}</span>
          </div>
        </div>
      </div>
      <i data-lucide="chevron-right" class="w-4 h-4 text-slate-600 group-hover:text-slate-300"></i>
    </div>
  `).join('');
}

// ================= MY KNOWLEDGE VIEW =================
async function loadNotes() {
  try {
    const res = await fetch('/api/notes');
    state.notes = await res.json();
    state.filteredNotes = [...state.notes];
    renderSubjectsFilter();
    renderNotesGrid();
  } catch (err) {
    console.error('Failed to load notes:', err);
  }
}

function renderSubjectsFilter() {
  const container = document.getElementById('subject-filters');
  const subjects = Array.from(new Set(state.notes.map(n => n.subject).filter(Boolean)));
  
  container.innerHTML = `
    <button onclick="filterNotesBySubject('')" class="subj-filter-btn px-3 py-1 rounded-lg text-xs font-semibold ${state.selectedSubject === '' ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'}">All</button>
  ` + subjects.map(s => `
    <button onclick="filterNotesBySubject('${escapeHtml(s)}')" class="subj-filter-btn px-3 py-1 rounded-lg text-xs font-semibold ${state.selectedSubject === s ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-white'}">${escapeHtml(s)}</button>
  `).join('');
}

function filterNotesBySubject(subj) {
  state.selectedSubject = subj;
  if (!subj) {
    state.filteredNotes = [...state.notes];
  } else {
    state.filteredNotes = state.notes.filter(n => n.subject === subj);
  }
  renderSubjectsFilter();
  renderNotesGrid();
}

function searchNotes(query) {
  const q = query.toLowerCase().trim();
  state.filteredNotes = state.notes.filter(n => {
    const matchSubj = !state.selectedSubject || n.subject === state.selectedSubject;
    const matchText = n.title.toLowerCase().includes(q) ||
                      (n.tags && n.tags.toLowerCase().includes(q)) ||
                      n.content.toLowerCase().includes(q);
    return matchSubj && matchText;
  });
  renderNotesGrid();
}

function renderNotesGrid() {
  const container = document.getElementById('notes-list');
  if (state.filteredNotes.length === 0) {
    container.innerHTML = `
      <div class="col-span-full text-center py-12 bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-xs space-y-2">
        <i data-lucide="book-open" class="w-8 h-8 mx-auto text-slate-600"></i>
        <div>No matching notes found. Capture your first note above!</div>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  container.innerHTML = state.filteredNotes.map(n => `
    <div onclick="viewNoteDetail(${n.id})" class="bg-slate-900/80 hover:bg-slate-850/90 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 cursor-pointer transition-all flex flex-col justify-between group shadow-sm">
      <div class="space-y-2.5">
        <div class="flex items-center justify-between text-[11px]">
          <span class="font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full">${escapeHtml(n.subject)}</span>
          <span class="text-slate-500 flex items-center gap-1">
            <i data-lucide="${n.source_type === 'image' ? 'camera' : 'type'}" class="w-3 h-3 text-orange-400"></i>
            ${n.source_type === 'image' ? 'OCR Note' : 'Text Note'}
          </span>
        </div>
        <h3 class="font-bold text-sm text-white group-hover:text-emerald-300 transition-colors line-clamp-1">${escapeHtml(n.title)}</h3>
        <p class="text-xs text-slate-400 line-clamp-3 leading-relaxed">${escapeHtml(n.content)}</p>
      </div>
      <div class="pt-4 mt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
        <div class="flex items-center gap-3">
          <span class="flex items-center gap-1"><i data-lucide="layers" class="w-3.5 h-3.5 text-emerald-400"></i> ${n.flashcard_count || 0} cards</span>
          <span class="flex items-center gap-1"><i data-lucide="award" class="w-3.5 h-3.5 text-teal-400"></i> ${n.quiz_count || 0} quizzes</span>
        </div>
        <span class="text-emerald-400 group-hover:translate-x-0.5 transition-transform">→</span>
      </div>
    </div>
  `).join('');

  if (window.lucide) window.lucide.createIcons();
}

// ================= NOTE DETAIL MODAL =================
async function viewNoteDetail(noteId) {
  try {
    const res = await fetch(`/api/notes/${noteId}`);
    const note = await res.json();
    state.activeNoteId = note.id;

    document.getElementById('nd-title').textContent = note.title;
    document.getElementById('nd-subject').textContent = note.subject;
    document.getElementById('nd-content').textContent = note.content;
    document.getElementById('nd-cards-count').textContent = note.flashcards?.length || 0;
    document.getElementById('nd-quizzes-count').textContent = note.quizzes?.length || 0;

    const imgContainer = document.getElementById('nd-image-container');
    const imgEl = document.getElementById('nd-image');
    if (note.image_path) {
      imgEl.src = note.image_path;
      imgContainer.classList.remove('hidden');
    } else {
      imgContainer.classList.add('hidden');
    }

    document.getElementById('note-detail-modal').classList.remove('hidden');
    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    showToast('Failed to load note details', 'error');
  }
}

function closeNoteDetailModal() {
  document.getElementById('note-detail-modal').classList.add('hidden');
  state.activeNoteId = null;
}

async function deleteCurrentNote() {
  if (!state.activeNoteId) return;
  if (!confirm('Are you sure you want to delete this note and its study cards?')) return;

  try {
    await fetch(`/api/notes/${state.activeNoteId}`, { method: 'DELETE' });
    closeNoteDetailModal();
    showToast('Note deleted successfully', 'success');
    loadNotes();
    loadDashboard();
  } catch (err) {
    showToast('Failed to delete note', 'error');
  }
}

function practiceFromNote() {
  closeNoteDetailModal();
  startReviewSession();
}

// ================= ACTIVE RECALL & REVIEW (SM-2) =================
async function loadReviewQueue(subject = '') {
  try {
    const url = subject ? `/api/review/queue?subject=${encodeURIComponent(subject)}` : '/api/review/queue';
    const res = await fetch(url);
    state.reviewQueue = await res.json();
    state.currentCardIndex = 0;
    state.isCardFlipped = false;
    state.sessionXp = 0;

    renderReviewArea();
  } catch (err) {
    console.error('Failed to load review queue:', err);
  }
}

function startReviewSession() {
  navigateView('review');
}

function renderReviewArea() {
  const cardArea = document.getElementById('review-card-area');
  const buttonsBar = document.getElementById('review-buttons-bar');
  const completeState = document.getElementById('review-complete-state');
  const counter = document.getElementById('review-counter');
  const progressBar = document.getElementById('review-progress-bar');
  const sessionXp = document.getElementById('review-session-xp');

  sessionXp.textContent = `+${state.sessionXp} XP`;

  if (state.reviewQueue.length === 0 || state.currentCardIndex >= state.reviewQueue.length) {
    cardArea.classList.add('hidden');
    buttonsBar.classList.add('hidden');
    completeState.classList.remove('hidden');
    counter.textContent = 'Session Complete';
    progressBar.style.width = '100%';
    return;
  }

  cardArea.classList.remove('hidden');
  buttonsBar.classList.remove('hidden');
  completeState.classList.add('hidden');

  const card = state.reviewQueue[state.currentCardIndex];
  counter.textContent = `Card ${state.currentCardIndex + 1} of ${state.reviewQueue.length}`;
  const pct = Math.round(((state.currentCardIndex) / state.reviewQueue.length) * 100);
  progressBar.style.width = `${Math.max(5, pct)}%`;

  // Reset flip
  state.isCardFlipped = false;
  document.getElementById('flashcard-element').classList.remove('is-flipped');

  // Populate front & back
  document.getElementById('card-front-subject').textContent = card.subject || 'General';
  document.getElementById('card-front-question').textContent = card.question;

  document.getElementById('card-back-subject').textContent = card.subject || 'Solution';
  document.getElementById('card-back-answer').textContent = card.answer;
  document.getElementById('card-back-explanation').textContent = card.explanation || 'No extra explanation provided.';

  if (window.lucide) window.lucide.createIcons();
}

function toggleCardFlip() {
  const el = document.getElementById('flashcard-element');
  state.isCardFlipped = !state.isCardFlipped;
  if (state.isCardFlipped) {
    el.classList.add('is-flipped');
  } else {
    el.classList.remove('is-flipped');
  }
}

async function submitReview(grade) {
  if (state.currentCardIndex >= state.reviewQueue.length) return;
  const card = state.reviewQueue[state.currentCardIndex];

  try {
    const res = await fetch(`/api/flashcards/${card.id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ grade })
    });
    const result = await res.json();

    state.sessionXp += result.xp_earned;
    showXpPop(`+${result.xp_earned} XP`);

    // Move to next card
    state.currentCardIndex++;
    if (state.currentCardIndex >= state.reviewQueue.length) {
      triggerConfetti();
      showToast(`Great session! You earned ${state.sessionXp} Knowledge XP!`, 'success');
      loadDashboard();
    }

    renderReviewArea();
  } catch (err) {
    showToast('Failed to record review grade', 'error');
  }
}

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Only handle when on review view and no modal is open
    if (state.currentView !== 'review') return;
    if (!document.getElementById('add-modal').classList.contains('hidden')) return;
    if (!document.getElementById('note-detail-modal').classList.contains('hidden')) return;

    if (e.code === 'Space') {
      e.preventDefault();
      toggleCardFlip();
    } else if (state.isCardFlipped) {
      if (e.key === '1') submitReview('again');
      if (e.key === '2') submitReview('hard');
      if (e.key === '3') submitReview('good');
      if (e.key === '4') submitReview('easy');
    }
  });
}

// ================= QUIZZES =================
async function loadQuizzes() {
  try {
    const res = await fetch('/api/quizzes');
    state.quizzes = await res.json();
    renderQuizzesList();
  } catch (err) {
    console.error('Failed to load quizzes:', err);
  }
}

function renderQuizzesList() {
  const container = document.getElementById('quizzes-list');
  if (state.quizzes.length === 0) {
    container.innerHTML = `
      <div class="col-span-full text-center py-12 bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-xs">
        No quizzes available yet. Generate quizzes when adding knowledge notes!
      </div>
    `;
    return;
  }

  container.innerHTML = state.quizzes.map((q, idx) => {
    const accuracy = q.times_attempted > 0 ? Math.round((q.times_correct / q.times_attempted) * 100) : null;
    return `
      <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-3">
        <div class="space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full">${escapeHtml(q.subject)}</span>
            <span class="text-slate-500 text-[11px]">${accuracy !== null ? `${accuracy}% Accuracy` : 'Not attempted'}</span>
          </div>
          <h3 class="font-bold text-sm text-white line-clamp-2">${escapeHtml(q.question)}</h3>
          <div class="text-[11px] text-slate-400">4 multiple-choice choices</div>
        </div>
        <button onclick="startQuiz(${idx})" class="w-full bg-slate-800 hover:bg-emerald-500 hover:text-slate-950 text-slate-200 font-bold py-2 rounded-xl text-xs transition-colors flex items-center justify-center gap-2">
          <i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>
          <span>Practice Question (+25 XP)</span>
        </button>
      </div>
    `;
  }).join('');

  if (window.lucide) window.lucide.createIcons();
}

function startQuiz(quizIndex) {
  state.currentQuiz = state.quizzes[quizIndex];
  const q = state.currentQuiz;

  document.getElementById('qp-subject').textContent = q.subject;
  document.getElementById('qp-question').textContent = q.question;
  document.getElementById('qp-explanation-box').classList.add('hidden');
  document.getElementById('qp-next-btn').classList.add('hidden');
  document.getElementById('qp-xp-alert').textContent = '';

  const optContainer = document.getElementById('qp-options-container');
  optContainer.innerHTML = q.options.map((opt, i) => `
    <button onclick="selectQuizOption(${i})" class="quiz-opt-btn w-full text-left p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-xs text-slate-200 transition-colors flex items-center gap-3">
      <span class="w-6 h-6 rounded-lg bg-slate-800 flex items-center justify-center font-bold text-slate-300 text-[11px] shrink-0">${String.fromCharCode(65 + i)}</span>
      <span class="flex-1">${escapeHtml(opt)}</span>
    </button>
  `).join('');

  document.getElementById('quiz-player-modal').classList.remove('hidden');
  if (window.lucide) window.lucide.createIcons();
}

function closeQuizPlayer() {
  document.getElementById('quiz-player-modal').classList.add('hidden');
  state.currentQuiz = null;
  loadQuizzes();
}

async function selectQuizOption(selectedIndex) {
  if (!state.currentQuiz) return;
  const q = state.currentQuiz;

  // Disable all option buttons
  const buttons = document.querySelectorAll('.quiz-opt-btn');
  buttons.forEach(b => b.disabled = true);

  try {
    const res = await fetch(`/api/quizzes/${q.id}/attempt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_index: selectedIndex })
    });
    const result = await res.json();

    // Style the buttons
    buttons.forEach((b, idx) => {
      if (idx === result.correct_index) {
        b.classList.remove('bg-slate-950', 'border-slate-800');
        b.classList.add('bg-emerald-500/20', 'border-emerald-500', 'text-emerald-300', 'font-bold');
      } else if (idx === selectedIndex && !result.is_correct) {
        b.classList.remove('bg-slate-950', 'border-slate-800');
        b.classList.add('bg-rose-500/20', 'border-rose-500', 'text-rose-300');
      }
    });

    // Reveal explanation
    document.getElementById('qp-explanation-text').textContent = result.explanation;
    document.getElementById('qp-explanation-box').classList.remove('hidden');

    if (result.is_correct) {
      document.getElementById('qp-xp-alert').textContent = `Correct! +${result.xp_earned} XP earned! 🎉`;
      triggerConfetti();
    } else {
      document.getElementById('qp-xp-alert').textContent = `Keep going! +${result.xp_earned} XP for practice.`;
    }

    document.getElementById('qp-next-btn').classList.remove('hidden');
    loadDashboard();
  } catch (err) {
    showToast('Failed to record quiz answer', 'error');
  }
}

function nextQuizQuestion() {
  closeQuizPlayer();
}

// ================= PROGRESS & MASTERY =================
async function loadProgress() {
  try {
    const res = await fetch('/api/progress');
    const data = await res.json();
    renderProgress(data);
  } catch (err) {
    console.error('Failed to load progress:', err);
  }
}

function renderProgress(d) {
  document.getElementById('prog-level-title').textContent = d.level_title;
  document.getElementById('prog-level-tag').textContent = `Level ${d.level}`;
  document.getElementById('prog-xp-val').textContent = d.xp;
  document.getElementById('prog-xp-text').textContent = `${d.xp} XP`;
  document.getElementById('prog-next-xp-text').textContent = `${d.next_xp} XP`;

  const xpProgress = Math.min(100, Math.round(((d.xp - d.base_xp) / (d.next_xp - d.base_xp)) * 100));
  document.getElementById('prog-xp-bar').style.width = `${Math.max(5, xpProgress)}%`;

  // Mastery breakdown
  const masteryContainer = document.getElementById('progress-mastery-list');
  if (d.mastery.length === 0) {
    masteryContainer.innerHTML = `<div class="text-xs text-slate-500">No flashcards created yet.</div>`;
  } else {
    masteryContainer.innerHTML = d.mastery.map(m => {
      const masteredPct = Math.round((m.mastered_cards / m.total_cards) * 100);
      const learningPct = Math.round((m.learning_cards / m.total_cards) * 100);
      return `
        <div class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold text-slate-200">${escapeHtml(m.subject)}</span>
            <span class="text-slate-400 text-[11px]">${m.total_cards} cards (${m.mastered_cards} mastered)</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-2 flex overflow-hidden">
            <div class="bg-emerald-500 h-2" style="width: ${masteredPct}%" title="Mastered"></div>
            <div class="bg-blue-500 h-2" style="width: ${learningPct}%" title="Learning"></div>
          </div>
          <div class="flex gap-4 text-[10px] text-slate-500">
            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-emerald-500"></span> Mastered (${m.mastered_cards})</span>
            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-blue-500"></span> In Review (${m.learning_cards})</span>
            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-slate-700"></span> New (${m.new_cards})</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // Badges Shelf
  const badgesContainer = document.getElementById('badges-grid');
  badgesContainer.innerHTML = d.badges.map(b => `
    <div class="p-3.5 rounded-2xl border ${b.unlocked ? 'bg-gradient-to-b from-amber-500/10 to-slate-900 border-amber-500/30' : 'bg-slate-950/40 border-slate-800/60 opacity-50'} text-center flex flex-col items-center justify-center space-y-2">
      <div class="w-10 h-10 rounded-xl ${b.unlocked ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-600'} flex items-center justify-center">
        <i data-lucide="${b.icon}" class="w-5 h-5"></i>
      </div>
      <div>
        <div class="font-bold text-xs ${b.unlocked ? 'text-white' : 'text-slate-400'}">${escapeHtml(b.title)}</div>
        <div class="text-[10px] text-slate-500 leading-tight mt-0.5">${escapeHtml(b.desc)}</div>
      </div>
      <span class="text-[9px] font-bold px-2 py-0.5 rounded-full ${b.unlocked ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-500'}">
        ${b.unlocked ? 'Unlocked' : 'Locked'}
      </span>
    </div>
  `).join('');

  if (window.lucide) window.lucide.createIcons();
}

// ================= SETTINGS =================
async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const s = await res.json();
    if (s.daily_goal) {
      document.getElementById('setting-daily-goal').value = s.daily_goal;
    }
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

async function updateDailyGoal(val) {
  try {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ daily_goal: parseInt(val) })
    });
    showToast('Daily study goal updated', 'success');
    loadDashboard();
  } catch (err) {
    showToast('Failed to update goal', 'error');
  }
}

async function exportDataBackup() {
  window.open('/api/export', '_blank');
}

async function resetDemoData() {
  if (!confirm('Reset local database to sample demo data? Any custom notes will be replaced.')) return;
  try {
    await fetch('/api/settings/reset-demo', { method: 'POST' });
    showToast('Sample data restored', 'success');
    loadDashboard();
    loadNotes();
  } catch (err) {
    showToast('Failed to reset demo data', 'error');
  }
}

// ================= ADD KNOWLEDGE MODAL (CAPTURE WORKFLOW) =================
function openAddModal(tab = 'text') {
  document.getElementById('add-modal').classList.remove('hidden');
  switchAddTab(tab);
  resetAddForm();
  if (window.lucide) window.lucide.createIcons();
}

function closeAddModal() {
  document.getElementById('add-modal').classList.add('hidden');
  resetAddForm();
}

function switchAddTab(tab) {
  state.activeAddTab = tab;
  const btnText = document.getElementById('tab-btn-text');
  const btnPhoto = document.getElementById('tab-btn-photo');
  const tabText = document.getElementById('add-tab-text');
  const tabPhoto = document.getElementById('add-tab-photo');

  if (tab === 'text') {
    btnText.className = 'pb-3 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-2';
    btnPhoto.className = 'pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2';
    tabText.classList.remove('hidden');
    tabPhoto.classList.add('hidden');
  } else {
    btnPhoto.className = 'pb-3 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-2';
    btnText.className = 'pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2';
    tabPhoto.classList.remove('hidden');
    tabText.classList.add('hidden');
  }
  if (window.lucide) window.lucide.createIcons();
}

function resetAddForm() {
  document.getElementById('add-input-title').value = '';
  document.getElementById('add-input-subject').value = '';
  document.getElementById('add-input-tags').value = '';
  document.getElementById('add-input-content').value = '';
  document.getElementById('ocr-editable-text').value = '';
  document.getElementById('ocr-preview-img').src = '';
  document.getElementById('ocr-result-area').classList.add('hidden');
  document.getElementById('ocr-spinner').classList.add('hidden');
  document.getElementById('generated-preview-area').classList.add('hidden');
  document.getElementById('btn-save-package').classList.add('hidden');
  document.getElementById('btn-generate-ai').classList.remove('hidden');
  state.uploadedImage = null;
  state.generatedPackage = null;
}

// Handle Photo Upload & Sarvam OCR
async function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('content_type', document.getElementById('ocr-content-type').value);
  formData.append('language', document.getElementById('ocr-language').value);

  document.getElementById('ocr-spinner').classList.remove('hidden');
  document.getElementById('ocr-result-area').classList.add('hidden');

  try {
    const res = await fetch('/api/ocr', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    document.getElementById('ocr-spinner').classList.add('hidden');

    state.uploadedImage = data;
    document.getElementById('ocr-preview-img').src = data.image_path;
    document.getElementById('ocr-editable-text').value = data.full_text || '';
    document.getElementById('ocr-result-area').classList.remove('hidden');

    if (data.success) {
      showToast('Sarvam Doc AI extracted note text successfully!', 'success');
      // Auto populate title if empty
      if (!document.getElementById('add-input-title').value) {
        document.getElementById('add-input-title').value = file.name.replace(/\.[^/.]+$/, "");
      }
    } else {
      showToast(data.message || 'OCR issue encountered. Image preserved for manual input.', 'error');
    }
  } catch (err) {
    document.getElementById('ocr-spinner').classList.add('hidden');
    showToast('Failed to connect to Sarvam OCR endpoint', 'error');
  }
}

// Run AI Study Generation (Sarvam LLM)
async function runAiGeneration() {
  const title = document.getElementById('add-input-title').value.trim();
  const subject = document.getElementById('add-input-subject').value.trim() || 'General';
  
  // Decide active text based on tab
  let text = '';
  if (state.activeAddTab === 'text') {
    text = document.getElementById('add-input-content').value.trim();
  } else {
    text = document.getElementById('ocr-editable-text').value.trim();
  }

  if (!text || text.length < 10) {
    showToast('Please provide at least 10 characters of study notes.', 'error');
    return;
  }

  const btn = document.getElementById('btn-generate-ai');
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="inline-block w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span> Generating with Sarvam...`;
  btn.disabled = true;

  const targetLanguage = document.getElementById('add-input-language')?.value || 'auto';

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        num_cards: 4,
        num_quizzes: 2,
        subject,
        target_language: targetLanguage
      })
    });
    const data = await res.json();
    state.generatedPackage = data;

    renderGeneratedPreview(data);
    document.getElementById('btn-save-package').classList.remove('hidden');
    document.getElementById('btn-generate-ai').classList.add('hidden');
    showToast('Study materials generated! Review and save below.', 'success');
  } catch (err) {
    showToast('Failed to generate study materials: ' + err.message, 'error');
  } finally {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    if (window.lucide) window.lucide.createIcons();
  }
}

function renderGeneratedPreview(data) {
  const container = document.getElementById('generated-preview-area');
  container.classList.remove('hidden');

  document.getElementById('gen-cards-count').textContent = data.flashcards.length;
  document.getElementById('gen-quiz-count').textContent = data.quizzes.length;

  const cardsList = document.getElementById('gen-cards-list');
  cardsList.innerHTML = data.flashcards.map((c, i) => `
    <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
      <div class="font-bold text-white">Q: ${escapeHtml(c.question)}</div>
      <div class="text-emerald-400">A: ${escapeHtml(c.answer)}</div>
    </div>
  `).join('');

  const quizList = document.getElementById('gen-quizzes-list');
  quizList.innerHTML = data.quizzes.map((q, i) => `
    <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
      <div class="font-bold text-white">${escapeHtml(q.question)}</div>
      <div class="text-slate-400 text-[11px]">Correct: ${escapeHtml(q.options[q.answer_index])}</div>
    </div>
  `).join('');
}

// Save complete study package to database
async function saveStudyPackage() {
  const title = document.getElementById('add-input-title').value.trim() || 'Untitled Study Note';
  const subject = document.getElementById('add-input-subject').value.trim() || 'General';
  const tags = document.getElementById('add-input-tags').value.trim();

  let content = '';
  let imagePath = null;
  let rawOcrText = null;
  let ocrBlocks = null;
  const sourceType = state.activeAddTab === 'photo' ? 'image' : 'text';

  if (sourceType === 'image') {
    content = document.getElementById('ocr-editable-text').value.trim();
    if (state.uploadedImage) {
      imagePath = state.uploadedImage.image_path;
      rawOcrText = state.uploadedImage.full_text;
      ocrBlocks = JSON.stringify(state.uploadedImage.blocks || []);
    }
  } else {
    content = document.getElementById('add-input-content').value.trim();
  }

  const payload = {
    title,
    subject,
    tags,
    source_type: sourceType,
    image_path: imagePath,
    raw_ocr_text: rawOcrText,
    ocr_blocks_json: ocrBlocks,
    content,
    flashcards: state.generatedPackage?.flashcards || [],
    quizzes: state.generatedPackage?.quizzes || []
  };

  try {
    const res = await fetch('/api/notes/save-generated', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    closeAddModal();
    triggerConfetti();
    showToast(`Saved! +${result.xp_awarded} XP earned!`, 'success');
    loadDashboard();
    loadNotes();
  } catch (err) {
    showToast('Failed to save study package', 'error');
  }
}

// ================= UTILITIES & FEEDBACK =================
function triggerConfetti() {
  if (typeof confetti === 'function') {
    confetti({
      particleCount: 50,
      spread: 60,
      origin: { y: 0.7 }
    });
  }
}

function showXpPop(text) {
  const el = document.createElement('div');
  el.className = 'xp-float text-sm font-extrabold';
  el.textContent = text;
  el.style.left = '50%';
  el.style.top = '40%';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1200);
}

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  const bg = type === 'error' ? 'bg-rose-500' : (type === 'success' ? 'bg-emerald-600' : 'bg-slate-800');
  toast.className = `${bg} text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-lg shadow-black/30 pointer-events-auto flex items-center gap-2 transition-all duration-300 transform translate-y-2 opacity-0`;
  toast.textContent = msg;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[m]);
}
