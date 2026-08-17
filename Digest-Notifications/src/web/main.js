document.addEventListener('DOMContentLoaded', () => {
  // API Token State & UI Setup
  const apiTokenInput = document.getElementById('apiTokenInput');
  const urlParams = new URLSearchParams(window.location.search);
  const queryToken = urlParams.get('token');
  if (queryToken) {
    apiTokenInput.value = queryToken;
    sessionStorage.setItem('api_token', queryToken);
  } else {
    apiTokenInput.value = sessionStorage.getItem('api_token') || '';
  }

  apiTokenInput.addEventListener('input', () => {
    sessionStorage.setItem('api_token', apiTokenInput.value);
  });

  const getAuthHeaders = () => {
    const token = sessionStorage.getItem('api_token') || '';
    return { 'X-API-Token': token };
  };

  // Set default dates
  const todayStr = new Date().toISOString().split('T')[0];
  document.getElementById('refDate').value = todayStr;
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('date').value = tomorrow.toISOString().split('T')[0];
  document.getElementById('time').value = '10:00';

  // State
  let currentGeneratedDigest = null;
  let interviewsOffset = 0;
  const interviewsLimit = 5;
  let logsOffset = 0;
  const logsLimit = 5;

  // Selectors — Digest Generator
  const interviewForm    = document.getElementById('interviewForm');
  const timelineList     = document.getElementById('timelineList');
  const totalCountBadge  = document.getElementById('totalCount');
  const generateBtn      = document.getElementById('generateBtn');
  const digestType       = document.getElementById('digestType');
  const refDateInput     = document.getElementById('refDate');
  const previewEmpty     = document.getElementById('previewEmpty');
  const previewTypeBadge = document.getElementById('previewTypeBadge');
  const previewDateRange = document.getElementById('previewDateRange');
  const previewIframe    = document.getElementById('previewIframe');
  const sendBtn          = document.getElementById('sendBtn');
  const logsList         = document.getElementById('logsList');
  const batchSizeBadge   = document.getElementById('batchSizeBadge');
  const textPreviewBox   = document.getElementById('textPreviewBox');
  const txtDownloadBtn   = document.getElementById('txtDownloadBtn');

  // ── Load batch size config ────────────────────────────────────────────────
  fetch('/api/config')
    .then(r => r.json())
    .then(cfg => {
      if (batchSizeBadge) batchSizeBadge.textContent = `Batch limit: ${cfg.batch_size}`;
    });

  // ── Load and render interviews ────────────────────────────────────────────
  const loadInterviews = async () => {
    const res  = await fetch(`/api/interviews?limit=${interviewsLimit}&offset=${interviewsOffset}`);
    const data = await res.json();
    const list = data.interviews || [];
    const total = data.total || 0;

    totalCountBadge.textContent = total;
    timelineList.innerHTML = '';

    if (list.length === 0) {
      timelineList.innerHTML =
        '<div style="color:var(--text-muted);text-align:center;padding:20px;font-size:13px;">No interviews scheduled</div>';
      updateInterviewsPagination(total);
      return;
    }

    list.forEach(interview => {
      const item = document.createElement('div');
      item.className = 'timeline-item';
      const dateObj = new Date(interview.date);
      const formattedDate = dateObj.toLocaleDateString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric'
      });
      item.innerHTML = `
        <div class="timeline-content">
          <h4>${escapeHTML(interview.candidate_name)}</h4>
          <p>${escapeHTML(interview.role)}</p>
          <div class="timeline-meta">
            <span>🕒 ${interview.time}</span>
            <span>👤 ${escapeHTML(interview.interviewer_name)}</span>
            <span>📅 ${formattedDate}</span>
          </div>
        </div>
        <button class="btn-danger" data-id="${interview.id}">Delete</button>`;
      item.querySelector('.btn-danger').addEventListener('click', async e => {
        if (confirm('Delete this interview?')) await deleteInterview(e.target.dataset.id);
      });
      timelineList.appendChild(item);
    });

    updateInterviewsPagination(total);
  };

  const updateInterviewsPagination = (total) => {
    const totalPages = Math.max(1, Math.ceil(total / interviewsLimit));
    const currentPage = Math.floor(interviewsOffset / interviewsLimit) + 1;
    
    if (interviewsOffset >= total && total > 0) {
      interviewsOffset = Math.max(0, (totalPages - 1) * interviewsLimit);
      loadInterviews();
      return;
    }

    document.getElementById('interviewsPageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('interviewsPrevBtn').disabled = (interviewsOffset === 0);
    document.getElementById('interviewsNextBtn').disabled = (interviewsOffset + interviewsLimit >= total);
  };

  document.getElementById('interviewsPrevBtn').addEventListener('click', () => {
    if (interviewsOffset >= interviewsLimit) {
      interviewsOffset -= interviewsLimit;
      loadInterviews();
    }
  });

  document.getElementById('interviewsNextBtn').addEventListener('click', () => {
    interviewsOffset += interviewsLimit;
    loadInterviews();
  });

  // ── Add interview ─────────────────────────────────────────────────────────
  interviewForm.addEventListener('submit', async e => {
    e.preventDefault();
    const body = {
      candidate_name:   document.getElementById('candidateName').value,
      role:             document.getElementById('role').value,
      interviewer_name: document.getElementById('interviewerName').value,
      date:             document.getElementById('date').value,
      time:             document.getElementById('time').value,
    };
    const res = await fetch('/api/interviews', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(body),
    });
    if (res.status === 401) {
      alert('Authentication failed: Invalid or missing API Token');
      return;
    }
    if (res.ok) {
      interviewForm.reset();
      document.getElementById('date').value = tomorrow.toISOString().split('T')[0];
      document.getElementById('time').value = '10:00';
      interviewsOffset = 0;
      await loadInterviews();
    } else {
      alert('Failed to schedule interview');
    }
  });

  // ── Delete interview ──────────────────────────────────────────────────────
  const deleteInterview = async id => {
    const res = await fetch(`/api/interviews?id=${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (res.status === 401) {
      alert('Authentication failed: Invalid or missing API Token');
      return;
    }
    if (res.ok) await loadInterviews();
    else alert('Failed to delete interview');
  };

  // ── Generate Digest Preview ───────────────────────────────────────────────
  generateBtn.addEventListener('click', async () => {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span>⚡</span> Generating...';

    const res  = await fetch('/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ type: digestType.value, ref_date: refDateInput.value }),
    });
    if (res.status === 401) {
      alert('Authentication failed: Invalid or missing API Token');
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<span>⚡</span> Generate Preview';
      return;
    }
    const data = await res.json();

    generateBtn.disabled = false;
    generateBtn.innerHTML = '<span>⚡</span> Generate Preview';

    // ── Empty digest suppression UI ───────────────────────────────────────
    if (data.status === 'skipped') {
      previewEmpty.style.display  = 'flex';
      previewEmpty.querySelector('h3').textContent = 'No Interviews Found';
      previewEmpty.querySelector('p').textContent  =
        'There are no upcoming interviews for this period. Digest suppressed — nothing will be sent.';
      sendBtn.disabled  = true;
      sendBtn.className = 'btn btn-secondary';
      if (textPreviewBox) textPreviewBox.style.display = 'none';
      if (txtDownloadBtn) txtDownloadBtn.style.display = 'none';
      return;
    }

    if (data.status === 'success') {
      currentGeneratedDigest = {
        type: digestType.value, count: data.count, date_range: data.date_range, ref_date: refDateInput.value
      };
      previewTypeBadge.textContent = digestType.value.toUpperCase();
      previewDateRange.textContent = data.date_range;

      const warningBanner = document.getElementById('previewTruncationWarning');
      const warningShown = document.getElementById('warningShown');
      const warningTotal = document.getElementById('warningTotal');
      if (warningBanner && warningShown && warningTotal) {
        if (data.total_upcoming_count && data.total_upcoming_count > data.count) {
          warningShown.textContent = data.count;
          warningTotal.textContent = data.total_upcoming_count;
          warningBanner.style.display = 'block';
        } else {
          warningBanner.style.display = 'none';
        }
      }

      // HTML iframe preview
      const doc = previewIframe.contentDocument || previewIframe.contentWindow.document;
      doc.open(); doc.write(data.html); doc.close();
      previewEmpty.style.display = 'none';
      previewEmpty.querySelector('h3').textContent = 'No Digest Generated Yet';
      previewEmpty.querySelector('p').textContent  =
        'Select your configuration above and click "Generate Preview" to review the email batch.';

      // Plain-text preview
      if (textPreviewBox && data.text) {
        textPreviewBox.textContent = data.text;
        textPreviewBox.style.display = 'block';
      }

      // Plain-text download button
      if (txtDownloadBtn) {
        txtDownloadBtn.style.display = 'inline-block';
        txtDownloadBtn.onclick = () => {
          window.location.href = '/api/download/txt';
        };
      }

      sendBtn.disabled  = false;
      sendBtn.className = 'btn';
    } else {
      alert('Error generating preview: ' + data.message);
    }
  });

  // ── Dispatch Email ────────────────────────────────────────────────────────
  sendBtn.addEventListener('click', async () => {
    if (!currentGeneratedDigest) return;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span>📨</span> Sending...';

    const res  = await fetch('/api/send', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(currentGeneratedDigest),
    });
    if (res.status === 401) {
      alert('Authentication failed: Invalid or missing API Token');
      sendBtn.disabled = false;
      sendBtn.innerHTML = '<span>📨</span> Dispatch Email Notification';
      return;
    }
    const data = await res.json();

    if (data.status === 'success') {
      alert(data.message);
      sendBtn.disabled  = true;
      sendBtn.className = 'btn btn-secondary';
      sendBtn.innerHTML = '<span>📨</span> Dispatch Email Notification';
      previewEmpty.style.display = 'flex';
      previewIframe.src = 'about:blank';
      if (textPreviewBox) { textPreviewBox.textContent = ''; textPreviewBox.style.display = 'none'; }
      if (txtDownloadBtn) { txtDownloadBtn.style.display = 'none'; }
      currentGeneratedDigest = null;
      await loadLogs();
    } else {
      alert(data.message || 'Failed to send digest');
      sendBtn.disabled  = false;
      sendBtn.innerHTML = '<span>📨</span> Dispatch Email Notification';
    }
  });

  // ── Load Dispatch Logs ────────────────────────────────────────────────────
  const loadLogs = async () => {
    const res  = await fetch(`/api/logs?limit=${logsLimit}&offset=${logsOffset}`);
    const data = await res.json();
    const logs = data.logs || [];
    const total = data.total || 0;

    logsList.innerHTML = '';
    if (logs.length === 0) {
      logsList.innerHTML =
        '<div style="color:var(--text-muted);text-align:center;padding:20px;font-size:13px;">No mail dispatches logged</div>';
      updateLogsPagination(total);
      return;
    }
    logs.forEach(log => {
      const item = document.createElement('div');
      item.className = 'log-item';
      const timeStr = new Date(log.timestamp).toLocaleString();
      const isSimulated = log.status && (log.status.includes('Simulated') || log.status.includes('simulated'));
      const badgeText = isSimulated ? 'SIMULATED' : 'SENT';
      const badgeClass = isSimulated ? 'log-badge badge-simulated' : 'log-badge';
      item.innerHTML = `
        <div class="log-left">
          <span class="log-title">${log.type} Digest (${log.count} Items)</span>
          <span class="log-sub">Time: ${timeStr} &bull; To: ${escapeHTML(log.recipient)} &bull; ${escapeHTML(log.status)}</span>
        </div>
        <span class="${badgeClass}">${badgeText}</span>`;
      logsList.appendChild(item);
    });

    updateLogsPagination(total);
  };

  const updateLogsPagination = (total) => {
    const totalPages = Math.max(1, Math.ceil(total / logsLimit));
    const currentPage = Math.floor(logsOffset / logsLimit) + 1;
    
    if (logsOffset >= total && total > 0) {
      logsOffset = Math.max(0, (totalPages - 1) * logsLimit);
      loadLogs();
      return;
    }

    document.getElementById('logsPageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('logsPrevBtn').disabled = (logsOffset === 0);
    document.getElementById('logsNextBtn').disabled = (logsOffset + logsLimit >= total);
  };

  document.getElementById('logsPrevBtn').addEventListener('click', () => {
    if (logsOffset >= logsLimit) {
      logsOffset -= logsLimit;
      loadLogs();
    }
  });

  document.getElementById('logsNextBtn').addEventListener('click', () => {
    logsOffset += logsLimit;
    loadLogs();
  });

  // ── Helper ────────────────────────────────────────────────────────────────
  const escapeHTML = str => (str || '').replace(
    /[&<>'"]/g,
    t => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[t] || t)
  );

  // Initial load
  loadInterviews();
  loadLogs();
});
