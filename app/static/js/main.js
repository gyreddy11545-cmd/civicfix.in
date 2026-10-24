/**
 * CIVICFIX — MAIN JAVASCRIPT ENGINE
 * 1. Active Navigation Highlighting & Smooth Page Transitions
 * 2. Notification Centre with Circular Thumbnails & Unread Filters
 * 3. Floating CivicFix AI Assistant with Guided Intention Engine
 * 4. Theme & Alert Dismissal
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNavigationHighlighting();
  initNotificationsCenter();
  initAlertDismissal();
  initAIAssistant();
});

// ==========================================
// 1. NAVIGATION HIGHLIGHTING & SMOOTH TRANSITIONS
// ==========================================
function initNavigationHighlighting() {
  const currentPath = window.location.pathname.toLowerCase();

  // Helper to sync active state
  function syncActiveNav() {
    const navLinks = document.querySelectorAll('.nav-links .nav-link, .mobile-bottom-nav .bottom-nav-item');
    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (!href) return;
      const targetPath = href.toLowerCase();

      // Exact match or prefix match (e.g. /citizen/dashboard)
      const isHome = (currentPath === '/' && targetPath === '/');
      const isMatch = isHome || (targetPath !== '/' && (currentPath === targetPath || currentPath.startsWith(targetPath + '/')));

      if (isMatch) {
        link.classList.add('active');
      } else if (!isHome && targetPath === '/') {
        link.classList.remove('active');
      }
    });
  }

  syncActiveNav();

  // Support Back / Forward history transitions
  window.addEventListener('popstate', () => {
    syncActiveNav();
  });

  // Smooth page content entrance animation
  const pageWrapper = document.querySelector('.page-content-wrapper');
  if (pageWrapper && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    pageWrapper.classList.add('page-enter-active');
  }
}

// ==========================================
// 2. NOTIFICATIONS CENTRE (CIRCULAR THUMBNAILS)
// ==========================================
function initNotificationsCenter() {
  const notifBtn = document.getElementById('notif-bell-btn');
  const notifBadge = document.getElementById('notif-badge');
  const notifList = document.getElementById('notif-list-container');
  const notifSubtext = document.getElementById('notif-unread-subtext');
  const tabAll = document.getElementById('notif-tab-all');
  const tabUnread = document.getElementById('notif-tab-unread');
  const markAllBtn = document.getElementById('mark-all-read-btn');

  let activeFilter = 'all';

  if (!notifBtn) return;

  // Initial Unread Count Poll
  fetchUnreadCount();

  // Open modal on bell click
  notifBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    openModal('notif-modal');
    loadNotifications(activeFilter);
  });

  // Tab switching
  if (tabAll && tabUnread) {
    tabAll.addEventListener('click', () => {
      activeFilter = 'all';
      tabAll.classList.add('active');
      tabUnread.classList.remove('active');
      loadNotifications('all');
    });

    tabUnread.addEventListener('click', () => {
      activeFilter = 'unread';
      tabUnread.classList.add('active');
      tabAll.classList.remove('active');
      loadNotifications('unread');
    });
  }

  // Mark all as read button
  if (markAllBtn) {
    markAllBtn.addEventListener('click', () => {
      fetch('/api/notifications/mark-read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
        .then(res => res.json())
        .then(() => {
          if (notifBadge) notifBadge.style.display = 'none';
          if (notifSubtext) notifSubtext.textContent = '0 unread';
          loadNotifications(activeFilter);
        });
    });
  }

  function fetchUnreadCount() {
    fetch('/api/notifications?filter=unread')
      .then(res => res.json())
      .then(data => {
        if (data.unread_count > 0 && notifBadge) {
          notifBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
          notifBadge.style.display = 'flex';
          if (notifSubtext) notifSubtext.textContent = `${data.unread_count} unread`;
        } else if (notifBadge) {
          notifBadge.style.display = 'none';
          if (notifSubtext) notifSubtext.textContent = '0 unread';
        }
      })
      .catch(() => {});
  }

  function loadNotifications(filter) {
    if (!notifList) return;
    notifList.innerHTML = `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">Fetching notifications...</div>`;

    fetch(`/api/notifications?filter=${filter}`)
      .then(res => res.json())
      .then(data => {
        const items = data.notifications || [];
        if (notifBadge && data.unread_count !== undefined) {
          if (data.unread_count > 0) {
            notifBadge.textContent = data.unread_count;
            notifBadge.style.display = 'flex';
            if (notifSubtext) notifSubtext.textContent = `${data.unread_count} unread`;
          } else {
            notifBadge.style.display = 'none';
            if (notifSubtext) notifSubtext.textContent = '0 unread';
          }
        }

        if (items.length === 0) {
          notifList.innerHTML = `
            <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 0.5rem; opacity: 0.6;">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
              </svg>
              <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-main);">No notifications</div>
              <div style="font-size: 0.8rem; margin-top: 2px;">You're completely up to date with municipal updates.</div>
            </div>
          `;
          return;
        }

        notifList.innerHTML = items.map(n => {
          // Circular thumbnail or fallback category icon
          let thumbHtml = '';
          if (n.image_url) {
            thumbHtml = `<img src="${n.image_url}" alt="Issue Photo" class="notif-circle-img" onerror="this.src='/static/images/placeholder_issue.svg'">`;
          } else {
            thumbHtml = `<div class="notif-circle-fallback">${getCategoryGlyph(n.category)}</div>`;
          }

          const unreadClass = n.is_read ? 'notif-item-read' : 'notif-item-unread';

          return `
            <div class="notif-item ${unreadClass}">
              <div class="notif-thumb-col">
                ${thumbHtml}
                ${!n.is_read ? `<span class="notif-unread-dot"></span>` : ''}
              </div>
              <div class="notif-content-col">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 2px;">
                  <span class="notif-title">${escapeHtml(n.title)}</span>
                  <span class="notif-time">${n.created_at}</span>
                </div>
                <div class="notif-msg">${escapeHtml(n.message)}</div>
                <div style="display: flex; gap: 0.6rem; align-items: center; margin-top: 6px;">
                  ${n.issue_id ? `<a href="/issues/${n.issue_id}" class="btn btn-xs btn-outline-cyan">View Report ${n.issue_id}</a>` : ''}
                  ${!n.is_read ? `<button type="button" class="btn btn-xs btn-secondary" onclick="markSingleNotif(${n.id})">Mark read</button>` : ''}
                </div>
              </div>
            </div>
          `;
        }).join('');
      })
      .catch(() => {
        notifList.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--accent-coral);">Error loading notifications.</div>`;
      });
  }
}

// Global single notification read trigger
window.markSingleNotif = function(id) {
  fetch('/api/notifications/mark-read', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: id })
  })
    .then(res => res.json())
    .then(() => {
      // Re-trigger load
      const tabUnread = document.getElementById('notif-tab-unread');
      const activeFilter = (tabUnread && tabUnread.classList.contains('active')) ? 'unread' : 'all';
      const notifBell = document.getElementById('notif-bell-btn');
      if (notifBell) notifBell.click();
    });
};

// ==========================================
// 3. CIVICFIX AI ASSISTANT (FLOATING WIDGET)
// ==========================================
function initAIAssistant() {
  const launcherBtn = document.getElementById('ai-assistant-btn');
  const chatCard = document.getElementById('ai-assistant-card');
  const closeBtn = document.getElementById('ai-close-btn');
  const chatForm = document.getElementById('ai-chat-form');
  const userInput = document.getElementById('ai-user-input');
  const chatThread = document.getElementById('ai-chat-thread');
  const typingIndicator = document.getElementById('ai-typing-indicator');
  const chipsContainer = document.getElementById('ai-suggested-chips');

  if (!launcherBtn || !chatCard) return;

  // Toggle Assistant Card
  launcherBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isVisible = (chatCard.style.display !== 'none');
    if (isVisible) {
      chatCard.style.display = 'none';
      launcherBtn.classList.remove('open');
    } else {
      chatCard.style.display = 'flex';
      launcherBtn.classList.add('open');
      userInput?.focus();
      scrollThreadToBottom();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      chatCard.style.display = 'none';
      launcherBtn.classList.remove('open');
    });
  }

  // Handle Form Submission
  if (chatForm && userInput) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const message = userInput.value.trim();
      if (!message) return;

      appendUserBubble(message);
      userInput.value = '';
      sendAssistantQuery(message);
    });
  }

  // Handle Suggested Question Chips
  if (chipsContainer) {
    chipsContainer.addEventListener('click', (e) => {
      const chip = e.target.closest('.ai-chip-btn');
      if (!chip) return;
      const query = chip.getAttribute('data-query');
      if (query) {
        appendUserBubble(query);
        sendAssistantQuery(query);
      }
    });
  }

  function sendAssistantQuery(message) {
    if (typingIndicator) typingIndicator.style.display = 'flex';
    scrollThreadToBottom();

    const currentLang = localStorage.getItem('civicfix-lang') || 'en';

    fetch('/api/ai-assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message, lang: currentLang })
    })
      .then(res => res.json())
      .then(data => {
        if (typingIndicator) typingIndicator.style.display = 'none';
        appendBotBubble(data.reply, data.action_link);

        // Update suggested chips
        if (data.suggested_questions && chipsContainer) {
          chipsContainer.innerHTML = data.suggested_questions.map(q => `
            <button type="button" class="ai-chip-btn" data-query="${escapeHtml(q)}">${escapeHtml(q)}</button>
          `).join('');
        }
      })
      .catch(() => {
        if (typingIndicator) typingIndicator.style.display = 'none';
        appendBotBubble("I am temporarily unable to connect to the knowledge engine. Please check your internet connection or use the top navigation menu.", null);
      });
  }

  function appendUserBubble(text) {
    if (!chatThread) return;
    const bubble = document.createElement('div');
    bubble.className = 'ai-bubble-msg ai-bubble-user';
    bubble.innerHTML = `<div class="ai-bubble-content">${escapeHtml(text)}</div>`;
    chatThread.appendChild(bubble);
    scrollThreadToBottom();
  }

  function appendBotBubble(markdownText, actionLink) {
    if (!chatThread) return;
    const bubble = document.createElement('div');
    bubble.className = 'ai-bubble-msg ai-bubble-bot';

    let html = formatSimpleMarkdown(markdownText);
    if (actionLink) {
      html += `
        <div style="margin-top: 0.65rem;">
          <a href="${actionLink}" class="btn btn-xs btn-primary" style="text-decoration:none; display:inline-flex;">
            Open Page &rarr;
          </a>
        </div>
      `;
    }

    bubble.innerHTML = `<div class="ai-bubble-content">${html}</div>`;
    chatThread.appendChild(bubble);
    scrollThreadToBottom();
  }

  function scrollThreadToBottom() {
    if (chatThread) {
      chatThread.scrollTop = chatThread.scrollHeight;
    }
  }

  function formatSimpleMarkdown(txt) {
    if (!txt) return '';
    let out = escapeHtml(txt);
    // Bold
    out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Inline code
    out = out.replace(/`(.*?)`/g, '<code class="ai-inline-code">$1</code>');
    // Bullet points
    out = out.replace(/\n• (.*?)/g, '<br>&bull; $1');
    // Numbered lists
    out = out.replace(/\n(\d+)\. (.*?)/g, '<br><strong>$1.</strong> $2');
    // Paragraph newlines
    out = out.replace(/\n\n/g, '<br><br>');
    return out;
  }
}

// ==========================================
// 4. THEME & MODAL UTILITIES
// ==========================================
function initTheme() {
  const savedTheme = localStorage.getItem('civicfix-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', nextTheme);
      localStorage.setItem('civicfix-theme', nextTheme);
      updateThemeIcon(nextTheme);
    });
  }
}

function updateThemeIcon(theme) {
  const iconSpan = document.getElementById('theme-icon');
  if (!iconSpan) return;
  if (theme === 'light') {
    iconSpan.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
      </svg>
    `;
    iconSpan.setAttribute('title', 'Switch to Dark Mode');
  } else {
    iconSpan.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="5"></circle>
        <line x1="12" y1="1" x2="12" y2="3"></line>
        <line x1="12" y1="21" x2="12" y2="23"></line>
      </svg>
    `;
    iconSpan.setAttribute('title', 'Switch to Light Mode');
  }
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('open');
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
  }
}

function initAlertDismissal() {
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.alert')?.remove();
    });
  });
}

function getCategoryGlyph(cat) {
  const map = {
    'Pothole or damaged road': '🛣️',
    'Streetlight failure': '💡',
    'Overflowing garbage bin': '🗑️',
    'Drainage blockage': '🌊',
    'Water leakage': '💧',
    'Broken footpath': '🚶',
    'Damaged public property': '🏛️'
  };
  return map[cat] || '📋';
}

function escapeHtml(text) {
  if (!text) return '';
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.toString().replace(/[&<>"']/g, m => map[m]);
}
