// ─── State ───────────────────────────────────────────────
let currentProfile = null;
let currentStep = 1;
const TOTAL_STEPS = 4;

const wizardData = {
  username: '', display_name: '', state: '', city: '',
  experience: 'enthusiast', use_type: 'recreational',
  tolerance: 'medium', budget: 'mid',
  preferred_types: [], preferred_effects: [], flavor_profiles: [],
  favorite_strains: [], avoid: ''
};

// ─── US States ───────────────────────────────────────────
const US_STATES = [
  ['AL','Alabama'],['AK','Alaska'],['AZ','Arizona'],['AR','Arkansas'],
  ['CA','California'],['CO','Colorado'],['CT','Connecticut'],['DE','Delaware'],
  ['DC','District of Columbia'],['FL','Florida'],['GA','Georgia'],['HI','Hawaii'],
  ['ID','Idaho'],['IL','Illinois'],['IN','Indiana'],['IA','Iowa'],
  ['KS','Kansas'],['KY','Kentucky'],['LA','Louisiana'],['ME','Maine'],
  ['MD','Maryland'],['MA','Massachusetts'],['MI','Michigan'],['MN','Minnesota'],
  ['MS','Mississippi'],['MO','Missouri'],['MT','Montana'],['NE','Nebraska'],
  ['NV','Nevada'],['NH','New Hampshire'],['NJ','New Jersey'],['NM','New Mexico'],
  ['NY','New York'],['NC','North Carolina'],['ND','North Dakota'],['OH','Ohio'],
  ['OK','Oklahoma'],['OR','Oregon'],['PA','Pennsylvania'],['RI','Rhode Island'],
  ['SC','South Carolina'],['SD','South Dakota'],['TN','Tennessee'],['TX','Texas'],
  ['UT','Utah'],['VT','Vermont'],['VA','Virginia'],['WA','Washington'],
  ['WV','West Virginia'],['WI','Wisconsin'],['WY','Wyoming']
];

// ─── Init ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  buildStateSelect();
  setupWizardEvents();
  setupChatEvents();
  await checkProfile();
});

async function checkProfile() {
  const res = await fetch('/api/profile');
  const data = await res.json();
  if (data.profile) {
    currentProfile = data.profile;
    showApp();
  } else {
    showWizard();
  }
}

function buildStateSelect() {
  const sel = document.getElementById('state-select');
  sel.innerHTML = '<option value="">Select your state...</option>';
  US_STATES.forEach(([code, name]) => {
    sel.innerHTML += `<option value="${code}">${name}</option>`;
  });
}

// ─── Wizard ──────────────────────────────────────────────
function showWizard() {
  document.getElementById('wizard').classList.remove('hidden');
  document.getElementById('app').classList.remove('visible');
  updateProgress();
}

function showApp() {
  document.getElementById('wizard').classList.add('hidden');
  document.getElementById('app').classList.add('visible');
  renderProfile();
  showEmptyState();
}

function updateProgress() {
  document.querySelectorAll('.progress-dot').forEach((dot, i) => {
    dot.classList.remove('active', 'done');
    if (i + 1 === currentStep) dot.classList.add('active');
    else if (i + 1 < currentStep) dot.classList.add('done');
  });

  // Show/hide steps
  document.querySelectorAll('.wizard-step').forEach((step, i) => {
    step.classList.toggle('active', i + 1 === currentStep);
  });

  // Nav buttons
  const backBtn = document.getElementById('wizard-back');
  const nextBtn = document.getElementById('wizard-next');
  backBtn.classList.toggle('hidden', currentStep === 1);
  nextBtn.textContent = currentStep === TOTAL_STEPS ? 'Get Started' : 'Next';
}

function setupWizardEvents() {
  // Radio cards
  document.querySelectorAll('.radio-card').forEach(card => {
    card.addEventListener('click', () => {
      const group = card.dataset.group;
      document.querySelectorAll(`.radio-card[data-group="${group}"]`)
        .forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      wizardData[group] = card.dataset.value;
    });
  });

  // Chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('selected');
      const field = chip.dataset.field;
      const val = chip.dataset.value;
      if (chip.classList.contains('selected')) {
        if (!wizardData[field].includes(val)) wizardData[field].push(val);
      } else {
        wizardData[field] = wizardData[field].filter(v => v !== val);
      }
    });
  });

  // Nav
  document.getElementById('wizard-back').addEventListener('click', () => {
    if (currentStep > 1) { currentStep--; updateProgress(); }
  });

  document.getElementById('wizard-next').addEventListener('click', async () => {
    if (!validateStep()) return;
    collectStep();

    if (currentStep < TOTAL_STEPS) {
      currentStep++;
      updateProgress();
    } else {
      await submitProfile();
    }
  });
}

function validateStep() {
  if (currentStep === 1) {
    const username = document.getElementById('username-input').value.trim();
    const state = document.getElementById('state-select').value;
    if (!username) { shake('username-input'); return false; }
    if (!state) { shake('state-select'); return false; }
  }
  return true;
}

function collectStep() {
  if (currentStep === 1) {
    wizardData.username = document.getElementById('username-input').value.trim();
    wizardData.display_name = document.getElementById('display-name-input').value.trim()
      || wizardData.username;
    wizardData.state = document.getElementById('state-select').value;
    wizardData.city = document.getElementById('city-input').value.trim();
  }
  if (currentStep === 4) {
    wizardData.favorite_strains = document.getElementById('fav-strains-input').value
      .split(',').map(s => s.trim()).filter(Boolean);
    wizardData.avoid = document.getElementById('avoid-input').value.trim();
  }
}

async function submitProfile() {
  const nextBtn = document.getElementById('wizard-next');
  nextBtn.disabled = true;
  nextBtn.textContent = 'Setting up...';

  const res = await fetch('/api/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(wizardData)
  });

  const data = await res.json();
  nextBtn.disabled = false;

  if (data.success) {
    currentProfile = data.profile;
    showApp();
  } else {
    showToast(data.error || 'Something went wrong');
    nextBtn.textContent = 'Get Started';
  }
}

function shake(id) {
  const el = document.getElementById(id);
  el.style.borderColor = '#ef4444';
  el.animate([
    { transform: 'translateX(-4px)' }, { transform: 'translateX(4px)' },
    { transform: 'translateX(-4px)' }, { transform: 'translateX(0)' }
  ], { duration: 250 });
  setTimeout(() => { el.style.borderColor = ''; }, 1500);
}

// ─── Profile Sidebar ─────────────────────────────────────
function renderProfile() {
  if (!currentProfile) return;
  const p = currentProfile;

  document.getElementById('profile-avatar').textContent =
    (p.display_name || p.username || 'U')[0].toUpperCase();

  document.getElementById('profile-name').textContent =
    p.display_name || p.username;

  document.getElementById('profile-location').textContent =
    [p.city, p.state].filter(Boolean).join(', ') || 'Location not set';

  const badgesEl = document.getElementById('profile-badges');
  const expLabel = { beginner: 'Beginner', enthusiast: 'Enthusiast', connoisseur: 'Connoisseur', expert: 'Expert' };
  const budgetLabel = { budget: 'Budget', mid: 'Mid-tier', premium: 'Premium', topshelf: 'Top-shelf' };

  badgesEl.innerHTML = `
    <span class="badge green">${expLabel[p.experience] || p.experience}</span>
    <span class="badge">${budgetLabel[p.budget] || p.budget}</span>
    <span class="badge">${p.tolerance} tolerance</span>
  `;
}

// ─── Chat ────────────────────────────────────────────────
function showEmptyState() {
  const messagesEl = document.getElementById('messages');
  const name = currentProfile?.display_name || currentProfile?.username || '';

  messagesEl.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon">🌿</div>
      <h3>Hey${name ? ', ' + name : ''}. What are you hunting for?</h3>
      <p>I know the US cannabis market inside out — strains, dispensaries, terpenes, concentrates. Ask me anything.</p>
      <div class="empty-suggestions">
        <button class="suggestion-pill" onclick="sendQuick(this)">Best dispensaries near me</button>
        <button class="suggestion-pill" onclick="sendQuick(this)">Recommend me a strain for tonight</button>
        <button class="suggestion-pill" onclick="sendQuick(this)">What's the best live rosin right now?</button>
        <button class="suggestion-pill" onclick="sendQuick(this)">Explain terpenes to me</button>
        <button class="suggestion-pill" onclick="sendQuick(this)">Top craft growers in my state</button>
      </div>
    </div>
  `;
}

function sendQuick(btn) {
  const msg = btn.textContent;
  document.getElementById('message-input').value = msg;
  sendMessage();
}

function setupChatEvents() {
  const input = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-btn');

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
    sendBtn.disabled = !input.value.trim();
  });

  sendBtn.addEventListener('click', sendMessage);

  // Sidebar buttons
  document.getElementById('new-chat-btn').addEventListener('click', newChat);
  document.getElementById('new-chat-sidebar-btn').addEventListener('click', newChat);
  document.getElementById('edit-profile-btn').addEventListener('click', editProfile);
  document.getElementById('logout-btn').addEventListener('click', logout);

  // Quick actions
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('message-input').value = btn.dataset.prompt;
      sendMessage();
    });
  });
}

async function sendMessage() {
  const input = document.getElementById('message-input');
  const text = input.value.trim();
  if (!text) return;

  // Clear empty state
  const emptyState = document.querySelector('.empty-state');
  if (emptyState) emptyState.remove();

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;

  appendMessage('user', text);
  const typingEl = appendTyping();
  scrollToBottom();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });

    const data = await res.json();
    typingEl.remove();

    if (data.error) {
      showToast(data.error);
    } else {
      appendMessage('assistant', data.response);
    }
  } catch (err) {
    typingEl.remove();
    showToast('Connection error. Try again.');
  }

  scrollToBottom();
}

function appendMessage(role, text) {
  const messagesEl = document.getElementById('messages');

  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;

  const roleLabel = role === 'user' ? 'You' : 'CannaGuide';
  const content = role === 'assistant' ? marked.parse(text) : escapeHtml(text);

  wrap.innerHTML = `
    <div class="message-role">${roleLabel}</div>
    <div class="message-bubble">${content}</div>
  `;

  messagesEl.appendChild(wrap);
  return wrap;
}

function appendTyping() {
  const messagesEl = document.getElementById('messages');
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.innerHTML = `
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
    <span>CannaGuide is sourcing...</span>
  `;
  messagesEl.appendChild(el);
  return el;
}

function scrollToBottom() {
  const el = document.getElementById('messages');
  el.scrollTop = el.scrollHeight;
}

async function newChat() {
  await fetch('/api/new-chat', { method: 'POST' });
  showEmptyState();
}

function editProfile() {
  currentStep = 1;
  showWizard();
  updateProgress();

  // Pre-fill wizard with existing data
  if (currentProfile) {
    const p = currentProfile;
    document.getElementById('username-input').value = p.username || '';
    document.getElementById('display-name-input').value = p.display_name || '';
    document.getElementById('state-select').value = p.state || '';
    document.getElementById('city-input').value = p.city || '';

    // Restore radio cards
    ['experience', 'use_type', 'tolerance', 'budget'].forEach(field => {
      const val = p[field];
      document.querySelectorAll(`.radio-card[data-group="${field}"]`).forEach(c => {
        c.classList.toggle('selected', c.dataset.value === val);
      });
      wizardData[field] = val || wizardData[field];
    });

    // Restore chips
    ['preferred_types', 'preferred_effects', 'flavor_profiles'].forEach(field => {
      const vals = p[field] || [];
      wizardData[field] = [...vals];
      document.querySelectorAll(`.chip[data-field="${field}"]`).forEach(c => {
        c.classList.toggle('selected', vals.includes(c.dataset.value));
      });
    });

    wizardData.favorite_strains = p.favorite_strains || [];
    wizardData.avoid = p.avoid || '';
  }
}

async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  currentProfile = null;
  currentStep = 1;
  document.getElementById('messages').innerHTML = '';
  showWizard();
  updateProgress();
}

// ─── Utils ───────────────────────────────────────────────
function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/\n/g, '<br>');
}

function showToast(msg) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
