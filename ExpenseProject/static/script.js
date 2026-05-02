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
  const saved = localStorage.getItem('epTheme') || 'light';
  if (saved === 'dark') document.documentElement.classList.add('dark-mode');
})();

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark-mode');
  localStorage.setItem('epTheme', isDark ? 'dark' : 'light');
  document.querySelectorAll('.toggle-icon').forEach(el => {
    el.className = `toggle-icon fa-solid ${isDark ? 'fa-sun' : 'fa-moon'}`;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const isDark = document.documentElement.classList.contains('dark-mode');

  // Sync theme icons on load
  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.addEventListener('click', toggleTheme);
    const icon = btn.querySelector('.toggle-icon');
    if (icon) icon.className = `toggle-icon fa-solid ${isDark ? 'fa-sun' : 'fa-moon'}`;
  });

  console.log('%cExpensePro loaded ✓', 'color:#6d28d9;font-weight:bold;font-size:14px;');

  /* ════════════════════════════════════════
     NOTIFICATIONS
  ════════════════════════════════════════ */
  const notifBtn      = document.getElementById('notif-btn');
  const notifPanel    = document.getElementById('notif-panel');
  const notifBadge    = document.getElementById('notif-badge');
  const notifList     = document.getElementById('notif-list');
  const notifEmpty    = document.getElementById('notif-empty');
  const notifMarkAll  = document.getElementById('notif-mark-all');

  const KIND_ICONS = {
    submitted: { icon: 'fa-paper-plane',  color: '#3b82f6' },
    approved:  { icon: 'fa-circle-check', color: '#10b981' },
    rejected:  { icon: 'fa-circle-xmark', color: '#ef4444' },
  };

  async function fetchNotifications() {
    try {
      const res  = await fetch('/api/notifications/');
      const data = await res.json();

      // Update badge
      if (data.unread_count > 0) {
        notifBadge.textContent = data.unread_count > 9 ? '9+' : data.unread_count;
        notifBadge.classList.remove('hidden');
      } else {
        notifBadge.classList.add('hidden');
      }

      // Render list
      const items = data.notifications;
      // Remove existing rendered items (keep the empty placeholder)
      notifList.querySelectorAll('.notif-item').forEach(el => el.remove());

      if (items.length === 0) {
        notifEmpty.style.display = '';
      } else {
        notifEmpty.style.display = 'none';
        items.forEach(n => {
          const meta = KIND_ICONS[n.kind] || { icon: 'fa-bell', color: '#6d28d9' };
          const el   = document.createElement('a');
          el.className  = `notif-item${n.is_read ? ' read' : ''}`;
          el.href       = n.link || '#';
          el.dataset.id = n.id;
          el.innerHTML  = `
            <span class="notif-icon" style="color:${meta.color}">
              <i class="fa-solid ${meta.icon}"></i>
            </span>
            <span class="notif-content">
              <span class="notif-msg">${n.message}</span>
              <span class="notif-time">${n.created_at}</span>
            </span>
            ${!n.is_read ? '<span class="notif-dot"></span>' : ''}
          `;
          el.addEventListener('click', async (e) => {
            if (!n.is_read) {
              await fetch(`/api/notifications/${n.id}/read/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
              });
            }
            // Navigation handled by href
          });
          notifList.appendChild(el);
        });
      }
    } catch (err) {
      console.warn('Notifications fetch failed:', err);
    }
  }

  // Toggle notification panel
  if (notifBtn && notifPanel) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifPanel.classList.toggle('open');
      document.getElementById('profile-dropdown')?.classList.remove('open');
      if (notifPanel.classList.contains('open')) fetchNotifications();
    });
  }

  // Mark all read
  if (notifMarkAll) {
    notifMarkAll.addEventListener('click', async (e) => {
      e.stopPropagation();
      await fetch('/api/notifications/mark-all-read/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
      });
      fetchNotifications();
    });
  }

  // Poll every 60s for badge count
  fetchNotifications();
  setInterval(fetchNotifications, 60000);

  /* ════════════════════════════════════════
     PROFILE DROPDOWN
  ════════════════════════════════════════ */
  const avatarBtn       = document.getElementById('topbar-avatar-btn');
  const profileDropdown = document.getElementById('profile-dropdown');

  if (avatarBtn && profileDropdown) {
    avatarBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      profileDropdown.classList.toggle('open');
      notifPanel?.classList.remove('open');
    });
  }

  // Close both panels on outside click
  document.addEventListener('click', (e) => {
    if (notifPanel && !document.getElementById('notif-wrap')?.contains(e.target)) {
      notifPanel.classList.remove('open');
    }
    if (profileDropdown && !document.getElementById('topbar-profile-wrap')?.contains(e.target)) {
      profileDropdown.classList.remove('open');
    }
  });
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

  // Only trigger programmatic click if zone is NOT a <label>
  // (labels already open the file picker natively via their for/nested-input binding)
  if (zone.tagName !== 'LABEL') {
    zone.addEventListener('click', () => input?.click());
  }

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
