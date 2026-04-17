/* ===================================================
   ExpensePro — Global JavaScript
   Features: Sidebar, Theme Toggle, Modals,
             File Upload, CSRF, Toast, etc.
   =================================================== */
'use strict';

/* ════════════════════════════════════════
   THEME TOGGLE  (light ↔ dark)
════════════════════════════════════════ */
(function initTheme() {
  // Read saved preference, default = light
  const saved = localStorage.getItem('epTheme') || 'light';
  if (saved === 'dark') {
    document.documentElement.classList.add('dark-mode');
  }
})();

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.classList.toggle('dark-mode');
  localStorage.setItem('epTheme', isDark ? 'dark' : 'light');

  // Update all toggle button labels
  document.querySelectorAll('.toggle-label').forEach(el => {
    el.textContent = isDark ? 'Light' : 'Dark';
  });
  document.querySelectorAll('.toggle-icon').forEach(el => {
    el.className = `toggle-icon fa-solid ${isDark ? 'fa-sun' : 'fa-moon'}`;
  });
}

// Wire up all theme toggle buttons after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const isDark = document.documentElement.classList.contains('dark-mode');
  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.addEventListener('click', toggleTheme);
    // Sync icons
    const icon  = btn.querySelector('.toggle-icon');
    const label = btn.querySelector('.toggle-label');
    if (icon)  icon.className  = `toggle-icon fa-solid ${isDark ? 'fa-sun' : 'fa-moon'}`;
    if (label) label.textContent = isDark ? 'Light' : 'Dark';
  });

  console.log('%cExpensePro loaded ✓', 'color:#6d28d9;font-weight:bold;font-size:14px;');
});

/* ════════════════════════════════════════
   SIDEBAR TOGGLE
════════════════════════════════════════ */
const sidebar       = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');

if (sidebar && sidebarToggle) {
  sidebarToggle.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      sidebar.classList.toggle('mobile-open');
    } else {
      const collapsed = sidebar.classList.toggle('collapsed');
      localStorage.setItem('epSidebarCollapsed', collapsed);
    }
  });

  // Restore saved sidebar state
  if (localStorage.getItem('epSidebarCollapsed') === 'true' && window.innerWidth > 768) {
    sidebar.classList.add('collapsed');
  }
}

/* Close mobile sidebar on outside click */
document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768
      && sidebar
      && sidebar.classList.contains('mobile-open')
      && !sidebar.contains(e.target)
      && e.target !== sidebarToggle) {
    sidebar.classList.remove('mobile-open');
  }
});

/* ════════════════════════════════════════
   TOAST — Auto dismiss
════════════════════════════════════════ */
document.querySelectorAll('.toast').forEach(toast => {
  setTimeout(() => {
    toast.style.transition = 'opacity 0.4s ease';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 400);
  }, 4500);
});

/* ════════════════════════════════════════
   MODAL UTILITIES
════════════════════════════════════════ */
function openModal(id) {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(() => overlay.querySelector('input,textarea,select')?.focus(), 150);
}

function closeModal(id) {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(o => closeModal(o.id));
  }
});

/* ════════════════════════════════════════
   FILE UPLOAD — Drag & Drop
════════════════════════════════════════ */
document.querySelectorAll('.file-upload-zone').forEach(zone => {
  const input = zone.querySelector('input[type="file"]');
  const label = zone.querySelector('p');

  zone.addEventListener('click', () => input?.click());

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('dragover');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (input && e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      if (label) label.textContent = e.dataTransfer.files[0].name;
    }
  });

  input?.addEventListener('change', () => {
    if (input.files.length && label) label.textContent = input.files[0].name;
  });
});

/* ════════════════════════════════════════
   HELPERS
════════════════════════════════════════ */

/** Get Django CSRF token */
function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1]
    || '';
}

/** Generic fetch wrapper */
async function apiRequest(url, method = 'GET', data = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
  };
  if (data && method !== 'GET') opts.body = JSON.stringify(data);
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Format currency */
function formatCurrency(amount, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount);
}

/** Format date */
function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

/* ════════════════════════════════════════
   ACTIVE NAV HIGHLIGHT
════════════════════════════════════════ */
(function markActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (!href) return;
    if (href === path || (path !== '/' && href !== '/' && path.startsWith(href))) {
      link.classList.add('active');
    }
  });
})();
