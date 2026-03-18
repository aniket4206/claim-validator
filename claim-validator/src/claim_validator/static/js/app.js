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

// Close dropdown on Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeUserMenu();
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

  // Refresh dashboard data when navigating to it
  if (pageName === 'dashboard') {
    loadRecentChecks();
    renderPAPipeline();
  }

  window.scrollTo(0, 0);
}

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

  // Update dashboard stats
  const totalEl = document.getElementById('stat-total-checks');
  const eligibleEl = document.getElementById('stat-eligible');
  const sidebarChecks = document.getElementById('sidebar-checks-count');
  if (totalEl) totalEl.textContent = checks.length.toLocaleString();
  if (eligibleEl) eligibleEl.textContent = checks.filter(c => c.status === 'eligible').length.toLocaleString();
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
    const source = c.source || 'single';
    const sourceBadge = source === 'batch'
      ? '<span class="badge badge-batch">Batch</span>'
      : '<span class="badge badge-single">Single</span>';
    return `
    <tr style="cursor:pointer;" onclick="viewResult('${c.check_id}')">
      <td><strong>${c.patient_name}</strong></td>
      <td>${c.payer_name}</td>
      <td>${sourceBadge}</td>
      <td>${statusBadge(c.status)}</td>
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
    service_type_code: serviceTypeCode,
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

  // Prior Auth
  const paEl = document.getElementById('r-prior-auth');
  const btnPA = document.getElementById('btn-proceed-pa');
  if (r.prior_auth_required === true) {
    paEl.innerHTML = '<span class="badge badge-required">Required</span>';
    btnPA.style.display = 'inline-flex';
  } else if (r.prior_auth_required === false) {
    paEl.innerHTML = '<span class="badge badge-not-required">Not Required</span>';
    btnPA.style.display = 'none';
  } else {
    paEl.textContent = '--';
    btnPA.style.display = 'none';
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
  overlay.querySelector('.loading-sub').textContent = 'Contacting Waystar PA API (this may take 10-15 seconds)';
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
      service_type_code: document.getElementById('service_type_code').value || '30',
      eligibility_check_id: r.check_id || '',
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
}

function closePAModal() {
  document.getElementById('pa-modal').style.display = 'none';
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

// ── Dashboard PA Pipeline (mock data for now) ─────────────────
function renderPAPipeline() {
  const pendingData = [
    { name: 'Amanda Wilson', payer: 'BCBS', service: 'MRI Scan' },
    { name: 'James Lee', payer: 'Aetna', service: 'CT Scan' },
    { name: 'Lisa Brown', payer: 'Cigna', service: 'Surgery' },
  ];
  const submittedData = [
    { name: 'Mark Davis', payer: 'UHC', service: 'Physical Therapy' },
    { name: 'Sophia Garcia', payer: 'Humana', service: 'Specialist Visit' },
  ];
  const approvedData = [
    { name: 'Alex Thompson', payer: 'Medicare', service: 'Lab Tests' },
    { name: 'Maria Sanchez', payer: 'BCBS', service: 'Imaging' },
    { name: 'John Anderson', payer: 'Aetna', service: 'Surgery' },
  ];

  document.getElementById('pipe-pending-count').textContent = pendingData.length;
  document.getElementById('pipe-submitted-count').textContent = submittedData.length;
  document.getElementById('pipe-approved-count').textContent = approvedData.length;

  const renderCards = (data) => data.map(d => `
    <div class="pipeline-card">
      <div class="pipeline-card-name">${d.name}</div>
      <div class="pipeline-card-payer">${d.payer}</div>
      <div class="pipeline-card-service">${d.service}</div>
    </div>
  `).join('');

  document.getElementById('pipe-pending').innerHTML = renderCards(pendingData);
  document.getElementById('pipe-submitted').innerHTML = renderCards(submittedData);
  document.getElementById('pipe-approved').innerHTML = renderCards(approvedData);

  // Update dashboard stat
  const paEl = document.getElementById('stat-pa-submitted');
  if (paEl) paEl.textContent = (pendingData.length + submittedData.length + approvedData.length);

  const avgEl = document.getElementById('stat-avg-time');
  if (avgEl) avgEl.textContent = '2.3s';
  const sidebarAvg = document.getElementById('sidebar-avg-time');
  if (sidebarAvg) sidebarAvg.textContent = '1.8s';
  const sidebarRate = document.getElementById('sidebar-elig-rate');
  if (sidebarRate) sidebarRate.textContent = '92.4%';
}

// ── Init ──────────────────────────────────────────────────────
loadRecentChecks();
loadTestConfig();
renderPAPipeline();
