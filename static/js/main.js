/* =====================================================
   BloodNeed – Main JavaScript
   ===================================================== */

// ---- Flash Message Auto-dismiss ----------------------
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    // Click to dismiss
    const closeBtn = flash.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => dismissFlash(flash));
    }
    flash.addEventListener('click', () => dismissFlash(flash));
    // Auto dismiss after 5s
    setTimeout(() => dismissFlash(flash), 5000);
  });
});

function dismissFlash(el) {
  el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  el.style.opacity = '0';
  el.style.transform = 'translateX(100%)';
  setTimeout(() => el.remove(), 300);
}

// ---- Navbar Scroll Shadow ----------------------------
window.addEventListener('scroll', () => {
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    navbar.classList.toggle('scrolled', window.scrollY > 4);
  }
});

// ---- Mobile Nav Toggle ------------------------------
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      const isOpen = navLinks.classList.contains('open');
      toggle.setAttribute('aria-expanded', isOpen);
    });
    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!toggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('open');
      }
    });
  }
});

// ---- Password Visibility Toggle ---------------------
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.password-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      if (!input) return;
      const isText = input.type === 'text';
      input.type = isText ? 'password' : 'text';
      btn.textContent = isText ? '👁️' : '🙈';
    });
  });
});

// ---- Password Strength Meter -----------------------
document.addEventListener('DOMContentLoaded', () => {
  const passInput = document.getElementById('password');
  const strengthFill = document.querySelector('.strength-fill');
  const strengthText = document.querySelector('.strength-text');
  if (!passInput || !strengthFill) return;

  passInput.addEventListener('input', () => {
    const val = passInput.value;
    let score = 0;
    if (val.length >= 8)                          score++;
    if (/[A-Z]/.test(val))                        score++;
    if (/[a-z]/.test(val))                        score++;
    if (/\d/.test(val))                           score++;
    if (/[!@#$%^&*(),.?":{}|<>_\-]/.test(val))   score++;

    const pct   = (score / 5) * 100;
    const colors = ['#E74C3C', '#E67E22', '#F1C40F', '#27AE60', '#1ABC9C'];
    const labels = ['Very Weak', 'Weak', 'Fair', 'Strong', 'Very Strong'];
    strengthFill.style.width      = pct + '%';
    strengthFill.style.background = colors[score - 1] || '#E74C3C';
    if (strengthText) {
      strengthText.textContent   = score > 0 ? labels[score - 1] : '';
      strengthText.style.color   = colors[score - 1] || '#E74C3C';
    }
  });
});

// ---- Blood Group Pill Selector ----------------------
(function bloodSelector() {
  const COMPATIBLE = {
    'A+':  ['A+','A-','O+','O-'],
    'A-':  ['A-','O-'],
    'B+':  ['B+','B-','O+','O-'],
    'B-':  ['B-','O-'],
    'O+':  ['O+','O-'],
    'O-':  ['O-'],
    'AB+': ['A+','A-','B+','B-','O+','O-','AB+','AB-'],
    'AB-': ['A-','B-','O-','AB-'],
  };

  const patientSelect = document.getElementById('patientBloodGroup');
  const pills         = document.querySelectorAll('.blood-pill');
  const hiddenInput   = document.getElementById('selectedGroupsInput');
  const confirmBtn    = document.getElementById('confirmBloodBtn');
  const selectedLabel = document.getElementById('selectedBloodLabel');

  if (!pills.length) return;

  // Auto-select compatible groups when patient BG changes
  if (patientSelect) {
    patientSelect.addEventListener('change', () => {
      const bg   = patientSelect.value;
      const comp = COMPATIBLE[bg] || [];
      pills.forEach(pill => {
        const g = pill.dataset.group;
        pill.classList.remove('selected', 'disabled');
        if (!bg) return;
        if (comp.includes(g)) {
          pill.classList.add('selected');
        } else {
          pill.classList.add('disabled');
        }
      });
      updateLabel();
    });
  }

  // Manual toggle
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      if (pill.classList.contains('disabled')) return;
      pill.classList.toggle('selected');
      updateLabel();
    });
  });

  function updateLabel() {
    const selected = [...pills].filter(p => p.classList.contains('selected'))
                                .map(p => p.dataset.group);
    if (selectedLabel) {
      selectedLabel.textContent = selected.length
        ? 'Searching for: ' + selected.join(', ')
        : 'No blood group selected';
    }
    if (hiddenInput) hiddenInput.value = selected.join(',');
  }

  // Confirm button
  if (confirmBtn) {
    confirmBtn.addEventListener('click', (e) => {
      const form    = document.getElementById('bloodGroupForm');
      const selected = [...pills].filter(p => p.classList.contains('selected'));
      if (!selected.length) {
        e.preventDefault();
        showToast('Please select at least one blood group.', 'warning');
        return;
      }
      if (hiddenInput) {
        hiddenInput.value = selected.map(p => p.dataset.group).join(',');
      }
      if (form) form.submit();
    });
  }
})();

// ---- BMI Gauge Pointer ------------------------------
document.addEventListener('DOMContentLoaded', () => {
  const bmiVal = document.getElementById('bmiPointerValue');
  const pointer = document.getElementById('bmiPointer');
  if (!bmiVal || !pointer) return;
  const bmi = parseFloat(bmiVal.dataset.value || 0);
  // Scale: 10 = 0%, 40 = 100%
  let pct = Math.min(Math.max(((bmi - 10) / 30) * 100, 0), 100);
  pointer.style.left = pct + '%';
});

// ---- Availability Toggle (AJAX) --------------------
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('availabilityToggle');
  if (!toggle) return;
  toggle.addEventListener('change', async () => {
    try {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
      const res = await fetch('/profile/toggle-availability', {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':  csrfToken,
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.success) {
        const label = document.getElementById('availabilityLabel');
        if (label) label.textContent = data.status_text;
        showToast(
          data.is_available ? '✅ You are now available for donation!' : '❌ Marked as unavailable.',
          data.is_available ? 'success' : 'info'
        );
      }
    } catch (err) {
      console.error('Toggle failed:', err);
      toggle.checked = !toggle.checked; // revert
    }
  });
});

// ---- Confirm Dialogs --------------------------------
function confirmAction(message, formId) {
  if (confirm(message)) {
    document.getElementById(formId)?.submit();
  }
}

// ---- Toast Notification ----------------------------
function showToast(message, type = 'info') {
  const icons = { success: '✅', danger: '❌', warning: '⚠️', info: 'ℹ️' };
  const container = document.querySelector('.flash-container') || (() => {
    const c = document.createElement('div');
    c.className = 'flash-container';
    document.body.appendChild(c);
    return c;
  })();
  const el = document.createElement('div');
  el.className = `flash flash-${type}`;
  el.innerHTML = `
    <span class="flash-icon">${icons[type] || 'ℹ️'}</span>
    <span class="flash-text">${message}</span>
    <span class="flash-close" onclick="this.parentElement.remove()">×</span>
  `;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(100%)';
    el.style.transition = '0.3s ease';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}

// ---- Form Submission Loading State -----------------
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('button[type="submit"]');
      if (btn && !btn.disabled) {
        btn.disabled = true;
        const original = btn.innerHTML;
        btn.innerHTML = '<span class="spinner"></span> Processing...';
        setTimeout(() => {
          btn.disabled = false;
          btn.innerHTML = original;
        }, 8000);
      }
    });
  });
});

// ---- Smooth Scroll ----------------------------------
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// ---- Admin: Toggle User Active ----------------------
async function toggleUser(userId, csrfToken) {
  if (!confirm('Are you sure you want to toggle this user\'s active status?')) return;
  try {
    const res = await fetch(`/admin/toggle-user/${userId}`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken }
    });
    if (res.ok) location.reload();
  } catch (e) {
    showToast('Action failed. Please try again.', 'danger');
  }
}
