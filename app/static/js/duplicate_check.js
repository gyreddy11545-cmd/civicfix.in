/**
 * CIVICFIX — INTELLIGENT DUPLICATE DETECTION PROMPT
 * Real-time similarity check, non-intrusive preview, and options to Follow or Continue
 */

document.addEventListener('DOMContentLoaded', () => {
  initDuplicateChecker();
});

function initDuplicateChecker() {
  const titleInput = document.getElementById('input-title');
  const descInput = document.getElementById('input-description');
  const catInput = document.getElementById('input-category');
  const latInput = document.getElementById('input-latitude');
  const lonInput = document.getElementById('input-longitude');
  const container = document.getElementById('duplicate-alert-container');

  if (!titleInput || !container) return;

  let debounceTimer = null;

  function runCheck() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const title = titleInput.value.trim();
      const desc = descInput ? descInput.value.trim() : '';
      const cat = catInput ? catInput.value.trim() : '';
      const lat = latInput ? latInput.value.trim() : null;
      const lon = lonInput ? lonInput.value.trim() : null;

      if (title.length < 5 && !cat) {
        container.style.display = 'none';
        return;
      }

      fetch('/api/check-duplicates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: cat,
          title: title,
          description: desc,
          latitude: lat,
          longitude: lon
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.has_duplicates && data.candidates.length > 0) {
          const top = data.candidates[0];
          renderDuplicateNotice(top);
        } else {
          container.style.display = 'none';
        }
      })
      .catch(() => {});
    }, 600);
  }

  function renderDuplicateNotice(item) {
    const reasonsHtml = item.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('');
    container.innerHTML = `
      <div class="glass-card" style="border: 2px solid var(--accent-amber); background: rgba(251, 191, 36, 0.08); margin-bottom: 1.5rem;">
        <div style="display: flex; gap: 1rem; align-items: flex-start; flex-wrap: wrap;">
          ${item.image_path ? `<img src="${item.image_path}" style="width: 110px; height: 80px; object-fit: cover; border-radius: 8px; border: 1px solid var(--accent-amber);">` : ''}
          <div style="flex: 1; min-width: 240px;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 4px;">
              <span class="badge badge-high" style="font-size: 0.72rem;">${item.score}% SIMILARITY MATCH</span>
              <span class="badge badge-${item.status.toLowerCase().replace(' ', '-')}">${item.status}</span>
            </div>
            <h4 style="font-size: 0.95rem; margin-bottom: 4px; color: var(--text-main);">
              Possible Duplicate: ${escapeHtml(item.title)}
            </h4>
            <ul style="font-size: 0.78rem; color: var(--text-muted); margin: 0 0 0.75rem 1.25rem;">
              ${reasonsHtml}
            </ul>
            <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
              <a href="/issues/${item.issue_id}" target="_blank" class="btn btn-sm btn-outline-cyan">
                Inspect / Follow Existing Issue
              </a>
              <button type="button" class="btn btn-sm btn-secondary" onclick="document.getElementById('duplicate-alert-container').style.display='none'; document.getElementById('bypass_duplicate_input').value='1';">
                Different Problem, Continue Reporting
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
    container.style.display = 'block';
  }

  // Hook inputs
  titleInput.addEventListener('input', runCheck);
  if (descInput) descInput.addEventListener('input', runCheck);
  if (catInput) catInput.addEventListener('change', runCheck);

  // Expose global trigger for map marker move
  window.triggerDuplicateCheck = runCheck;
}
