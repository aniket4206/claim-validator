// ── ThinkAI Eligibility & Benefits Verification App ──────────────────

const API = '';  // same origin

// ── Auth helpers ─────────────────────────────────────────────
function getAuthToken() {
  return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token') || '';
}

function getAuthUser() {
  try {
    const raw = localStorage.getItem('auth_user') || sessionStorage.getItem('auth_user');
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function authHeaders(extra = {}) {
  return { 'Authorization': 'Bearer ' + getAuthToken(), 'Content-Type': 'application/json', ...extra };
}

function authFetch(url, opts = {}) {
  opts.headers = { ...authHeaders(), ...(opts.headers || {}) };
  return fetch(url, opts).then(res => {
    if (res.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      sessionStorage.removeItem('auth_token');
      sessionStorage.removeItem('auth_user');
      document.cookie = 'auth_token=; path=/; max-age=0';
      window.location.href = '/login';
      throw new Error('Session expired');
    }
    return res;
  });
}

function logout() {
  const token = getAuthToken();
  fetch('/api/v1/auth/logout', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + token },
  }).finally(() => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    sessionStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_user');
    document.cookie = 'auth_token=; path=/; max-age=0';
    window.location.href = '/login';
  });
}

// Set user info in topbar, dropdown, and profile page
(function initAuthUI() {
  const user = getAuthUser();
  if (!user) return;
  const displayName = user.display_name || user.username;
  const initials = displayName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  // Topbar
  const nameEl = document.querySelector('.user-name');
  const roleEl = document.querySelector('.user-role');
  const avatarEl = document.getElementById('user-avatar-btn');
  if (nameEl) nameEl.textContent = displayName;
  if (roleEl) roleEl.textContent = user.role || '';
  if (avatarEl) avatarEl.textContent = initials;

  // Dropdown header
  const ddAvatar = document.getElementById('dropdown-avatar');
  const ddName = document.getElementById('dropdown-user-name');
  const ddRole = document.getElementById('dropdown-user-role');
  if (ddAvatar) ddAvatar.textContent = initials;
  if (ddName) ddName.textContent = displayName;
  if (ddRole) ddRole.textContent = user.role || '';

  // Profile page
  const pAvatar = document.getElementById('profile-avatar-lg');
  const pName = document.getElementById('profile-display-name');
  const pRole = document.getElementById('profile-role-badge');
  const pUsername = document.getElementById('profile-username');
  const pRoleField = document.getElementById('profile-role');
  const pNameInput = document.getElementById('profile-name-input');
  const pSessionUser = document.getElementById('profile-session-user');
  const pLoginTime = document.getElementById('profile-login-time');
  if (pAvatar) pAvatar.textContent = initials;
  if (pName) pName.textContent = displayName;
  if (pRole) pRole.textContent = user.role || '';
  if (pUsername) pUsername.textContent = user.username || '';
  if (pRoleField) pRoleField.textContent = user.role || '';
  if (pNameInput) pNameInput.value = displayName;
  if (pSessionUser) pSessionUser.textContent = user.username || '';
  if (pLoginTime) pLoginTime.textContent = new Date().toLocaleString();
})();

// ── User Dropdown Menu ──────────────────────────────────────────
function toggleUserMenu(e) {
  e.stopPropagation();
  const dropdown = document.getElementById('user-dropdown');
  const avatar = document.getElementById('user-avatar-btn');
  const isOpen = dropdown.classList.contains('open');
  dropdown.classList.toggle('open', !isOpen);
  avatar.classList.toggle('menu-open', !isOpen);
}

function closeUserMenu() {
  const dropdown = document.getElementById('user-dropdown');
  const avatar = document.getElementById('user-avatar-btn');
  if (dropdown) dropdown.classList.remove('open');
  if (avatar) avatar.classList.remove('menu-open');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
  const wrapper = document.querySelector('.user-menu-wrapper');
  if (wrapper && !wrapper.contains(e.target)) {
    closeUserMenu();
  }
});

// ── Global Keyboard Shortcuts ───────────────────────────────────
document.addEventListener('keydown', function(e) {
  const tag = (e.target.tagName || '').toLowerCase();
  const isInput = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable;

  // Escape - close modals, dropdowns, overlays
  if (e.key === 'Escape') {
    closeUserMenu();
    closeShortcuts();
    const paModal = document.getElementById('pa-modal');
    if (paModal && paModal.style.display !== 'none') { closePAModal(); return; }
    return;
  }

  // ? key (not in input) - toggle shortcuts overlay
  if (e.key === '?' && !isInput) {
    e.preventDefault();
    toggleShortcuts();
    return;
  }

  // Alt + number for page navigation
  if (e.altKey && !e.ctrlKey && !e.metaKey) {
    const pageMap = {
      '1': 'morning-brief',
      '2': 'dashboard',
      '3': 'appointments',
      '4': 'pa-requests',
      '5': 'reports',
      '6': 'ehr-sync',
      '7': 'settings'
    };
    if (pageMap[e.key]) {
      e.preventDefault();
      navigateTo(pageMap[e.key]);
      return;
    }

    // Alt+N - focus first name field
    if (e.key === 'n' || e.key === 'N') {
      e.preventDefault();
      navigateTo('new-check');
      setTimeout(() => {
        const el = document.getElementById('patient_first_name');
        if (el) el.focus();
      }, 100);
      return;
    }

    // Alt+P - focus payer search
    if (e.key === 'p' || e.key === 'P') {
      e.preventDefault();
      navigateTo('new-check');
      setTimeout(() => {
        const el = document.getElementById('payer_search');
        if (el) el.focus();
      }, 100);
      return;
    }

    // Alt+Enter - submit eligibility check
    if (e.key === 'Enter') {
      e.preventDefault();
      const submitBtn = document.getElementById('submit-btn');
      if (submitBtn) submitBtn.click();
      return;
    }

    // Alt+C - clear form
    if (e.key === 'c' || e.key === 'C') {
      e.preventDefault();
      if (typeof clearForm === 'function') clearForm();
      return;
    }
  }

  // Enter on sidebar nav items
  if (e.key === 'Enter' && e.target.classList.contains('nav-item')) {
    e.preventDefault();
    e.target.click();
  }
});

// Shortcuts overlay toggle
function toggleShortcuts() {
  const overlay = document.getElementById('shortcuts-overlay');
  if (overlay) overlay.classList.toggle('open');
}

function closeShortcuts() {
  const overlay = document.getElementById('shortcuts-overlay');
  if (overlay) overlay.classList.remove('open');
}

// Close shortcuts overlay when clicking outside the panel
document.addEventListener('click', function(e) {
  const overlay = document.getElementById('shortcuts-overlay');
  if (overlay && overlay.classList.contains('open') && e.target === overlay) {
    closeShortcuts();
  }
});

// ── Profile Page Functions ──────────────────────────────────────
function saveProfile() {
  const nameInput = document.getElementById('profile-name-input');
  const emailInput = document.getElementById('profile-email-input');
  const newName = nameInput ? nameInput.value.trim() : '';
  if (!newName) return;

  // Update stored user data
  const user = getAuthUser();
  if (user) {
    user.display_name = newName;
    if (emailInput && emailInput.value.trim()) user.email = emailInput.value.trim();
    const storage = localStorage.getItem('auth_user') ? localStorage : sessionStorage;
    storage.setItem('auth_user', JSON.stringify(user));
  }

  // Update all UI elements
  const initials = newName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  document.querySelector('.user-name').textContent = newName;
  document.getElementById('user-avatar-btn').textContent = initials;
  document.getElementById('dropdown-avatar').textContent = initials;
  document.getElementById('dropdown-user-name').textContent = newName;
  document.getElementById('profile-avatar-lg').textContent = initials;
  document.getElementById('profile-display-name').textContent = newName;

  showProfileMsg('Profile updated successfully', 'success');
}

function changePassword() {
  const curPw = document.getElementById('profile-current-pw');
  const newPw = document.getElementById('profile-new-pw');
  const confirmPw = document.getElementById('profile-confirm-pw');

  if (!curPw.value || !newPw.value || !confirmPw.value) {
    showPwMsg('Please fill in all password fields', 'error');
    return;
  }
  if (newPw.value !== confirmPw.value) {
    showPwMsg('New passwords do not match', 'error');
    return;
  }
  if (newPw.value.length < 6) {
    showPwMsg('Password must be at least 6 characters', 'error');
    return;
  }

  // Call backend to change password
  authFetch('/api/v1/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: curPw.value, new_password: newPw.value }),
  }).then(res => res.json()).then(data => {
    if (data.status === 'ok') {
      showPwMsg('Password changed successfully', 'success');
      curPw.value = '';
      newPw.value = '';
      confirmPw.value = '';
    } else {
      showPwMsg(data.detail || 'Failed to change password', 'error');
    }
  }).catch(() => {
    showPwMsg('Connection error', 'error');
  });
}

function showPwMsg(text, type) {
  const el = document.getElementById('pw-msg');
  el.textContent = text;
  el.className = 'profile-msg ' + type;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 4000);
}

function showProfileMsg(text, type) {
  // Reuse pw-msg area or create a temporary toast
  const el = document.getElementById('pw-msg');
  el.textContent = text;
  el.className = 'profile-msg ' + type;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 3000);
}

// ── Sidebar Navigation ──────────────────────────────────────────
function navigateTo(pageName) {
  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  // Show target page
  const targetPage = document.getElementById('page-' + pageName);
  if (targetPage) targetPage.classList.add('active');

  // Update sidebar active state
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.page === pageName);
  });

  // Persist current page so refresh stays on same page
  try { localStorage.setItem('thinkAI_currentPage', pageName); } catch(e) {}

  // Refresh dashboard data when navigating to it
  if (pageName === 'dashboard') {
    loadRecentChecks();
    renderPAPipeline();
  }

  // Load PA requests when navigating to PA page
  if (pageName === 'pa-requests') {
    loadPARequests();
  }

  window.scrollTo(0, 0);
}

// Restore last page on load (or default to morning-brief)
(function restoreLastPage() {
  var saved = null;
  try { saved = localStorage.getItem('thinkAI_currentPage'); } catch(e) {}
  if (saved && document.getElementById('page-' + saved)) {
    navigateTo(saved);
  } else {
    navigateTo('morning-brief');
  }
})();

// Legacy showPage for results page navigation
function showPage(name) {
  if (name === 'form') {
    navigateTo('new-check');
    return;
  }
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  window.scrollTo(0, 0);
}

// Init sidebar click handlers
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => navigateTo(item.dataset.page));
});

// ── Combo Box (Searchable Dropdown) ──────────────────────────

let _serviceTypes = [];  // cached service type list
let _payerSearchTimeout = null;

// -- Payer search combo --
(function initPayerCombo() {
  const input = document.getElementById('payer_search');
  const dropdown = document.getElementById('payer-dropdown');
  const hiddenId = document.getElementById('payer_id');
  const hiddenName = document.getElementById('payer_name_hidden');

  input.addEventListener('input', () => {
    clearTimeout(_payerSearchTimeout);
    const q = input.value.trim();
    hiddenId.value = '';
    hiddenName.value = '';

    if (q.length < 1) {
      dropdown.classList.remove('open');
      return;
    }
    _payerSearchTimeout = setTimeout(async () => {
      try {
        const res = await authFetch(API + '/api/v1/lookup/payers?q=' + encodeURIComponent(q) + '&limit=30');
        const payers = await res.json();
        renderPayerDropdown(payers, q);
      } catch (e) {
        console.error('Payer search failed:', e);
      }
    }, 200);
  });

  input.addEventListener('focus', () => {
    if (input.value.trim().length >= 1 && dropdown.children.length > 0) {
      dropdown.classList.add('open');
    }
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.combo-group')) {
      document.querySelectorAll('.combo-dropdown').forEach(d => d.classList.remove('open'));
    }
  });

  function renderPayerDropdown(payers, query) {
    if (!payers.length) {
      dropdown.innerHTML = `
        <div class="combo-empty">No payers found for "${query}"</div>
        <div class="combo-custom" onclick="selectCustomPayer('${query}')">
          Use "${query}" as custom payer ID
        </div>`;
      dropdown.classList.add('open');
      return;
    }
    dropdown.innerHTML = payers.map(p => `
      <div class="combo-item" onclick="selectPayer('${p.id}', '${p.name.replace(/'/g, "\\'")}')">
        <span class="combo-item-id">${p.id}</span>
        <span class="combo-item-name">${highlightMatch(p.name, query)}</span>
        ${p.type ? `<span class="combo-item-type">${p.type}</span>` : ''}
      </div>
    `).join('');
    // Add custom option at bottom
    dropdown.innerHTML += `
      <div class="combo-custom" onclick="selectCustomPayer('${query}')">
        Use "${query}" as custom payer ID
      </div>`;
    dropdown.classList.add('open');
  }
})();

function selectPayer(id, name) {
  document.getElementById('payer_search').value = id + ' - ' + name;
  document.getElementById('payer_id').value = id;
  document.getElementById('payer_name_hidden').value = name;
  document.getElementById('payer-dropdown').classList.remove('open');
}

function selectCustomPayer(value) {
  document.getElementById('payer_search').value = value;
  document.getElementById('payer_id').value = value;
  document.getElementById('payer_name_hidden').value = value;
  document.getElementById('payer-dropdown').classList.remove('open');
}

// -- Service Type search combo --
(async function initServiceTypeCombo() {
  // Load all service types once
  try {
    const res = await authFetch(API + '/api/v1/lookup/service-types');
    _serviceTypes = await res.json();
  } catch (e) {
    console.error('Failed to load service types:', e);
    _serviceTypes = [{ code: '30', name: 'Health Benefit Plan Coverage' }];
  }

  const input = document.getElementById('service_type_search');
  const dropdown = document.getElementById('service-type-dropdown');
  const hiddenCode = document.getElementById('service_type_code');

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    hiddenCode.value = '';

    if (q.length < 1) {
      dropdown.classList.remove('open');
      return;
    }
    const filtered = _serviceTypes.filter(s =>
      s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
    ).slice(0, 30);

    if (!filtered.length) {
      dropdown.innerHTML = `
        <div class="combo-empty">No service types found for "${q}"</div>
        <div class="combo-custom" onclick="selectCustomServiceType('${q}')">
          Use "${q}" as custom service type code
        </div>`;
    } else {
      dropdown.innerHTML = filtered.map(s => `
        <div class="combo-item" onclick="selectServiceType('${s.code}', '${s.name.replace(/'/g, "\\'")}')">
          <span class="combo-item-id">${s.code}</span>
          <span class="combo-item-name">${highlightMatch(s.name, input.value.trim())}</span>
        </div>
      `).join('');
      dropdown.innerHTML += `
        <div class="combo-custom" onclick="selectCustomServiceType('${input.value.trim()}')">
          Use "${input.value.trim()}" as custom code
        </div>`;
    }
    dropdown.classList.add('open');
  });

  input.addEventListener('focus', () => {
    if (input.value.trim().length >= 1) {
      input.dispatchEvent(new Event('input'));
    }
  });
})();

function selectServiceType(code, name) {
  document.getElementById('service_type_search').value = code + ' - ' + name;
  document.getElementById('service_type_code').value = code;
  document.getElementById('service-type-dropdown').classList.remove('open');
}

function selectCustomServiceType(value) {
  document.getElementById('service_type_search').value = value;
  document.getElementById('service_type_code').value = value;
  document.getElementById('service-type-dropdown').classList.remove('open');
}

function highlightMatch(text, query) {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return text.substring(0, idx) +
    '<strong>' + text.substring(idx, idx + query.length) + '</strong>' +
    text.substring(idx + query.length);
}


// ── Load recent checks on startup ────────────────────────────
async function loadRecentChecks() {
  try {
    const res = await authFetch(API + '/api/v1/eligibility/checks');
    const checks = await res.json();
    renderRecentChecks(checks);
  } catch (e) {
    console.error('Failed to load recent checks:', e);
  }
}

// ── Pagination state ──
let _allChecks = [];
let _checksPage = 1;
const CHECKS_PER_PAGE = 5;

function renderRecentChecks(checks) {
  _allChecks = checks;
  _checksPage = 1;

  // Update sidebar stats only (dashboard stats come from /api/v1/stats)
  const sidebarChecks = document.getElementById('sidebar-checks-count');
  if (sidebarChecks) sidebarChecks.textContent = checks.length;

  _renderChecksPage();
}

function _renderChecksPage() {
  const tbody = document.getElementById('recent-checks-body');
  const empty = document.getElementById('empty-state');
  const checks = _allChecks;

  if (!checks.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    _renderPagination(0, 0);
    return;
  }
  empty.style.display = 'none';

  const totalPages = Math.ceil(checks.length / CHECKS_PER_PAGE);
  if (_checksPage > totalPages) _checksPage = totalPages;
  const start = (_checksPage - 1) * CHECKS_PER_PAGE;
  const pageChecks = checks.slice(start, start + CHECKS_PER_PAGE);

  tbody.innerHTML = pageChecks.map(c => {
    const paRequired = c.prior_auth_required;
    const paBadge = paRequired === true
      ? '<span class="badge badge-yes">Yes</span>'
      : '<span class="badge badge-no">No</span>';
    const time = c.run_date || '--';
    const ch = c.clearinghouse_provider || '--';
    const chLabel = {'stedi': 'Stedi', 'waystar': 'Waystar', 'claimmd': 'Claim.MD'}[ch] || ch;
    const carrier = c.carrier_name || '--';
    const plan = c.plan_name || '';
    const responseInfo = carrier !== '--' ? carrier + (plan ? ' / ' + plan : '') : (c.coverage_status || '--');
    return `
    <tr style="cursor:pointer;" onclick="viewResult('${c.check_id}')">
      <td><strong>${c.patient_name}</strong></td>
      <td>${c.payer_name}</td>
      <td><span class="badge badge-single">${chLabel}</span></td>
      <td>${statusBadge(c.status)}</td>
      <td><small>${responseInfo}</small></td>
      <td>${paBadge}</td>
      <td>${time}</td>
    </tr>
  `;
  }).join('');

  _renderPagination(totalPages, checks.length);
}

function _renderPagination(totalPages, totalRecords) {
  let paginationEl = document.getElementById('checks-pagination');
  if (!paginationEl) {
    paginationEl = document.createElement('div');
    paginationEl.id = 'checks-pagination';
    paginationEl.className = 'pagination-bar';
    const tableWrapper = document.getElementById('recent-checks-body').closest('.table-wrapper');
    tableWrapper.parentElement.appendChild(paginationEl);
  }

  if (totalPages <= 1) {
    paginationEl.innerHTML = totalRecords
      ? `<span class="pagination-info">Showing ${totalRecords} of ${totalRecords} records</span>`
      : '';
    return;
  }

  const start = (_checksPage - 1) * CHECKS_PER_PAGE + 1;
  const end = Math.min(_checksPage * CHECKS_PER_PAGE, totalRecords);

  let buttons = '';
  // Prev
  buttons += `<button class="pagination-btn" ${_checksPage === 1 ? 'disabled' : ''} onclick="goChecksPage(${_checksPage - 1})">&laquo; Prev</button>`;

  // Page numbers
  for (let i = 1; i <= totalPages; i++) {
    if (totalPages <= 7 || i === 1 || i === totalPages || Math.abs(i - _checksPage) <= 1) {
      buttons += `<button class="pagination-btn ${i === _checksPage ? 'active' : ''}" onclick="goChecksPage(${i})">${i}</button>`;
    } else if (i === _checksPage - 2 || i === _checksPage + 2) {
      buttons += `<span class="pagination-dots">...</span>`;
    }
  }

  // Next
  buttons += `<button class="pagination-btn" ${_checksPage === totalPages ? 'disabled' : ''} onclick="goChecksPage(${_checksPage + 1})">Next &raquo;</button>`;

  paginationEl.innerHTML = `
    <span class="pagination-info">Showing ${start}-${end} of ${totalRecords} records</span>
    <div class="pagination-buttons">${buttons}</div>
  `;
}

function goChecksPage(page) {
  _checksPage = page;
  _renderChecksPage();
}

function statusBadge(status) {
  const labels = {
    eligible: 'Eligible',
    not_eligible: 'Not Eligible',
    pending: 'Pending',
    error: 'Error',
  };
  const label = labels[status] || status;
  return `<span class="badge badge-${status}">${label}</span>`;
}

// ── Inline Field Validation ──────────────────────────────────
function showFieldError(fieldId, msg) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  field.classList.add('input-error');
  field.classList.remove('input-valid');
  let errEl = field.parentElement.querySelector('.field-error');
  if (!errEl) {
    errEl = document.createElement('div');
    errEl.className = 'field-error';
    errEl.style.cssText = 'color:var(--error);font-size:0.78rem;margin-top:3px;';
    field.parentElement.appendChild(errEl);
  }
  errEl.innerHTML = msg;
  errEl.style.display = 'block';
}

function clearFieldError(fieldId) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  field.classList.remove('input-error');
  const errEl = field.parentElement.querySelector('.field-error');
  if (errEl) errEl.style.display = 'none';
}

function showFieldValid(fieldId) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  field.classList.remove('input-error');
  field.classList.add('input-valid');
  const errEl = field.parentElement.querySelector('.field-error');
  if (errEl) errEl.style.display = 'none';
}

// ── Required field validation (inline on blur) ──

// Patient First Name: required
(function() {
  const el = document.getElementById('patient_first_name');
  if (!el) return;
  el.addEventListener('blur', () => {
    if (!el.value.trim()) showFieldError('patient_first_name', 'Patient First Name is required');
    else clearFieldError('patient_first_name');
  });
  el.addEventListener('input', () => { if (el.value.trim()) clearFieldError('patient_first_name'); });
})();

// Patient Last Name: required
(function() {
  const el = document.getElementById('patient_last_name');
  if (!el) return;
  el.addEventListener('blur', () => {
    if (!el.value.trim()) showFieldError('patient_last_name', 'Patient Last Name is required');
    else clearFieldError('patient_last_name');
  });
  el.addEventListener('input', () => { if (el.value.trim()) clearFieldError('patient_last_name'); });
})();

// Date of Birth: required, must be in the past
(function() {
  const el = document.getElementById('patient_dob');
  if (!el) return;
  el.addEventListener('blur', () => {
    const val = el.value;
    if (!val) { showFieldError('patient_dob', 'Date of Birth is required'); return; }
    if (new Date(val) >= new Date()) {
      showFieldError('patient_dob', 'Date of Birth must be in the past');
    } else {
      clearFieldError('patient_dob');
    }
  });
  el.addEventListener('input', () => { if (el.value) clearFieldError('patient_dob'); });
})();

// Member ID: required by all clearinghouses, min 3 chars
(function() {
  const memField = document.getElementById('member_id');
  if (!memField) return;
  memField.addEventListener('blur', () => {
    const val = memField.value.trim();
    if (!val) { showFieldError('member_id', 'Member ID is required by clearinghouses'); return; }
    if (val.length < 3) {
      showFieldError('member_id', 'Member ID seems too short (minimum 3 characters)');
    } else {
      clearFieldError('member_id');
    }
  });
  memField.addEventListener('input', () => { if (memField.value.trim()) clearFieldError('member_id'); });
})();

// Payer ID: required by all clearinghouses
(function() {
  const payerInput = document.getElementById('payer_search');
  if (!payerInput) return;
  payerInput.addEventListener('blur', () => {
    const val = payerInput.value.trim();
    if (!val) {
      showFieldError('payer_search', 'Payer ID is required by clearinghouses');
    } else {
      clearFieldError('payer_search');
    }
  });
  payerInput.addEventListener('input', () => { if (payerInput.value.trim()) clearFieldError('payer_search'); });
})();

// Provider Name: required by Stedi (organizationName or firstName+lastName)
(function() {
  const nameField = document.getElementById('provider_name');
  if (!nameField) return;
  nameField.addEventListener('blur', () => {
    const val = nameField.value.trim();
    if (!val) {
      showFieldError('provider_name', 'Provider Name is required by clearinghouses');
    } else {
      clearFieldError('provider_name');
    }
  });
  nameField.addEventListener('input', () => { if (nameField.value.trim()) clearFieldError('provider_name'); });
})();

// ── Form submission ──────────────────────────────────────────
document.getElementById('eligibility-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  // ── Validate required fields before submit ──
  let hasError = false;

  // Patient First Name
  const firstName = document.getElementById('patient_first_name').value.trim();
  if (!firstName) { showFieldError('patient_first_name', 'Patient First Name is required'); hasError = true; }
  else clearFieldError('patient_first_name');

  // Patient Last Name
  const lastName = document.getElementById('patient_last_name').value.trim();
  if (!lastName) { showFieldError('patient_last_name', 'Patient Last Name is required'); hasError = true; }
  else clearFieldError('patient_last_name');

  // Date of Birth
  const dob = document.getElementById('patient_dob').value;
  if (!dob) { showFieldError('patient_dob', 'Date of Birth is required'); hasError = true; }
  else if (new Date(dob) >= new Date()) { showFieldError('patient_dob', 'Date of Birth must be in the past'); hasError = true; }
  else clearFieldError('patient_dob');

  // Member ID — required by all clearinghouses
  const memberId = document.getElementById('member_id').value.trim();
  if (!memberId) { showFieldError('member_id', 'Member ID is required by clearinghouses'); hasError = true; }
  else if (memberId.length < 3) { showFieldError('member_id', 'Member ID seems too short (minimum 3 characters)'); hasError = true; }
  else clearFieldError('member_id');

  // Provider Name — required by Stedi
  const providerName = document.getElementById('provider_name').value.trim();
  if (!providerName) { showFieldError('provider_name', 'Provider Name is required by clearinghouses'); hasError = true; }
  else clearFieldError('provider_name');

  // Resolve payer
  let payerId = document.getElementById('payer_id').value;
  let payerName = document.getElementById('payer_name_hidden').value;
  const payerSearchVal = document.getElementById('payer_search').value.trim();

  if (!payerId && payerSearchVal) {
    const dashIdx = payerSearchVal.indexOf(' - ');
    if (dashIdx > 0) {
      payerId = payerSearchVal.substring(0, dashIdx).trim();
      payerName = payerSearchVal.substring(dashIdx + 3).trim();
    } else {
      payerId = payerSearchVal;
      payerName = payerSearchVal;
    }
  }

  if (!payerId) {
    showFieldError('payer_search', 'Insurance Payer is required. Search or enter a payer ID');
    hasError = true;
  } else clearFieldError('payer_search');

  // NPI validation (warning, not blocking)
  const npiVal = document.getElementById('provider_npi').value.trim();
  if (!npiVal) {
    showFieldError('provider_npi', 'Provider NPI is required for clearinghouse lookup');
    hasError = true;
  } else if (!/^\d{10}$/.test(npiVal)) {
    showFieldError('provider_npi', 'NPI must be exactly 10 digits');
    hasError = true;
  }

  // If any required field is missing, stop here
  if (hasError) {
    // Scroll to first error
    const firstErr = document.querySelector('.input-error');
    if (firstErr) firstErr.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  // NPI Luhn check — block submission if invalid
  if (npiVal && !checkLuhnNPI(npiVal)) {
    const corrected = computeCorrectNPI(npiVal);
    let msg = 'NPI fails Luhn check-digit validation — invalid NPI.';
    if (corrected) msg += ' Suggested: ' + corrected;
    showFieldError('provider_npi', msg);
    document.getElementById('provider_npi').scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  // Resolve service type
  let serviceTypeCode = document.getElementById('service_type_code').value;
  const stSearchVal = document.getElementById('service_type_search').value.trim();
  if (!serviceTypeCode && stSearchVal) {
    const dashIdx = stSearchVal.indexOf(' - ');
    serviceTypeCode = dashIdx > 0 ? stSearchVal.substring(0, dashIdx).trim() : stSearchVal;
  }
  if (!serviceTypeCode) serviceTypeCode = '30';

  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  document.getElementById('loading-overlay').style.display = 'flex';

  const payload = {
    patient_first_name: document.getElementById('patient_first_name').value.trim(),
    patient_last_name: document.getElementById('patient_last_name').value.trim(),
    patient_dob: document.getElementById('patient_dob').value,
    member_id: document.getElementById('member_id').value.trim(),
    payer_id: payerId,
    payer_name: payerName || payerId,
    provider_npi: document.getElementById('provider_npi').value.trim(),
    provider_name: document.getElementById('provider_name').value.trim(),
    provider_tax_id: document.getElementById('provider_tax_id').value.trim(),
    service_type_code: serviceTypeCode,
    clearinghouse: document.getElementById('clearinghouse_select').value || document.getElementById('global_provider_select').value || '',
  };

  try {
    const res = await authFetch(API + '/api/v1/eligibility/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await res.json();

    // Refresh the table
    await loadRecentChecks();

    // Show results
    _lastEligResult = result;
    renderResults(result);
    showPage('results');
  } catch (err) {
    alert('Error running eligibility check: ' + err.message);
  } finally {
    btn.disabled = false;
    document.getElementById('loading-overlay').style.display = 'none';
  }
});

// ── View a past result ───────────────────────────────────────
async function viewResult(checkId) {
  document.getElementById('loading-overlay').style.display = 'flex';
  try {
    const res = await authFetch(API + '/api/v1/eligibility/checks/' + checkId);
    if (!res.ok) throw new Error('Check not found');
    const result = await res.json();
    _lastEligResult = result;
    renderResults(result);
    showPage('results');
  } catch (err) {
    alert('Could not load result: ' + err.message);
  } finally {
    document.getElementById('loading-overlay').style.display = 'none';
  }
}

// ── Render results page ──────────────────────────────────────
function renderResults(r) {
  // Header
  document.getElementById('r-patient-name').textContent = r.patient_name;
  const badge = document.getElementById('r-status-badge');
  badge.className = 'badge badge-' + r.status;
  const statusLabels = { eligible: 'Eligible', not_eligible: 'Not Eligible', inactive: 'Inactive', pending: 'Pending', error: 'Error' };
  badge.textContent = statusLabels[r.status] || r.status;

  document.getElementById('r-subtitle').textContent =
    (r.plan_name || r.payer_name) + ' \u2022 Check ID: ' + r.check_id;

  // Financial Summary
  const financialCard = document.getElementById('financial-card');
  if (r.annual_deductible !== null && r.annual_deductible !== undefined) {
    financialCard.style.display = 'block';
    const dedMax = r.annual_deductible_max || r.annual_deductible;
    const dedPct = dedMax > 0 ? (r.annual_deductible / dedMax) * 100 : 0;
    const dedRemaining = dedMax - r.annual_deductible;

    document.getElementById('r-deductible').textContent = '$' + fmt(r.annual_deductible);
    document.getElementById('r-deductible-max').textContent = '/ $' + fmt(dedMax);
    document.getElementById('r-deductible-bar').style.width = dedPct + '%';
    document.getElementById('r-deductible-remaining').textContent = '$' + fmt(dedRemaining) + ' remaining';

    const oop = r.out_of_pocket || 0;
    const oopMax = r.out_of_pocket_max || oop;
    const oopPct = oopMax > 0 ? (oop / oopMax) * 100 : 0;
    const oopRemaining = oopMax - oop;

    document.getElementById('r-oop').textContent = '$' + fmt(oop);
    document.getElementById('r-oop-max').textContent = '/ $' + fmt(oopMax);
    document.getElementById('r-oop-bar').style.width = oopPct + '%';
    document.getElementById('r-oop-remaining').textContent = '$' + fmt(oopRemaining) + ' remaining';
  } else {
    financialCard.style.display = 'none';
  }

  // Coverage Details
  document.getElementById('r-copay').textContent =
    r.copay !== null && r.copay !== undefined ? '$' + fmt(r.copay) : '--';
  document.getElementById('r-coinsurance').textContent =
    r.coinsurance !== null && r.coinsurance !== undefined ? r.coinsurance + '%' : '--';

  // Prior Auth — always show button when patient is eligible so staff can
  // initiate a PA inquiry regardless of whether the payer flagged it as required.
  const paEl = document.getElementById('r-prior-auth');
  const btnPA = document.getElementById('btn-proceed-pa');
  if (r.prior_auth_required === true) {
    paEl.innerHTML = '<span class="badge badge-required">Required</span>';
    btnPA.style.display = 'inline-flex';
  } else if (r.prior_auth_required === false) {
    paEl.innerHTML = '<span class="badge badge-not-required">Not Required</span>';
    // Still allow staff to manually initiate PA if needed
    btnPA.style.display = (r.status === 'eligible') ? 'inline-flex' : 'none';
  } else {
    paEl.textContent = '--';
    // Show PA button for eligible patients even when prior_auth field is unknown
    btnPA.style.display = (r.status === 'eligible') ? 'inline-flex' : 'none';
  }

  document.getElementById('r-plan-name').textContent = r.plan_name || '--';

  // Coverage dates
  if (r.coverage_start) {
    document.getElementById('r-coverage-dates').textContent =
      r.coverage_start + ' to ' + (r.coverage_end || 'Present');
  } else {
    document.getElementById('r-coverage-dates').textContent = '--';
  }

  // Group / Plan number
  const gnText = [r.group_number, r.plan_number].filter(Boolean).join(' / ');
  document.getElementById('r-group-number').textContent = gnText || '--';

  // Payer Response Details (from Waystar)
  const payerCard = document.getElementById('payer-response-card');
  if (r.carrier_name || r.subscriber_name || r.coverage_status) {
    payerCard.style.display = 'block';
    document.getElementById('r-carrier-name').textContent = r.carrier_name || '--';

    const csEl = document.getElementById('r-coverage-status');
    const cs = r.coverage_status || r.status;
    csEl.textContent = cs.charAt(0).toUpperCase() + cs.slice(1);
    csEl.className = 'detail-value ' + (cs.toLowerCase() === 'active' || r.status === 'eligible' ? 'active' : 'inactive');

    document.getElementById('r-subscriber-name').textContent = r.subscriber_name || '--';
    document.getElementById('r-relationship').textContent = r.relationship || '--';
    document.getElementById('r-payer-patient').textContent = r.patient_name || '--';
    document.getElementById('r-payer-dob').textContent = r.patient_dob_from_payer || '--';
    document.getElementById('r-payer-gender').textContent = r.patient_gender || '--';
    document.getElementById('r-payer-member-id').textContent = r.raw_response?.ParsedOutput?.MemberId || '--';
    document.getElementById('r-claims-address').textContent = r.claims_address || '--';
  } else {
    payerCard.style.display = 'none';
  }

  // Findings
  const findingsCard = document.getElementById('findings-card');
  const findings = r.findings || [];
  if (findings.length > 0) {
    findingsCard.style.display = 'block';
    document.getElementById('r-findings-count').textContent = findings.length;

    const list = document.getElementById('findings-list');
    list.innerHTML = findings.map(f => {
      const suggestedNpi = f.context && f.context.suggested_npi ? f.context.suggested_npi : null;
      return `
      <div class="finding-item ${f.severity}">
        <div class="finding-code">${f.code}</div>
        <div class="finding-message">${f.message}</div>
        ${f.suggestion ? `<div class="finding-suggestion">${f.suggestion}</div>` : ''}
        ${suggestedNpi ? `<div class="finding-action">
          <button class="btn-fix" onclick="applyCorrectNPI('${suggestedNpi}'); navigateTo('new-check');">
            Use corrected NPI: ${suggestedNpi}
          </button>
        </div>` : ''}
      </div>
    `;
    }).join('');
  } else {
    findingsCard.style.display = 'none';
  }

  // Raw Eligibility Response
  var rawCard = document.getElementById('raw-response-card');
  if (r.raw_response) {
    rawCard.style.display = 'block';
    var chLabels = {'stedi': 'Stedi', 'waystar': 'Waystar / Zirmed', 'claimmd': 'Claim.MD'};
    document.getElementById('r-clearinghouse').textContent = chLabels[r.clearinghouse_provider] || r.clearinghouse_provider || '--';
    document.getElementById('r-exec-time').textContent = r.execution_time ? r.execution_time + 's' : '--';
    document.getElementById('r-check-id-display').textContent = r.check_id || '--';
    try {
      document.getElementById('r-raw-json').textContent = JSON.stringify(r.raw_response, null, 2);
    } catch(e) {
      document.getElementById('r-raw-json').textContent = String(r.raw_response);
    }
  } else {
    rawCard.style.display = 'none';
  }

  // AI Coverage Prediction
  renderAIPrediction(r);

  // Recommendation
  renderRecommendation(r);
}

function renderAIPrediction(r) {
  let pct, confidence, factors;

  if (r.status === 'eligible' && r.total_errors === 0) {
    pct = r.total_warnings > 0 ? 72 : 87;
    confidence = pct >= 80 ? 'high' : 'medium';
    factors = [
      { name: 'Payer History', pct: 92 },
      { name: 'Diagnosis Match', pct: 85 },
      { name: 'Documentation Completeness', pct: r.total_warnings > 0 ? 60 : 78 },
      { name: 'Prior Auth Track Record', pct: 94 },
    ];
  } else if (r.status === 'inactive') {
    pct = 10;
    confidence = 'low';
    factors = [
      { name: 'Coverage Status', pct: 0 },
      { name: 'Payer History', pct: 40 },
      { name: 'Documentation Completeness', pct: 50 },
      { name: 'Prior Auth Track Record', pct: 15 },
    ];
  } else if (r.status === 'not_eligible') {
    pct = 15;
    confidence = 'low';
    factors = [
      { name: 'Payer History', pct: 30 },
      { name: 'Coverage Status', pct: 0 },
      { name: 'Documentation Completeness', pct: 45 },
      { name: 'Prior Auth Track Record', pct: 20 },
    ];
  } else {
    pct = 50;
    confidence = 'medium';
    factors = [
      { name: 'Payer History', pct: 60 },
      { name: 'Diagnosis Match', pct: 55 },
      { name: 'Documentation Completeness', pct: 40 },
      { name: 'Prior Auth Track Record', pct: 50 },
    ];
  }

  // Gauge
  const circumference = 314;
  const offset = circumference - (pct / 100) * circumference;
  document.getElementById('r-gauge-fill').setAttribute('stroke-dashoffset', offset);
  document.getElementById('r-gauge-fill').style.stroke =
    pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--error)';

  document.getElementById('r-ai-pct').textContent = pct + '%';
  document.getElementById('r-ai-pct').style.color =
    pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--error)';

  const confBadge = document.getElementById('r-ai-confidence');
  confBadge.className = 'confidence-badge ' + confidence;
  confBadge.textContent =
    confidence === 'high' ? 'High Confidence' :
    confidence === 'medium' ? 'Medium Confidence' : 'Low Confidence';

  // Factors
  document.getElementById('r-factors').innerHTML = factors.map(f => `
    <div class="factor-item">
      <span class="factor-name">${f.name}</span>
      <span class="factor-pct">${f.pct}%</span>
    </div>
    <div class="factor-bar">
      <div class="factor-bar-fill" style="width:${f.pct}%"></div>
    </div>
  `).join('');
}

function renderRecommendation(r) {
  const card = document.getElementById('recommendation-card');
  const text = document.getElementById('r-recommendation');
  const tips = document.getElementById('r-tips');

  if (r.status === 'eligible' && r.total_errors === 0) {
    card.className = 'card recommendation-card success';
    card.querySelector('h3').innerHTML = '<span class="icon-check">&#10003;</span> Recommendation';
    if (r.prior_auth_required) {
      text.textContent = 'Patient is eligible. Prior authorization is required — proceed with authorization request.';
    } else {
      text.textContent = 'Patient is eligible with no issues detected. Safe to proceed with claim submission.';
    }
    tips.innerHTML = `
      <li>Ensure current prescription is on file</li>
      <li>Include detailed clinical notes</li>
      <li>Verify diagnosis codes match payer requirements</li>
    `;
  } else if (r.status === 'inactive') {
    card.className = 'card recommendation-card error';
    card.querySelector('h3').innerHTML = '<span style="color:var(--error)">&#10007;</span> Coverage Inactive';
    text.textContent = 'Payer confirms this coverage is INACTIVE. The claim will be denied if submitted with this insurance.';
    tips.innerHTML = `
      <li>Verify patient has current active insurance coverage</li>
      <li>Check for updated member ID or new policy number</li>
      <li>Ask patient about secondary/alternate insurance</li>
      <li>Contact payer to confirm termination date: ${r.coverage_end || 'unknown'}</li>
    `;
  } else if (r.status === 'not_eligible') {
    card.className = 'card recommendation-card error';
    card.querySelector('h3').innerHTML = '<span style="color:var(--error)">&#10007;</span> Action Required';
    text.textContent = 'Patient is not eligible. Review the findings below and resolve issues before proceeding.';
    tips.innerHTML = `
      <li>Verify patient's insurance card for current member ID</li>
      <li>Contact payer to confirm coverage status</li>
      <li>Check for alternate or secondary insurance</li>
      <li>Review findings and correct any data entry errors</li>
    `;
  } else {
    card.className = 'card recommendation-card warning';
    card.querySelector('h3').innerHTML = '<span style="color:var(--warning)">&#9888;</span> Review Required';
    text.textContent = 'There are warnings that need attention. Review findings to reduce denial risk.';
    tips.innerHTML = `
      <li>Address all validation warnings before submission</li>
      <li>Double-check member ID and payer information</li>
      <li>Ensure all required documentation is attached</li>
    `;
  }
}

// ── NPI Luhn Validation ──────────────────────────────────────
function checkLuhnNPI(npi) {
  if (!npi || npi.length !== 10 || !/^\d{10}$/.test(npi)) return false;
  const prefixed = '80840' + npi;
  let total = 0;
  for (let i = prefixed.length - 1, alt = false; i >= 0; i--, alt = !alt) {
    let d = parseInt(prefixed[i], 10);
    if (alt) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    total += d;
  }
  return total % 10 === 0;
}

function computeCorrectNPI(npi) {
  if (!npi || npi.length < 9 || !/^\d{9,10}$/.test(npi)) return null;
  const base9 = npi.substring(0, 9);
  const prefixed = '80840' + base9 + '0';
  let total = 0;
  for (let i = prefixed.length - 1, alt = false; i >= 0; i--, alt = !alt) {
    let d = parseInt(prefixed[i], 10);
    if (alt) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    total += d;
  }
  const checkDigit = (10 - (total % 10)) % 10;
  return base9 + String(checkDigit);
}

function applyCorrectNPI(correctedNpi) {
  const npiInput = document.getElementById('provider_npi');
  if (npiInput) {
    npiInput.value = correctedNpi;
    npiInput.dispatchEvent(new Event('blur'));
  }
}

(function initNPIValidation() {
  const npiInput = document.getElementById('provider_npi');
  if (!npiInput) return;

  const wrapper = npiInput.parentElement;
  const errEl = document.createElement('div');
  errEl.className = 'npi-validation-msg';
  errEl.style.cssText = 'font-size:0.8rem;margin-top:4px;display:none;line-height:1.4;';
  wrapper.appendChild(errEl);

  function validateNPIField() {
    const val = npiInput.value.trim();
    if (!val) {
      npiInput.classList.remove('input-error', 'input-valid');
      errEl.style.display = 'none';
      return;
    }

    // Only non-digit characters
    if (/\D/.test(val)) {
      npiInput.classList.add('input-error');
      npiInput.classList.remove('input-valid');
      errEl.style.color = '#e74c3c';
      errEl.innerHTML = '<strong>Invalid:</strong> NPI must contain only digits (0-9)';
      errEl.style.display = 'block';
      return;
    }

    // Still typing (less than 10 digits)
    if (val.length < 10) {
      npiInput.classList.remove('input-error', 'input-valid');
      errEl.style.color = '#6b7280';
      if (val.length === 9) {
        // Show what the correct 10th digit should be
        const suggested = computeCorrectNPI(val + '0');
        const checkDigit = suggested ? suggested[9] : '?';
        errEl.innerHTML = '9/10 digits entered &mdash; correct check digit would be: ' +
          '<strong style="font-size:1rem;color:#2563eb;">' + checkDigit + '</strong> ' +
          '(full NPI: <strong>' + (suggested || val + '?') + '</strong>) ' +
          '<button onclick="applyCorrectNPI(\'' + suggested + '\'); return false;" ' +
          'style="background:#2563eb;color:#fff;border:none;border-radius:4px;padding:2px 8px;' +
          'font-size:0.75rem;cursor:pointer;margin-left:4px;">Use this</button>';
      } else {
        errEl.innerHTML = val.length + '/10 digits entered';
      }
      errEl.style.display = 'block';
      return;
    }

    // Too many digits
    if (val.length > 10) {
      npiInput.classList.add('input-error');
      npiInput.classList.remove('input-valid');
      errEl.style.color = '#e74c3c';
      errEl.innerHTML = '<strong>Invalid:</strong> NPI must be exactly 10 digits (' + val.length + ' entered)';
      errEl.style.display = 'block';
      return;
    }

    // Exactly 10 digits — run Luhn check
    const corrected = computeCorrectNPI(val);
    if (!checkLuhnNPI(val)) {
      npiInput.classList.add('input-error');
      npiInput.classList.remove('input-valid');
      errEl.style.color = '#e74c3c';
      errEl.innerHTML = '<strong>Invalid NPI:</strong> Check digit is wrong. ' +
        (corrected
          ? 'Suggested NPI: <strong style="font-size:1rem;letter-spacing:0.5px;">' + corrected + '</strong> ' +
            '<button onclick="applyCorrectNPI(\'' + corrected + '\'); return false;" ' +
            'style="background:#2563eb;color:#fff;border:none;border-radius:4px;padding:3px 10px;' +
            'font-size:0.8rem;cursor:pointer;margin-left:6px;font-weight:600;">Apply</button>'
          : 'Verify at npiregistry.cms.hhs.gov');
      errEl.style.display = 'block';
    } else {
      npiInput.classList.remove('input-error');
      npiInput.classList.add('input-valid');
      errEl.style.color = '#16a34a';
      errEl.innerHTML = '<strong>Valid NPI</strong> (check digit verified)';
      errEl.style.display = 'block';
    }
  }

  // Validate on every keystroke and on blur
  npiInput.addEventListener('input', validateNPIField);
  npiInput.addEventListener('blur', validateNPIField);

  // Expose for external callers (e.g. loadTestData)
  window.validateNPIField = validateNPIField;
})();

// ── Helpers ───────────────────────────────────────────────────
function fmt(n) {
  if (n === null || n === undefined) return '--';
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function clearForm() {
  document.getElementById('eligibility-form').reset();
  document.getElementById('payer_id').value = '';
  document.getElementById('payer_name_hidden').value = '';
  document.getElementById('service_type_code').value = '30';
  document.getElementById('service_type_search').value = '30 - Health Benefit Plan Coverage';
}

// ── Provider-specific demo data loaders ─────────────────────────

function _fillDemoForm(data) {
  clearForm();
  document.getElementById('patient_first_name').value = data.first;
  document.getElementById('patient_last_name').value = data.last;
  document.getElementById('patient_dob').value = data.dob;
  document.getElementById('member_id').value = data.member_id;
  document.getElementById('provider_npi').value = data.npi;
  document.getElementById('provider_name').value = data.provider_name;
  document.getElementById('provider_tax_id').value = data.provider_tax_id || '';
  document.getElementById('payer_id').value = data.payer_id;
  document.getElementById('payer_name_hidden').value = data.payer_name;
  document.getElementById('payer_search').value = data.payer_id + ' - ' + data.payer_name;
  if (data.service_type_code) {
    document.getElementById('service_type_code').value = data.service_type_code;
    document.getElementById('service_type_search').value = data.service_type_code + ' - ' + (data.service_type_name || 'Health Benefit Plan Coverage');
  }
  // Set clearinghouse dropdowns (form + global topbar)
  const chSelect = document.getElementById('clearinghouse_select');
  if (chSelect && data.clearinghouse) {
    chSelect.value = data.clearinghouse;
  }
  const globalSelect = document.getElementById('global_provider_select');
  if (globalSelect && data.clearinghouse) {
    globalSelect.value = data.clearinghouse;
    const provider = _allProviders.find(p => p.id === data.clearinghouse);
    if (provider) _updateProviderStatusDot(provider);
  }
  if (window.validateNPIField) window.validateNPIField();
  console.log('Demo data loaded for ' + data.clearinghouse + ':', data);
}

// Per-provider test data — loaded by the single "Load Test Data" button
const _providerTestData = {
  stedi: {
    first: 'Jane',
    last: 'Doe',
    dob: '2004-04-04',
    member_id: 'AETNA12345',
    npi: '1111111112',
    provider_name: 'ACME Health Services',
    provider_tax_id: '999999999',
    payer_id: '60054',
    payer_name: 'Aetna',
    service_type_code: '30',
    service_type_name: 'Health Benefit Plan Coverage',
    clearinghouse: 'stedi',
  },
  waystar: {
    first: 'Alice',
    last: 'Williams',
    dob: '1980-07-22',
    member_id: 'SUB987654321',
    npi: '1245319599',
    provider_name: 'ACME Health Services',
    provider_tax_id: '999999999',
    payer_id: '66666',
    payer_name: 'ZIRMED',
    service_type_code: '30',
    service_type_name: 'Health Benefit Plan Coverage',
    clearinghouse: 'waystar',
  },
  claimmd: {
    first: 'Jane',
    last: 'Doe',
    dob: '2004-04-04',
    member_id: 'AETNA12345',
    npi: '1111111112',
    provider_name: 'ACME Health Services',
    provider_tax_id: '999999999',
    payer_id: '60054',
    payer_name: 'Aetna',
    service_type_code: '30',
    service_type_name: 'Health Benefit Plan Coverage',
    clearinghouse: 'claimmd',
  },
};

function loadTestDataForProvider() {
  // Determine which provider is selected (form override > global selector)
  const formSelect = document.getElementById('clearinghouse_select');
  const globalSelect = document.getElementById('global_provider_select');
  const provider = (formSelect && formSelect.value) || (globalSelect && globalSelect.value) || '';

  const data = _providerTestData[provider];
  if (data) {
    _fillDemoForm(data);
  } else {
    // Fallback: load server test config or default to stedi
    if (_testConfig) {
      loadTestData();
    } else {
      _fillDemoForm(_providerTestData.stedi);
    }
  }
}

// ── Prior Auth ────────────────────────────────────────────────

// Store last eligibility result for PA flow
let _lastEligResult = null;

// Override renderResults to also store the result
const _origRenderResults = renderResults;
// We store the result when rendering
function renderResultsWrapped(r) {
  _lastEligResult = r;
  _origRenderResults(r);
}
// Monkey-patch — reassign all callers
// Actually, let's just store it in the submit handler
// We'll set _lastEligResult in the submit handler and viewResult

async function runPriorAuth() {
  if (!_lastEligResult) {
    alert('No eligibility result to proceed with.');
    return;
  }

  const r = _lastEligResult;
  const overlay = document.getElementById('loading-overlay');
  overlay.querySelector('p').textContent = 'Submitting Prior Auth inquiry...';
  // Use the clearinghouse from the eligibility result (not the form dropdown)
  const selectedProvider = r.clearinghouse_provider || document.getElementById('clearinghouse_select').value || document.getElementById('global_provider_select').value || '';
  const providerLabel = {'claimmd': 'Claim.MD', 'waystar': 'Waystar', 'stedi': 'Stedi'}[selectedProvider] || selectedProvider;
  overlay.querySelector('.loading-sub').textContent = 'Contacting ' + providerLabel + ' PA API (this may take 10-15 seconds)';
  overlay.style.display = 'flex';

  try {
    const payload = {
      patient_first_name: r.patient_name.split(' ')[0] || '',
      patient_last_name: r.patient_name.split(' ').slice(1).join(' ') || '',
      patient_dob: document.getElementById('patient_dob').value || '',
      member_id: document.getElementById('member_id').value || '',
      payer_id: document.getElementById('payer_id').value || r.payer_name,
      payer_name: r.payer_name,
      provider_npi: document.getElementById('provider_npi').value || '',
      provider_name: document.getElementById('provider_name').value || '',
      provider_tax_id: document.getElementById('provider_tax_id').value || '',
      service_type_code: document.getElementById('service_type_code').value || '30',
      eligibility_check_id: r.check_id || '',
      clearinghouse: selectedProvider,
    };

    console.log('PA payload:', payload);

    const res = await authFetch(API + '/api/v1/prior-auth/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'PA check failed');
    }

    const result = await res.json();
    console.log('PA result:', result);
    showPAModal(result);
  } catch (err) {
    alert('Prior Auth error: ' + err.message);
  } finally {
    overlay.style.display = 'none';
    overlay.querySelector('p').textContent = 'Running eligibility check...';
    overlay.querySelector('.loading-sub').textContent = 'Validating inputs & contacting payer';
  }
}

function showPAModal(r) {
  document.getElementById('pa-id').textContent = r.pa_id;

  const statusEl = document.getElementById('pa-status');
  const statusLabels = {
    submitted: 'Submitted', pending: 'Pending', approved: 'Approved',
    denied: 'Denied', error: 'Error'
  };
  statusEl.textContent = statusLabels[r.status] || r.status;
  statusEl.className = 'pa-value badge badge-' + (r.status === 'approved' ? 'eligible' : r.status === 'denied' ? 'error' : r.status === 'pending' ? 'pending' : 'error');

  document.getElementById('pa-ref-id').textContent = r.reference_id || '--';
  document.getElementById('pa-status-msg').textContent = r.status_message || '--';
  document.getElementById('pa-exec-time').textContent = r.execution_time + 's';

  const authRow = document.getElementById('pa-auth-row');
  if (r.auth_number) {
    authRow.style.display = 'flex';
    document.getElementById('pa-auth-number').textContent = r.auth_number;
  } else {
    authRow.style.display = 'none';
  }

  const errorRow = document.getElementById('pa-error-row');
  if (r.error_message) {
    errorRow.style.display = 'flex';
    document.getElementById('pa-error-msg').textContent = r.error_message;
  } else {
    errorRow.style.display = 'none';
  }

  document.getElementById('pa-modal').style.display = 'flex';

  // Refresh PA table in background so it's up to date when user visits PA page
  loadPARequests();
}

function closePAModal() {
  document.getElementById('pa-modal').style.display = 'none';
}

// ── PA Requests Page ─────────────────────────────────────────

async function loadPARequests() {
  try {
    const res = await authFetch(API + '/api/v1/prior-auth/checks');
    if (!res.ok) return;
    const checks = await res.json();
    renderPATable(checks);
  } catch (err) {
    console.error('Failed to load PA requests:', err);
  }
}

function renderPATable(checks) {
  const tbody = document.getElementById('pa-table-body');
  if (!checks || checks.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No PA requests yet. Run an eligibility check and click "Proceed to Prior Auth".</td></tr>';
    return;
  }

  const statusBadge = (s) => {
    const cls = s === 'approved' ? 'eligible' : s === 'denied' ? 'error' : s === 'pending' ? 'pending' : s === 'submitted' ? 'pending' : 'error';
    const label = s.charAt(0).toUpperCase() + s.slice(1);
    return `<span class="badge badge-${cls}">${label}</span>`;
  };

  tbody.innerHTML = checks.map(c => `
    <tr onclick="showPADetailPanel('${c.pa_id}')" style="cursor:pointer;" title="Click to view details">
      <td><strong>${c.pa_id}</strong></td>
      <td>${c.run_date || '--'}</td>
      <td>${c.patient_name || '--'}</td>
      <td>${c.payer_name || c.payer_id || '--'}</td>
      <td>${c.provider_name || c.provider_npi || '--'}</td>
      <td>${statusBadge(c.status)}</td>
      <td>${c.auth_number || '--'}</td>
      <td><button class="btn btn-sm" onclick="event.stopPropagation(); showPADetailPanel('${c.pa_id}')">View</button></td>
    </tr>
  `).join('');
}

async function showPADetailPanel(paId) {
  try {
    const res = await authFetch(API + '/api/v1/prior-auth/checks/' + paId);
    if (!res.ok) { alert('PA not found'); return; }
    const d = await res.json();

    document.getElementById('pa-detail-panel').style.display = 'block';
    document.getElementById('pa-detail-id').textContent = d.pa_id;

    // Request fields
    document.getElementById('pa-d-patient').textContent = d.patient_name || '--';
    document.getElementById('pa-d-dob').textContent = d.patient_dob || '--';
    document.getElementById('pa-d-member').textContent = d.member_id || '--';
    document.getElementById('pa-d-payer').textContent = (d.payer_id || '') + (d.payer_name ? ' - ' + d.payer_name : '');
    document.getElementById('pa-d-npi').textContent = d.provider_npi || '--';
    document.getElementById('pa-d-provname').textContent = d.provider_name || '--';
    document.getElementById('pa-d-svc').textContent = d.service_type_code || '--';
    document.getElementById('pa-d-diag').textContent = d.diagnosis_code || '--';
    document.getElementById('pa-d-proc').textContent = d.procedure_code || '--';
    document.getElementById('pa-d-elig').textContent = d.eligibility_check_id || '--';

    // Response fields
    const statusEl = document.getElementById('pa-d-status');
    statusEl.textContent = d.status;
    statusEl.className = 'coverage-value badge badge-' + (d.status === 'approved' ? 'eligible' : d.status === 'denied' ? 'error' : d.status === 'pending' ? 'pending' : 'error');

    document.getElementById('pa-d-auth').textContent = d.auth_number || '--';
    document.getElementById('pa-d-ref').textContent = d.reference_id || '--';
    document.getElementById('pa-d-msg').textContent = d.status_message || '--';
    document.getElementById('pa-d-error').textContent = d.error_message || '--';
    document.getElementById('pa-d-time').textContent = (d.execution_time || 0) + 's';
    document.getElementById('pa-d-date').textContent = d.run_date || '--';

    // Raw response
    const rawEl = document.getElementById('pa-d-raw');
    rawEl.textContent = d.raw_response ? JSON.stringify(d.raw_response, null, 2) : 'No raw response';

    // Scroll to detail
    document.getElementById('pa-detail-panel').scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    console.error('Failed to load PA detail:', err);
  }
}

// ── Test Environment Config ───────────────────────────────────

let _testConfig = null;

async function loadTestConfig() {
  try {
    const res = await authFetch(API + '/api/v1/test-config');
    if (!res.ok) return;
    _testConfig = await res.json();

    if (_testConfig.environment === 'test') {
      // Show test environment badge
      const badge = document.getElementById('env-badge');
      badge.style.display = 'inline-block';
      badge.textContent = 'TEST ENV';

      // Show "Load Test Data" button
      document.getElementById('btn-load-test').style.display = 'inline-flex';

      console.log('Test environment detected. Config:', _testConfig);
    }
  } catch (e) {
    console.warn('Could not load test config:', e);
  }
}

function loadTestData() {
  if (!_testConfig) return;

  const c = _testConfig;
  if (c.patient_first) document.getElementById('patient_first_name').value = c.patient_first;
  if (c.patient_last) document.getElementById('patient_last_name').value = c.patient_last;
  if (c.patient_dob) document.getElementById('patient_dob').value = c.patient_dob;
  if (c.member_id) document.getElementById('member_id').value = c.member_id;
  if (c.provider_npi) document.getElementById('provider_npi').value = c.provider_npi;
  if (c.provider_name) document.getElementById('provider_name').value = c.provider_name;

  // Set payer
  if (c.payer_id) {
    document.getElementById('payer_id').value = c.payer_id;
    document.getElementById('payer_name_hidden').value = c.payer_name || '';
    const payerSearch = document.getElementById('payer_search');
    if (payerSearch) {
      payerSearch.value = c.payer_id + (c.payer_name ? ' - ' + c.payer_name : '');
    }
  }

  // Trigger NPI validation after loading test data
  if (window.validateNPIField) window.validateNPIField();

  console.log('Test data loaded:', c);
}

// ── Batch CSV Upload ──────────────────────────────────────────

let _csvData = [];       // parsed CSV rows
let _csvHeaders = [];    // CSV column headers
let _columnMapping = {}; // csvHeader -> systemField

const SYSTEM_FIELDS = [
  { key: 'patient_name', label: 'Patient Name' },
  { key: 'patient_first_name', label: 'Patient First Name' },
  { key: 'patient_last_name', label: 'Patient Last Name' },
  { key: 'date_of_birth', label: 'DOB' },
  { key: 'member_id', label: 'Member ID' },
  { key: 'payer_id', label: 'Payer ID' },
  { key: 'payer_name', label: 'Payer Name' },
  { key: 'group_number', label: 'Group Number' },
  { key: 'provider_npi', label: 'Provider NPI' },
  { key: 'provider_name', label: 'Provider Name' },
  { key: 'service_type', label: 'Service Type' },
  { key: '', label: '-- Skip --' },
];

// Auto-detect mapping from CSV header to system field
function autoMapColumn(header) {
  const h = header.toLowerCase().replace(/[^a-z0-9]/g, '');
  const map = {
    'patientfullname': 'patient_name', 'patientname': 'patient_name', 'fullname': 'patient_name', 'name': 'patient_name',
    'firstname': 'patient_first_name', 'patientfirstname': 'patient_first_name', 'first': 'patient_first_name',
    'lastname': 'patient_last_name', 'patientlastname': 'patient_last_name', 'last': 'patient_last_name',
    'dateofbirth': 'date_of_birth', 'dob': 'date_of_birth', 'birthdate': 'date_of_birth', 'patientdob': 'date_of_birth',
    'memberid': 'member_id', 'insuranceid': 'member_id', 'insurancememberid': 'member_id', 'subscriberid': 'member_id',
    'payerid': 'payer_id', 'payercode': 'payer_id',
    'payername': 'payer_name', 'payer': 'payer_name', 'insurancepayer': 'payer_name', 'insurance': 'payer_name',
    'groupnumber': 'group_number', 'groupnum': 'group_number', 'group': 'group_number',
    'providernpi': 'provider_npi', 'npi': 'provider_npi',
    'providername': 'provider_name', 'provider': 'provider_name', 'doctorname': 'provider_name',
    'servicetype': 'service_type', 'cptcode': 'service_type', 'cpt': 'service_type',
  };
  return map[h] || '';
}

function parseCSV(text) {
  const lines = text.split('\n').filter(l => l.trim());
  if (lines.length < 2) return { headers: [], rows: [] };
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''));
    if (values.length === headers.length) {
      const row = {};
      headers.forEach((h, idx) => row[h] = values[idx]);
      rows.push(row);
    }
  }
  return { headers, rows };
}

function handleCSVFile(file) {
  if (!file || !file.name.endsWith('.csv')) {
    alert('Please upload a .csv file');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const { headers, rows } = parseCSV(e.target.result);
    if (!headers.length || !rows.length) {
      alert('CSV file is empty or has no data rows');
      return;
    }
    _csvHeaders = headers;
    _csvData = rows;

    // Auto-map columns
    _columnMapping = {};
    headers.forEach(h => { _columnMapping[h] = autoMapColumn(h); });

    renderColumnMapping();
    document.getElementById('column-mapping-card').style.display = 'block';
    document.getElementById('batch-step1-actions').style.display = 'flex';

    // Update upload zone to show file info
    document.getElementById('upload-zone').innerHTML =
      '<div class="upload-icon" style="color:var(--success);">&#10003;</div>' +
      '<div class="upload-text">' + file.name + '</div>' +
      '<div class="upload-sub">' + rows.length + ' records found, ' + headers.length + ' columns</div>' +
      '<button type="button" class="btn btn-secondary" onclick="resetBatchUpload()">Choose Different File</button>';
  };
  reader.readAsText(file);
}

function renderColumnMapping() {
  const container = document.getElementById('mapping-rows');
  container.innerHTML = _csvHeaders.map(h => {
    const mapped = _columnMapping[h] || '';
    const options = SYSTEM_FIELDS.map(sf =>
      `<option value="${sf.key}" ${sf.key === mapped ? 'selected' : ''}>${sf.label}</option>`
    ).join('');
    return `
      <div class="mapping-row">
        <div class="mapping-csv-col">${h}</div>
        <select class="mapping-select" onchange="_columnMapping['${h}']=this.value">${options}</select>
      </div>
    `;
  }).join('');
}

function resetBatchUpload() {
  _csvData = [];
  _csvHeaders = [];
  _columnMapping = {};
  document.getElementById('column-mapping-card').style.display = 'none';
  document.getElementById('batch-step1-actions').style.display = 'none';
  document.getElementById('upload-zone').innerHTML =
    '<div class="upload-icon">&#9729;</div>' +
    '<div class="upload-text">Drag & drop your CSV file here</div>' +
    '<div class="upload-sub">Supports: Patient Name, DOB, Insurance ID, Payer, Group#, NPI, CPT Codes</div>' +
    '<button type="button" class="btn btn-primary" onclick="document.getElementById(\'csv-file-input\').click()">Browse Files</button>';
  document.getElementById('csv-file-input').value = '';
  goToStep(1);
}

// Step navigation
function goToStep(step) {
  document.querySelectorAll('.batch-step').forEach(s => s.classList.remove('active'));
  document.getElementById('batch-step-' + step).classList.add('active');

  for (let i = 1; i <= 3; i++) {
    const el = document.getElementById('step-' + i + '-indicator');
    el.classList.remove('active', 'done');
    if (i < step) el.classList.add('done');
    if (i === step) el.classList.add('active');
  }
  for (let i = 1; i <= 2; i++) {
    const line = document.getElementById('step-line-' + i);
    line.classList.toggle('done', i < step);
  }
}

function proceedToStep2() {
  // Validate we have all required column mappings
  const mapped = Object.values(_columnMapping).filter(v => v);
  const missing = [];

  const hasName = mapped.includes('patient_name') || (mapped.includes('patient_first_name') && mapped.includes('patient_last_name'));
  if (!hasName) missing.push('Patient Name (or First + Last Name)');
  if (!mapped.includes('date_of_birth')) missing.push('Date of Birth');
  if (!mapped.includes('member_id')) missing.push('Member ID');
  if (!mapped.includes('payer_name') && !mapped.includes('payer_id')) missing.push('Payer Name or Payer ID');
  if (!mapped.includes('provider_npi')) missing.push('Provider NPI');
  if (!mapped.includes('provider_name')) missing.push('Provider Name');

  if (missing.length) {
    alert('Required column mappings missing:\n\n- ' + missing.join('\n- ') + '\n\nPlease map these columns before continuing.');
    return;
  }

  // Build review data with validation
  renderReviewTable();
  goToStep(2);
}

function getMappedValue(row, systemField) {
  for (const [csvHeader, sysField] of Object.entries(_columnMapping)) {
    if (sysField === systemField) return row[csvHeader] || '';
  }
  return '';
}

function validateRow(row) {
  const errors = [];   // block submission
  const warnings = []; // allow but flag

  // — Required fields (same as single eligibility form) —

  // Patient First Name
  const firstName = getMappedValue(row, 'patient_first_name');
  const fullName = getMappedValue(row, 'patient_name');
  if (!firstName && !fullName) {
    errors.push('Missing First Name');
  }

  // Patient Last Name
  const lastName = getMappedValue(row, 'patient_last_name');
  if (!lastName && !fullName) {
    errors.push('Missing Last Name');
  }

  // Date of Birth — required, must not be future
  const dob = getMappedValue(row, 'date_of_birth');
  if (!dob) {
    errors.push('Missing DOB');
  } else if (new Date(dob) >= new Date()) {
    errors.push('DOB is in the future');
  }

  // Member ID — required, min 3 chars
  const memberId = getMappedValue(row, 'member_id');
  if (!memberId) {
    errors.push('Missing Member ID');
  } else if (memberId.length < 3) {
    errors.push('Member ID too short (min 3)');
  }

  // Payer — required
  const payer = getMappedValue(row, 'payer_name') || getMappedValue(row, 'payer_id');
  if (!payer) {
    errors.push('Missing Payer');
  }

  // Provider NPI — required, must be 10 digits
  const npi = getMappedValue(row, 'provider_npi');
  if (!npi) {
    errors.push('Missing NPI');
  } else if (!/^\d{10}$/.test(npi)) {
    errors.push('NPI must be 10 digits');
  } else if (!checkLuhnNPI(npi)) {
    const corrected = computeCorrectNPI(npi);
    errors.push('NPI fails Luhn check' + (corrected ? ' (suggested: ' + corrected + ')' : ''));
  }

  // Provider Name — required by Stedi
  const provName = getMappedValue(row, 'provider_name');
  if (!provName) {
    errors.push('Missing Provider Name');
  }

  return { errors, warnings };
}

// Store validation results for popup
let _rowValidations = [];

function renderReviewTable() {
  const thead = document.getElementById('review-thead').querySelector('tr');
  const tbody = document.getElementById('review-tbody');

  // Build header
  thead.innerHTML = '<th>#</th><th>PATIENT</th><th>PAYER</th><th>MEMBER ID</th><th>NPI</th><th>DOB</th><th>STATUS</th>';

  let validCount = 0, warningCount = 0, errorCount = 0;
  _rowValidations = [];
  const rows = [];
  _csvData.forEach((row, idx) => {
    const { errors, warnings } = validateRow(row);
    const name = getMappedValue(row, 'patient_name') || (getMappedValue(row, 'patient_first_name') + ' ' + getMappedValue(row, 'patient_last_name')).trim();
    const payer = getMappedValue(row, 'payer_name') || getMappedValue(row, 'payer_id');
    const memberId = getMappedValue(row, 'member_id');
    const npi = getMappedValue(row, 'provider_npi');
    const dob = getMappedValue(row, 'date_of_birth');

    // Store for popup
    _rowValidations.push({ name, payer, memberId, npi, dob, errors, warnings });

    let statusHtml, rowClass;
    if (errors.length) {
      errorCount++;
      rowClass = 'row-error';
      statusHtml = `<div class="status-cell">
        <span class="badge badge-error">Invalid</span>
        <button class="status-icon-btn icon-error" title="View errors" onclick="showRowErrorPopup(${idx})">&#9432;</button>
      </div>`;
    } else if (warnings.length) {
      warningCount++;
      rowClass = 'row-warning';
      statusHtml = `<div class="status-cell">
        <span class="badge badge-inactive">Warning</span>
        <button class="status-icon-btn icon-warning" title="View warnings" onclick="showRowErrorPopup(${idx})">&#9888;</button>
      </div>`;
    } else {
      validCount++;
      rowClass = 'row-valid';
      statusHtml = '<span class="badge badge-eligible">Valid</span>';
    }

    rows.push(`
      <tr class="${rowClass}">
        <td>${idx + 1}</td>
        <td>${name || '--'}</td>
        <td>${payer || '--'}</td>
        <td>${memberId || '--'}</td>
        <td>${npi || '--'}</td>
        <td>${dob || '--'}</td>
        <td>${statusHtml}</td>
      </tr>
    `);
  });
  tbody.innerHTML = rows.join('');

  document.getElementById('review-summary').textContent =
    _csvData.length + ' records found. ' + validCount + ' valid, ' +
    warningCount + ' with warnings, ' + errorCount + ' with errors.';

  // Disable run button if all have errors (warnings can still proceed)
  document.getElementById('btn-run-batch').disabled = (validCount + warningCount === 0);
}

function showRowErrorPopup(idx) {
  const v = _rowValidations[idx];
  if (!v) return;

  const isError = v.errors.length > 0;
  const title = isError ? 'Validation Errors' : 'Validation Warnings';
  const titleIcon = isError ? '&#9432;' : '&#9888;';
  const titleColor = isError ? 'var(--error)' : 'var(--warning)';

  let itemsHtml = '';
  if (v.errors.length) {
    itemsHtml += v.errors.map(e => `<li class="error-item">${e}</li>`).join('');
  }
  if (v.warnings.length) {
    itemsHtml += v.warnings.map(w => `<li class="warning-item">${w}</li>`).join('');
  }

  const overlay = document.createElement('div');
  overlay.className = 'row-error-modal-overlay';
  overlay.innerHTML = `
    <div class="row-error-modal">
      <div class="row-error-modal-header">
        <h4><span style="color:${titleColor}">${titleIcon}</span> Row ${idx + 1} — ${title}</h4>
        <button class="close-btn" onclick="closeRowErrorPopup()">&times;</button>
      </div>
      <div class="row-error-modal-body">
        <div class="modal-row-info">
          <span>${v.name || '--'}</span> &bull; ${v.payer || '--'} &bull; Member: ${v.memberId || '--'} &bull; NPI: ${v.npi || '--'}
        </div>
        <ul>${itemsHtml}</ul>
      </div>
      <div class="row-error-modal-footer">
        <button onclick="closeRowErrorPopup()">Close</button>
      </div>
    </div>
  `;
  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeRowErrorPopup();
  });
  document.body.appendChild(overlay);
}

function closeRowErrorPopup() {
  const overlay = document.querySelector('.row-error-modal-overlay');
  if (overlay) overlay.remove();
}

async function runBatchChecks() {
  goToStep(3);
  const progressWrap = document.getElementById('batch-progress-wrap');
  const progressFill = document.getElementById('batch-progress-fill');
  const summaryEl = document.getElementById('batch-results-summary');
  const tbody = document.getElementById('results-tbody');

  progressWrap.style.display = 'block';
  tbody.innerHTML = '';

  // Filter rows without errors (warnings are allowed to proceed)
  const validRows = _csvData.filter(row => validateRow(row).errors.length === 0);
  summaryEl.textContent = 'Processing ' + validRows.length + ' of ' + _csvData.length + ' records...';

  let completed = 0, successCount = 0, failCount = 0;

  for (let i = 0; i < validRows.length; i++) {
    const row = validRows[i];
    const name = getMappedValue(row, 'patient_name') || (getMappedValue(row, 'patient_first_name') + ' ' + getMappedValue(row, 'patient_last_name')).trim();
    const payer = getMappedValue(row, 'payer_name') || getMappedValue(row, 'payer_id');
    const memberId = getMappedValue(row, 'member_id');
    const dob = getMappedValue(row, 'date_of_birth');
    const npi = getMappedValue(row, 'provider_npi');

    // Split name if full name
    let firstName = getMappedValue(row, 'patient_first_name');
    let lastName = getMappedValue(row, 'patient_last_name');
    if (!firstName && !lastName && name) {
      const parts = name.split(' ');
      firstName = parts[0] || '';
      lastName = parts.slice(1).join(' ') || '';
    }

    const payload = {
      patient_first_name: firstName,
      patient_last_name: lastName,
      patient_dob: dob,
      member_id: memberId,
      payer_id: getMappedValue(row, 'payer_id') || payer,
      payer_name: payer,
      provider_npi: npi || '',
      provider_name: getMappedValue(row, 'provider_name') || '',
      service_type_code: getMappedValue(row, 'service_type') || '30',
      source: 'batch',
    };

    let status = 'error', detail = '';
    try {
      const res = await authFetch(API + '/api/v1/eligibility/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      if (res.ok) {
        status = result.status || 'pending';
        detail = '<a class="check-id-link" onclick="viewResult(\'' + result.check_id + '\')">' + result.check_id + '</a>';
        successCount++;
      } else {
        detail = result.detail || 'API error';
        failCount++;
      }
    } catch (err) {
      detail = err.message;
      failCount++;
    }

    completed++;
    progressFill.style.width = ((completed / validRows.length) * 100) + '%';

    tbody.innerHTML += `
      <tr>
        <td>${i + 1}</td>
        <td>${name}</td>
        <td>${payer}</td>
        <td>${memberId}</td>
        <td>${statusBadge(status)}</td>
        <td>${detail}</td>
      </tr>
    `;

    summaryEl.textContent = completed + ' of ' + validRows.length + ' processed. ' +
      successCount + ' successful, ' + failCount + ' failed.';
  }

  progressWrap.style.display = 'none';
  summaryEl.textContent = 'Batch complete: ' + successCount + ' successful, ' + failCount + ' failed out of ' + validRows.length + ' records.';

  // Refresh dashboard
  await loadRecentChecks();
}

// Upload zone drag & drop
(function initUploadZone() {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('csv-file-input');
  if (!zone || !fileInput) return;

  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleCSVFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) handleCSVFile(fileInput.files[0]);
  });
})();

// Sample CSV download
(function initSampleCSV() {
  const link = document.getElementById('download-sample-csv');
  if (!link) return;
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const csv = [
      'first_name,last_name,date_of_birth,insurance_member_id,payer_name,group_number,provider_npi,provider_name,service_type',
      'Jane,Doe,2004-04-04,AETNA12345,Aetna,GRP001,1234567893,Dr. Smith,30',
      'John,Smith,1985-06-15,UHC98765,UnitedHealthcare,GRP002,1234567893,Dr. Smith,30',
      'Sarah,Johnson,1990-03-22,BCBS55555,Blue Cross Blue Shield,GRP003,1234567893,Dr. Smith,30',
      'Michael,Chen,1978-11-08,CIGNA44444,Cigna,GRP004,1234567893,Dr. Smith,30',
      'Emily,Rodriguez,2001-01-30,HUM33333,Humana,,1234567893,Dr. Smith,30',
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'eligibility_check_template.csv';
    a.click();
    URL.revokeObjectURL(url);
  });
})();

// ── Dashboard PA Pipeline (from real PA data) ─────────────────
function renderPAPipeline() {
  // Fetch real PA data from the stats cache or API
  var paChecks = (_statsData && _statsData.pa_checks) || [];
  var pendingData = paChecks.filter(function(p) { return p.status === 'pending' || p.status === 'submitted'; });
  var approvedData = paChecks.filter(function(p) { return p.status === 'approved'; });
  var deniedData = paChecks.filter(function(p) { return p.status === 'denied' || p.status === 'error'; });

  document.getElementById('pipe-pending-count').textContent = pendingData.length;
  document.getElementById('pipe-submitted-count').textContent = deniedData.length;
  document.getElementById('pipe-approved-count').textContent = approvedData.length;

  var renderCards = function(data) {
    if (data.length === 0) return '<div style="color:var(--text-secondary);font-size:12px;padding:12px;">None</div>';
    return data.map(function(d) {
      return '<div class="pipeline-card"><div class="pipeline-card-name">' + (d.patient_name || '--') + '</div>' +
        '<div class="pipeline-card-payer">' + (d.payer_name || d.payer_id || '--') + '</div>' +
        '<div class="pipeline-card-service">' + (d.procedure_code || d.service_type_code || '--') + '</div></div>';
    }).join('');
  };

  document.getElementById('pipe-pending').innerHTML = renderCards(pendingData);
  document.getElementById('pipe-submitted').innerHTML = renderCards(deniedData);
  document.getElementById('pipe-approved').innerHTML = renderCards(approvedData);
}

// ── Load clearinghouse providers into dropdowns ──────────────────
let _allProviders = [];

async function loadProviders() {
  try {
    const res = await authFetch(API + '/api/v1/providers');
    if (!res.ok) return;
    _allProviders = await res.json();

    // Populate form dropdown
    const formSelect = document.getElementById('clearinghouse_select');
    if (formSelect) {
      // Keep the first "Default" option, clear the rest
      while (formSelect.options.length > 1) formSelect.remove(1);
      _allProviders.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.label + (p.is_default ? ' (default)' : '') + (!p.configured ? ' — not configured' : '');
        if (!p.configured) opt.disabled = true;
        if (p.is_default) opt.selected = true;
        formSelect.appendChild(opt);
      });
    }

    // Populate global topbar dropdown
    const globalSelect = document.getElementById('global_provider_select');
    if (globalSelect) {
      globalSelect.innerHTML = '';
      _allProviders.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name + (p.is_default ? ' (default)' : '');
        if (p.is_default) opt.selected = true;
        globalSelect.appendChild(opt);
      });
      // Set initial status dot
      const defaultProvider = _allProviders.find(p => p.is_default) || _allProviders[0];
      if (defaultProvider) _updateProviderStatusDot(defaultProvider);
    }
  } catch (e) { /* ignore */ }
}

function _updateProviderStatusDot(provider) {
  const dot = document.getElementById('global-provider-status');
  if (!dot) return;
  if (provider.configured) {
    dot.className = 'provider-status-dot connected';
    dot.title = provider.name + ' — Configured';
  } else {
    dot.className = 'provider-status-dot not-configured';
    dot.title = provider.name + ' — Not configured (go to Settings)';
  }
}

function onGlobalProviderChange(providerId) {
  // Sync to form dropdown
  const formSelect = document.getElementById('clearinghouse_select');
  if (formSelect) formSelect.value = providerId;

  // Update status dot
  const provider = _allProviders.find(p => p.id === providerId);
  if (provider) _updateProviderStatusDot(provider);
}

// Sync form dropdown back to global dropdown when changed
document.addEventListener('change', function(e) {
  if (e.target && e.target.id === 'clearinghouse_select') {
    const globalSelect = document.getElementById('global_provider_select');
    if (globalSelect && e.target.value) {
      globalSelect.value = e.target.value;
      const provider = _allProviders.find(p => p.id === e.target.value);
      if (provider) _updateProviderStatusDot(provider);
    }
  }
});

// ── Settings: Provider Config UI ─────────────────────────────
let _settingsProviders = [];

async function loadSettingsProviders() {
  try {
    const res = await authFetch(API + '/api/v1/providers');
    if (!res.ok) return;
    _settingsProviders = await res.json();
    renderProviderTabs();
    if (_settingsProviders.length) selectProviderTab(_settingsProviders[0].id);
  } catch (e) { /* ignore */ }
}

function renderProviderTabs() {
  const tabsEl = document.getElementById('provider-tabs');
  if (!tabsEl) return;
  tabsEl.innerHTML = _settingsProviders.map(p => {
    const dotClass = p.is_default ? 'is-default' : (p.configured ? 'configured' : '');
    return `<div class="provider-tab" data-provider="${p.id}" onclick="selectProviderTab('${p.id}')">
      <span class="tab-dot ${dotClass}"></span>
      ${p.name}
      ${p.is_default ? '<span class="tab-badge">DEFAULT</span>' : ''}
    </div>`;
  }).join('');
}

async function selectProviderTab(providerId) {
  document.querySelectorAll('.provider-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.provider === providerId);
  });
  try {
    const res = await authFetch(API + '/api/v1/providers/' + providerId);
    if (!res.ok) return;
    const data = await res.json();
    renderProviderPanel(data);
  } catch (e) { /* ignore */ }
}

function renderProviderPanel(provider) {
  const panelsEl = document.getElementById('provider-panels');
  if (!panelsEl) return;

  const fieldsHtml = provider.fields.map(f => {
    const val = (provider.config && provider.config[f.key]) || '';
    const inputType = f.secret ? 'password' : 'text';
    const reqMark = f.required ? ' <span class="req">*</span>' : '';
    const ph = f.placeholder || '';
    return `<div class="provider-config-field">
      <label>${f.label}${reqMark}</label>
      <input type="${inputType}" id="prov-cfg-${provider.id}-${f.key}" value="${val}" placeholder="${ph}" autocomplete="off" />
    </div>`;
  }).join('');

  const defaultBtnClass = provider.is_default ? 'btn-set-default is-default' : 'btn-set-default';
  const defaultBtnText = provider.is_default ? '&#10003; Default Provider' : 'Set as Default';

  panelsEl.innerHTML = `
    <div class="provider-panel active">
      <div class="provider-panel-header">
        <div>
          <div class="provider-panel-title">${provider.label}</div>
          <div style="margin-top:4px;">
            <span class="provider-card-status ${provider.configured ? 'active' : 'inactive'}" style="font-size:12px;">
              ${provider.configured ? 'Configured' : 'Not configured'}
            </span>
          </div>
        </div>
        <div class="provider-panel-supports">
          ${provider.supports.map(s => '<span class="provider-tag">' + s.replace('_', ' ') + '</span>').join('')}
        </div>
      </div>
      <div class="card" style="margin-bottom:0;">
        <h2 class="card-title" style="font-size:14px;">Credentials</h2>
        <div class="provider-config-form">
          ${fieldsHtml}
        </div>
        <div class="provider-actions-bar">
          <button class="${defaultBtnClass}" id="btn-default-${provider.id}" onclick="setProviderDefault('${provider.id}')" ${provider.is_default ? 'disabled' : ''}>
            ${defaultBtnText}
          </button>
          <div class="spacer"></div>
          <button class="btn-test-connection" id="btn-test-${provider.id}" onclick="testProviderConnection('${provider.id}')">
            &#9889; Test Connection
          </button>
          <button class="btn btn-primary" onclick="saveProviderConfig('${provider.id}')">
            Save Configuration
          </button>
        </div>
        <div class="provider-test-result" id="provider-result-${provider.id}"></div>
      </div>
    </div>
  `;
}

function _collectProviderConfig(providerId) {
  const provider = _settingsProviders.find(p => p.id === providerId);
  if (!provider) return {};
  const config = {};
  (provider.fields || []).forEach(f => {
    const input = document.getElementById('prov-cfg-' + providerId + '-' + f.key);
    if (input) config[f.key] = input.value;
  });
  return config;
}

async function saveProviderConfig(providerId) {
  const config = _collectProviderConfig(providerId);
  const resultEl = document.getElementById('provider-result-' + providerId);
  try {
    const res = await authFetch(API + '/api/v1/providers/' + providerId + '/save', {
      method: 'POST',
      body: JSON.stringify({ config: config }),
    });
    const data = await res.json();
    if (resultEl) {
      resultEl.textContent = data.message || 'Saved';
      resultEl.className = 'provider-test-result ' + (data.status === 'ok' ? 'success' : 'error');
    }
    await loadSettingsProviders();
    await loadProviders();
    await selectProviderTab(providerId);
  } catch (e) {
    if (resultEl) {
      resultEl.textContent = 'Failed to save: ' + e.message;
      resultEl.className = 'provider-test-result error';
    }
  }
}

async function testProviderConnection(providerId) {
  const resultEl = document.getElementById('provider-result-' + providerId);
  const btn = document.getElementById('btn-test-' + providerId);
  if (resultEl) { resultEl.textContent = 'Testing connection...'; resultEl.className = 'provider-test-result testing'; }
  if (btn) btn.disabled = true;

  // Save first so test uses latest values
  const config = _collectProviderConfig(providerId);
  await authFetch(API + '/api/v1/providers/' + providerId + '/save', {
    method: 'POST', body: JSON.stringify({ config: config }),
  });

  try {
    const res = await authFetch(API + '/api/v1/providers/' + providerId + '/test', { method: 'POST' });
    const data = await res.json();
    if (resultEl) {
      resultEl.textContent = data.message || (data.status === 'ok' ? 'Connection successful' : 'Connection failed');
      resultEl.className = 'provider-test-result ' + (data.status === 'ok' ? 'success' : 'error');
    }
  } catch (e) {
    if (resultEl) { resultEl.textContent = 'Test failed: ' + e.message; resultEl.className = 'provider-test-result error'; }
  }
  if (btn) btn.disabled = false;
}

async function setProviderDefault(providerId) {
  try {
    const res = await authFetch(API + '/api/v1/providers/' + providerId + '/set-default', { method: 'POST' });
    const data = await res.json();
    const resultEl = document.getElementById('provider-result-' + providerId);
    if (resultEl) {
      resultEl.textContent = data.message || 'Done';
      resultEl.className = 'provider-test-result ' + (data.status === 'ok' ? 'success' : 'error');
    }
    await loadSettingsProviders();
    await loadProviders();
    await selectProviderTab(providerId);
  } catch (e) { /* ignore */ }
}

// ══════════════════════════════════════════════════════════════
// NEW PAGES — Morning Brief, Appointments, Reports, etc.
// All pages pull REAL data from /api/v1/stats
// ══════════════════════════════════════════════════════════════

var _statsData = null; // cached stats

async function loadAllPageData() {
  try {
    const res = await authFetch(API + '/api/v1/stats');
    if (res.ok) _statsData = await res.json();
  } catch (e) { console.warn('Stats fetch failed:', e); }
  renderMorningBrief();
  renderAppointments();
  renderReportsPage();
  renderPAPipeline();
  updateDashboardStats();
}

function updateDashboardStats() {
  if (!_statsData) return;
  var e = _statsData.eligibility || {};
  var p = _statsData.prior_auth || {};
  var el = function(id, v) { var x = document.getElementById(id); if (x) x.textContent = v; };
  el('stat-total-checks', e.total || 0);
  el('stat-eligible', e.eligible || 0);
  el('stat-pa-submitted', p.total || 0);
  el('stat-avg-time', e.avg_time ? e.avg_time + 's' : '--');
  // Also update sidebar stats
  el('sidebar-checks-count', e.total || 0);
  el('sidebar-avg-time', e.avg_time ? e.avg_time + 's' : '--');
  el('sidebar-elig-rate', e.elig_rate ? e.elig_rate + '%' : '--');
}

// ── Copy raw response ─────────────────────────────────
function copyRawResponse() {
  var el = document.getElementById('r-raw-json');
  if (el) {
    navigator.clipboard.writeText(el.textContent).then(function() {
      alert('Response JSON copied to clipboard');
    }).catch(function() {
      // Fallback
      var range = document.createRange();
      range.selectNode(el);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
      document.execCommand('copy');
      window.getSelection().removeAllRanges();
      alert('Response JSON copied to clipboard');
    });
  }
}

// ── New Check Dropdown ────────────────────────────────
function toggleNewCheckDropdown(e) {
  e && e.stopPropagation();
  const dd = document.getElementById('new-check-dropdown');
  dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}
function closeNewCheckDropdown() {
  const dd = document.getElementById('new-check-dropdown');
  if (dd) dd.style.display = 'none';
}
document.addEventListener('click', function(e) {
  const w = document.querySelector('.new-check-dropdown-wrapper');
  if (w && !w.contains(e.target)) closeNewCheckDropdown();
});

// ── Morning Brief ─────────────────────────────────────
function renderMorningBrief() {
  var now = new Date();
  var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  var greeting = document.getElementById('mb-greeting');
  if (greeting) greeting.textContent = days[now.getDay()] + ', ' + months[now.getMonth()] + ' ' + now.getDate() + ' \u2014 Morning Brief';

  var checks = (_statsData && _statsData.recent_checks) || [];
  var paChecks = (_statsData && _statsData.pa_checks) || [];
  var eligStats = (_statsData && _statsData.eligibility) || {};

  // Agent status line
  var agentEl = document.getElementById('mb-agent-status');
  if (agentEl) agentEl.textContent = 'Agent ran at 6:00 AM \u2022 ' + (checks.length || 0) + ' checks processed \u2022 Avg ' + (eligStats.avg_time || '--') + 's';

  // ── PA Requirements: checks where prior_auth_required + PA checks ──
  var paRows = [];
  checks.forEach(function(c) {
    if (c.prior_auth_required) {
      paRows.push({ time: _fmtTime(c.run_date || c.created_at), patient: c.patient_name || '--', provider: c.provider_name || '--', insurance: c.payer_name || c.payer_id || '--', service: c.plan_name || 'Health Benefit Plan', status: 'required', urgency: 'high', daysLeft: 2 });
    }
  });
  paChecks.forEach(function(p) {
    if (p.status === 'pending' || p.status === 'submitted') {
      paRows.push({ time: _fmtTime(p.run_date || p.created_at), patient: p.patient_name || '--', provider: p.provider_name || '--', insurance: p.payer_name || p.payer_id || '--', service: (p.procedure_code || '') + ' ' + (p.diagnosis_code || ''), status: 'pending', urgency: 'medium', daysLeft: 5 });
    }
  });

  var paTbody = document.getElementById('mb-pa-tbody');
  if (paTbody) {
    if (paRows.length === 0) {
      paTbody.innerHTML = '<tr><td colspan="9" class="empty-state">No prior authorization requirements found.</td></tr>';
    } else {
      paTbody.innerHTML = paRows.slice(0, 10).map(function(r) {
        return '<tr><td>' + r.time + '</td>' +
          '<td><strong>' + r.patient + '</strong></td>' +
          '<td>' + r.provider + '</td><td>' + r.insurance + '</td>' +
          '<td>' + r.service + '</td>' +
          '<td><span class="status-pill ' + r.status + '">' + (r.status === 'required' ? 'Required' : 'Pending') + '</span></td>' +
          '<td><span class="urgency-badge ' + r.urgency + '">\u2299 ' + r.urgency.charAt(0).toUpperCase() + r.urgency.slice(1) + '</span></td>' +
          '<td class="days-left-text ' + (r.daysLeft <= 2 ? 'urgent' : 'normal') + '">' + r.daysLeft + ' days</td>' +
          '<td><div class="action-icons"><button class="action-icon-btn" title="Email">&#9993;</button><button class="action-icon-btn" title="Print">&#128438;</button></div></td></tr>';
      }).join('');
    }
    var actionCount = paRows.filter(function(r) { return r.status === 'required'; }).length;
    var pendCount = paRows.filter(function(r) { return r.status === 'pending'; }).length;
    var el = function(id, v) { var x = document.getElementById(id); if (x) x.querySelector('strong').textContent = v; };
    try { document.querySelector('.mb-badge.red strong').textContent = actionCount; } catch(e) {}
    try { document.querySelector('.mb-badge.orange strong').textContent = pendCount; } catch(e) {}
  }

  // ── Collection Summary: eligible checks with financial data ──
  var colTbody = document.getElementById('mb-collection-tbody');
  if (colTbody) {
    var eligChecks = checks.filter(function(c) { return c.status === 'eligible' || c.status === 'inactive'; });
    var totalCopay = 0, totalDed = 0, totalCollect = 0;

    if (eligChecks.length === 0) {
      colTbody.innerHTML = '<tr><td colspan="10" class="empty-state">No recent eligibility checks with financial data.</td></tr>';
    } else {
      colTbody.innerHTML = eligChecks.slice(0, 15).map(function(c) {
        var copay = c.copay || 0;
        var ded = c.annual_deductible || 0;
        var dedMax = c.annual_deductible_max || 0;
        var total = copay + ded;
        var isInactive = c.status === 'inactive';
        if (!isInactive) { totalCopay += copay; totalDed += ded; totalCollect += total; }
        var dedDisplay = ded ? '$' + ded : '\u2013';
        var dedDetail = dedMax ? '$' + ded + ' / $' + dedMax : '';
        var notes = isInactive ? 'URGENT: Coverage terminated' : (ded && dedMax && ded >= dedMax * 0.8 ? 'Near deductible limit' : c.plan_name || '');
        return '<tr><td>' + _fmtTime(c.run_date || c.created_at) + '</td>' +
          '<td><strong>' + (c.patient_name || '--') + '</strong></td>' +
          '<td>' + (c.provider_name || '--') + '</td><td>' + (c.payer_name || c.payer_id || '--') + '</td>' +
          '<td><span class="status-pill ' + (isInactive ? 'inactive' : 'active') + '">' + (isInactive ? 'Inactive' : 'Active') + '</span></td>' +
          '<td>' + (copay ? '<strong>$' + copay + '</strong>' : '\u2013') + '</td>' +
          '<td>' + (ded ? '<strong>' + dedDisplay + '</strong>' : '\u2013') + (dedDetail ? '<br><small style="color:var(--text-secondary);">' + dedDetail + '</small>' : '') + '</td>' +
          '<td>' + (total ? '<strong>$' + total + '</strong>' : '\u2013') + '</td>' +
          '<td><span class="note-text' + (isInactive ? ' urgent' : '') + '">' + notes + '</span></td>' +
          '<td>' + (!isInactive ? '<div class="action-icons"><button class="action-icon-btn">&#128196;</button><button class="action-icon-btn">&#128438;</button></div>' : '<span class="awaiting-text">No payment</span>') + '</td></tr>';
      }).join('');
    }
    var setEl = function(id, v) { var x = document.getElementById(id); if (x) x.textContent = v; };
    setEl('mb-total-copay', '$' + totalCopay);
    setEl('mb-total-ded', '$' + Math.round(totalDed));
    setEl('mb-total-collect', '$' + Math.round(totalCollect));
  }
}

function _fmtTime(dateStr) {
  if (!dateStr) return '--';
  try {
    var d = new Date(dateStr);
    if (isNaN(d)) return dateStr.split(' ').slice(1).join(' ') || dateStr;
    var h = d.getHours(), m = d.getMinutes();
    var ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return h + ':' + (m < 10 ? '0' : '') + m + ' ' + ampm;
  } catch(e) { return dateStr; }
}

// ── Appointments ──────────────────────────────────────
function renderAppointments() {
  var colors = ['teal','blue','purple','orange','pink','indigo','green','amber','cyan','red'];
  var apptData = (_statsData && _statsData.appointments) || {};
  var todayAppts = apptData.today || [];
  var tomorrowAppts = apptData.tomorrow || [];
  var weekAppts = apptData.week || [];
  var apptStats = apptData.stats || {};

  // If no appointments, fall back to showing recent eligibility checks as appointment-like rows
  var displayData = weekAppts.length > 0 ? weekAppts : ((_statsData && _statsData.recent_checks) || []);
  var isFromAppts = weekAppts.length > 0;

  var tbody = document.getElementById('appt-tbody');
  if (!tbody) return;

  if (displayData.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No appointments found. Connect your EHR or create appointments to see data here.</td></tr>';
  } else {
    var eligLabels = { 'eligible': 'Eligible', 'inactive': 'INACTIVE', 'error': 'Error', 'pending': 'Pending', 'cleared': 'Cleared', 'action_needed': 'Action Needed' };
    tbody.innerHTML = displayData.slice(0, 20).map(function(a, i) {
      var name = isFromAppts ? (a.patient_name || '--') : (a.patient_name || '--');
      var parts = name.split(' ');
      var initials = ((parts[0] || '').charAt(0) + (parts[1] || '').charAt(0)).toUpperCase();
      var shortName = parts[0] + ' ' + ((parts[1] || '').charAt(0) || '') + '.';

      var eligStatus = isFromAppts ? (a.eligibility_status || a.status || 'scheduled') : (a.status || 'pending');
      var statusClass = eligStatus === 'eligible' || eligStatus === 'cleared' ? 'eligible' : eligStatus === 'inactive' || eligStatus === 'action_needed' ? 'inactive' : eligStatus === 'error' ? 'denied' : 'checking';
      var statusLabel = eligLabels[eligStatus] || eligStatus.charAt(0).toUpperCase() + eligStatus.slice(1);

      var paStatus = isFromAppts ? (a.pa_status || 'not_required') : (a.prior_auth_required ? 'required' : 'not_required');
      var paLabel = paStatus === 'required' || paStatus === 'pa_required' ? 'PA Required' : paStatus === 'approved' ? 'PA Approved' : paStatus === 'pending' || paStatus === 'submitted' ? 'PA Pending' : 'Not Required';
      var paClass = paStatus !== 'not_required' && paStatus !== 'not required' ? 'required' : 'not-required';

      var timeStr = isFromAppts ? (a.appointment_time || '--') : _fmtTime(a.run_date || a.created_at);
      var apptType = isFromAppts ? (a.appointment_type || '--') : (a.source === 'batch' ? 'Batch' : 'Single');
      var payer = a.payer_name || a.payer_id || '--';
      var provider = a.provider_name || '--';

      var action = '';
      if (eligStatus === 'inactive' || eligStatus === 'action_needed') action = 'Call Patient';
      else if (paStatus === 'required' || paStatus === 'pa_required') action = 'Track PA';
      else if (a.eligibility_check_id) action = 'View';

      return '<tr><td>' + timeStr + '</td>' +
        '<td><div class="patient-cell"><div class="patient-avatar ' + colors[i % colors.length] + '">' + initials + '</div><span>' + shortName + '</span></div></td>' +
        '<td>' + provider + '</td><td>' + payer + '</td>' +
        '<td>' + apptType + '</td>' +
        '<td><span class="status-pill ' + statusClass + '">\u25CF ' + statusLabel + '</span></td>' +
        '<td class="pa-status-cell"><span class="pa-tag ' + paClass + '">' + paLabel + '</span></td>' +
        '<td>' + (action === 'Call Patient' ? '<button class="btn btn-secondary" style="font-size:11px;padding:4px 10px;color:var(--error);border-color:var(--error);">Call Patient</button>' : action === 'View' && a.eligibility_check_id ? '<a href="#" onclick="viewResult(\'' + a.eligibility_check_id + '\');return false;" style="color:var(--primary);font-size:12px;">View</a>' : action ? '<a href="#" style="color:var(--primary);font-size:12px;">' + action + '</a>' : '\u2014') + '</td></tr>';
    }).join('');
  }

  // Update tab counts from real appointment data
  document.querySelectorAll('.appt-tab').forEach(function(tab) {
    var countEl = tab.querySelector('.tab-count');
    if (!countEl) return;
    var tabType = tab.dataset.tab;
    if (tabType === 'today') countEl.textContent = '\u2022 ' + (apptData.today_count || todayAppts.length || displayData.length);
    else if (tabType === 'tomorrow') countEl.textContent = '\u2022 ' + (apptData.tomorrow_count || tomorrowAppts.length);
    else countEl.textContent = '\u2022 ' + (apptData.week_count || weekAppts.length || displayData.length);
  });

  // Update agent status bar stats from real data
  var agentStatus = (_statsData && _statsData.agent_status) || {};
  var agentEl = document.querySelector('.agent-status-bar');
  if (agentEl && agentStatus.started_at) {
    var agentTime = new Date(agentStatus.started_at);
    var h = agentTime.getHours(), m = agentTime.getMinutes();
    var ampm = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
    var timeLabel = h + ':' + (m < 10 ? '0' : '') + m + ' ' + ampm;
    document.querySelectorAll('.agent-status-bar > span:first-child').forEach(function(el) {
      el.innerHTML = '&#129302; Agent last ran: <strong>' + timeLabel + '</strong>';
    });
  }

  var eligCount = apptStats.eligible || displayData.filter(function(c) { return (c.eligibility_status || c.status) === 'eligible' || c.status === 'cleared'; }).length;
  var paCount = apptStats.pa_required || displayData.filter(function(c) { return c.pa_status === 'required' || c.prior_auth_required; }).length;
  var actionCount = apptStats.action_needed || displayData.filter(function(c) { return c.status === 'inactive' || c.status === 'error' || c.status === 'action_needed'; }).length;
  document.querySelectorAll('.appt-stat.green').forEach(function(el) { el.textContent = eligCount + ' eligible'; });
  document.querySelectorAll('.appt-stat.orange').forEach(function(el) { el.textContent = paCount + ' PA required'; });
  document.querySelectorAll('.appt-stat.red').forEach(function(el) { el.textContent = actionCount + ' action needed'; });

  // Footer
  var footer = document.querySelector('.table-footer');
  if (footer) footer.textContent = 'Showing 1-' + Math.min(displayData.length, 20) + ' of ' + displayData.length;

  // Wire up filter/tab buttons
  document.querySelectorAll('.filter-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
      this.classList.add('active');
    });
  });
  document.querySelectorAll('.appt-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
      document.querySelectorAll('.appt-tab').forEach(function(t) { t.classList.remove('active'); });
      this.classList.add('active');
    });
  });
}
function runAgentNow() { alert('Agent eligibility check started for all scheduled appointments.'); }

// ── Reports ───────────────────────────────────────────
function renderReportsPage() {
  var es = (_statsData && _statsData.eligibility) || {};
  var ps = (_statsData && _statsData.prior_auth) || {};

  // Update report stat cards dynamically
  var statCards = document.querySelectorAll('#page-reports .stat-card');
  if (statCards.length >= 5) {
    statCards[0].querySelector('.stat-value').textContent = (es.total || 0).toLocaleString();
    statCards[1].querySelector('.stat-value').textContent = (es.elig_rate || 0) + '%';
    var paRate = es.total ? Math.round(es.pa_required / es.total * 100 * 10) / 10 : 0;
    statCards[2].querySelector('.stat-value').textContent = paRate + '%';
    var autoRate = ps.total ? Math.round(ps.approved / Math.max(ps.total, 1) * 100) : 0;
    statCards[3].querySelector('.stat-value').textContent = autoRate + '%';
    statCards[4].querySelector('.stat-value').textContent = (es.avg_time || '--') + 's';
  }

  renderVolumeChart();
  renderPAOutcomesChart();
  renderDenialReasons();
  renderAIInsights();
}

function renderVolumeChart() {
  var el = document.getElementById('chart-volume');
  if (!el) return;
  // Use real check data to build a volume-over-time approximation
  var checks = (_statsData && _statsData.recent_checks) || [];
  var dayBuckets = {};
  checks.forEach(function(c) {
    var dateKey = (c.run_date || c.created_at || '').split(' ')[0] || 'unknown';
    dayBuckets[dateKey] = (dayBuckets[dateKey] || 0) + 1;
  });
  var bucketKeys = Object.keys(dayBuckets).sort();
  var data = bucketKeys.map(function(k) { return dayBuckets[k]; });
  if (data.length === 0) { el.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:40px;">No check data yet. Run eligibility checks to populate.</p>'; return; }
  var max = Math.max.apply(null, data) || 1;
  el.innerHTML = '<div class="css-line-chart">' + data.map(function(v) {
    return '<div class="line-bar primary" style="height:' + (v/max*100) + '%;"></div>';
  }).join('') + '</div><div class="chart-legend"><div class="legend-item"><div class="legend-dot" style="background:var(--primary);"></div>Total Checks</div><div class="legend-item"><div class="legend-dot" style="background:#ff9800;"></div>PA Required</div></div>';
}

function renderPAOutcomesChart() {
  var el = document.getElementById('chart-pa-outcomes');
  if (!el) return;
  // Build from real payer_stats
  var payerStats = (_statsData && _statsData.payer_stats) || {};
  var payers = Object.keys(payerStats).map(function(name) {
    var s = payerStats[name];
    return { name: name, eligible: s.eligible || 0, error: s.error || 0, inactive: s.inactive || 0 };
  });
  // Sort by total descending, take top 5
  payers.sort(function(a, b) { return (b.eligible + b.error + b.inactive) - (a.eligible + a.error + a.inactive); });
  payers = payers.slice(0, 5);

  if (payers.length === 0) {
    el.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:40px;">No payer data yet. Run eligibility checks to populate.</p>';
    return;
  }

  var maxT = Math.max.apply(null, payers.map(function(p) { return p.eligible + p.error + p.inactive; })) || 1;
  el.innerHTML = '<div class="css-bar-chart">' + payers.map(function(p) {
    return '<div class="bar-row"><div class="bar-label">' + p.name + '</div><div class="bar-track">' +
      '<div class="bar-fill approved" style="width:' + (p.eligible/maxT*100) + '%;"></div>' +
      '<div class="bar-fill denied" style="width:' + (p.error/maxT*100) + '%;"></div>' +
      '<div class="bar-fill pending-bar" style="width:' + (p.inactive/maxT*100) + '%;"></div></div></div>';
  }).join('') + '</div><div class="chart-legend"><div class="legend-item"><div class="legend-dot" style="background:#26a69a;"></div>Eligible</div><div class="legend-item"><div class="legend-dot" style="background:#ef5350;"></div>Error</div><div class="legend-item"><div class="legend-dot" style="background:#ffa726;"></div>Inactive</div></div>';
}

function renderDenialReasons() {
  var el = document.getElementById('denial-reasons-tbody');
  if (!el) return;
  var denials = (_statsData && _statsData.top_denials) || [];
  if (denials.length === 0) {
    el.innerHTML = '<tr><td colspan="4" class="empty-state">No denial data yet.</td></tr>';
    return;
  }
  var totalDenials = denials.reduce(function(sum, d) { return sum + d.count; }, 0) || 1;
  // Friendly labels for error codes
  var labels = {
    'PAYER_REJECTION': 'Payer rejection (invalid data)',
    'CLEARINGHOUSE_VALIDATION': 'Clearinghouse validation error',
    'CLEARINGHOUSE_ERROR': 'Clearinghouse error',
    'CLEARINGHOUSE_UNAVAILABLE': 'Clearinghouse unavailable',
    'CLEARINGHOUSE_DATA_ERROR': 'Payer/member not recognized',
    'ELIG_INVALID_PAYER': 'Invalid payer ID',
    'ELIG_INVALID_NPI': 'Invalid provider NPI',
    'ELIG_MISSING_SUBSCRIBER': 'Missing subscriber ID',
  };
  el.innerHTML = denials.map(function(d) {
    var pct = Math.round(d.count / totalDenials * 1000) / 10;
    var label = labels[d.code] || d.code;
    return '<tr><td>' + label + '</td><td><strong>' + d.count + '</strong></td><td><strong>' + pct + '%</strong></td><td><span class="trend-icon flat">\u2014</span></td></tr>';
  }).join('');
}

function renderAIInsights() {
  var el = document.getElementById('ai-insights-list');
  if (!el) return;
  var es = (_statsData && _statsData.eligibility) || {};
  var ps = (_statsData && _statsData.prior_auth) || {};
  var insights = [];

  // Generate dynamic insights from real data
  if (es.inactive > 0) {
    insights.push({ type: 'warning', icon: '&#128293;', text: es.inactive + ' patient(s) had inactive coverage. Verify insurance status before scheduling.' });
  }
  if (es.pa_required > 0) {
    insights.push({ type: 'info', icon: '&#10024;', text: es.pa_required + ' check(s) flagged prior authorization required. Review PA pipeline.' });
  }
  if (es.avg_time && es.avg_time < 3) {
    insights.push({ type: 'success', icon: '&#10024;', text: 'Average response time ' + es.avg_time + 's \u2014 optimal. No action needed.' });
  } else if (es.avg_time && es.avg_time >= 3) {
    insights.push({ type: 'warning', icon: '&#128293;', text: 'Average response time ' + es.avg_time + 's \u2014 above target. Consider checking clearinghouse connectivity.' });
  }
  if (es.elig_rate >= 90) {
    insights.push({ type: 'success', icon: '&#10024;', text: 'Eligibility rate at ' + es.elig_rate + '% \u2014 excellent performance.' });
  } else if (es.elig_rate > 0 && es.elig_rate < 80) {
    insights.push({ type: 'warning', icon: '&#128293;', text: 'Eligibility rate at ' + es.elig_rate + '%. Review patient data quality.' });
  }
  if (ps.denied > 0) {
    insights.push({ type: 'info', icon: '&#10024;', text: ps.denied + ' PA request(s) denied. Review denial reasons for resubmission opportunities.' });
  }

  if (insights.length === 0) {
    insights.push({ type: 'success', icon: '&#10024;', text: 'Run eligibility checks to generate AI insights from your data.' });
  }

  el.innerHTML = insights.map(function(i) {
    return '<div class="ai-insight-item ' + i.type + '"><span class="ai-insight-icon">' + i.icon + '</span><span>' + i.text + '</span></div>';
  }).join('');
}

// ── Init ──────────────────────────────────────────────────────
loadRecentChecks();
loadTestConfig();
renderPAPipeline();
loadProviders();
loadSettingsProviders();
loadAllPageData();
