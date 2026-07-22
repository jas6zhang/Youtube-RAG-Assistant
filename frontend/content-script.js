const API_BASE = 'https://youtube-rag-assistant-7.onrender.com';
// const API_BASE = 'http://localhost:8000';

// Light gating so random traffic can't hit the API directly. This is
// obfuscation, not real security (anyone can read an extension's source) —
// the real protection is server-side rate limiting. Must match the API_KEY
// env var set on the backend. Leave empty to run against an unauthenticated
// (dev) backend.
const API_KEY = '';

const N_RESULTS = 20;
const API_COOLDOWN = 1000; // client-side rate limit
const TIMEOUT = 500;
const STATUS_POLL_INTERVAL = 1500;

let last_question_asked = 0;

function apiHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (API_KEY) headers['X-API-Key'] = API_KEY;
  return headers;
}

function getVideoId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("v");
}

function formatTime(totalSeconds) {
  const s = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
  const m = Math.floor((totalSeconds / 60) % 60);
  const h = Math.floor(totalSeconds / 3600);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s}`;
  }
  return `${m}:${s}`;
}

const STATUS_LABELS = {
  pending: 'Preparing…',
  loading_captions: 'Reading captions…',
  transcribing: 'Transcribing audio (this can take a minute)…',
  ready: 'Ask Question',
  error: 'Transcript unavailable',
  unknown: 'Loading transcript…',
};

function setLoadingState(label, { enabled }) {
  const askButton = document.getElementById('ask-button');
  const questionInput = document.getElementById('question-input');
  if (!askButton || !questionInput) return;
  askButton.textContent = label;
  askButton.disabled = !enabled;
  questionInput.disabled = !enabled;
}

function loadTranscript(videoId) {
  setLoadingState('Loading transcript…', { enabled: false });
  fetch(`${API_BASE}/load_transcript`, {
    method: 'POST',
    headers: apiHeaders(),
    body: JSON.stringify({ video_id: videoId })
  })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(() => pollTranscriptStatus(videoId))
    .catch(err => {
      console.error('Error Loading transcript:', err);
      setLoadingState('Transcript unavailable', { enabled: false });
      showNotification('Error loading transcript', 'error');
    });
}

function pollTranscriptStatus(videoId) {
  const poll = () => {
    // Bail out if the user navigated to a different video mid-poll.
    if (getVideoId() !== videoId) return;

    fetch(`${API_BASE}/transcript_status/${videoId}`, { headers: apiHeaders() })
      .then(response => response.json())
      .then(data => {
        const status = data.status || 'unknown';
        const label = STATUS_LABELS[status] || STATUS_LABELS.unknown;

        if (status === 'ready') {
          setLoadingState('Ask Question', { enabled: true });
          showNotification('Transcript loaded successfully!', 'success');
        } else if (status === 'error') {
          setLoadingState('Transcript unavailable', { enabled: false });
          showNotification(data.detail || 'Transcript unavailable', 'error');
        } else {
          setLoadingState(label, { enabled: false });
          setTimeout(poll, STATUS_POLL_INTERVAL);
        }
      })
      .catch(err => {
        console.error('Error polling transcript status:', err);
        setTimeout(poll, STATUS_POLL_INTERVAL);
      });
  };
  poll();
}

function showNotification(message, type = 'success') {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 10px 15px;
    border-radius: 5px;
    color: white;
    font-weight: bold;
    z-index: 10000;
    background-color: ${type === 'error' ? 'red' : 'green'};
  `;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 3000);
}

function injectUI() {
  // Find the sidebar with recommended videos
  const secondary = document.querySelector('#secondary');
  if (!secondary) {
    // Try again later if not found (YouTube loads dynamically)
    setTimeout(injectUI, TIMEOUT);
    return;
  }

  // Avoid duplicate insertion
  if (document.getElementById('youtube-rag-ui')) {
    document.getElementById('question-input').value = '';
    document.getElementById('answer').innerHTML = '';
    document.getElementById('answer').style.display = 'none';
    setLoadingState('Loading transcript…', { enabled: false });
    return;
  }

  const container = document.createElement('div');
  container.id = 'youtube-rag-ui';
  container.style.cssText = `
    background: #fff;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    font-family: Arial, sans-serif;
    box-sizing: border-box;
  `;

  container.innerHTML = `
    <h3 style="margin: 0 0 10px 0; color: #333;">Youtube Video Assistant</h3>
    <textarea id="question-input" placeholder="Ask a question about this video. The more detailed the question, the more context the assistant will have."
              style="width: 95%; height: 80px; padding: 8px; border: 1px solid #ddd; border-radius: 4px; resize: vertical; margin-bottom: 10px;"></textarea>
    <button id="ask-button" style="width: 100%; padding: 8px; background: red; color: white; border: none; border-radius: 4px; cursor: pointer;">
      Ask Question
    </button>
    <div id="answer" style="margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px; display: none;"></div>
    <div style="text-align: right; font-size: 12px; margin-top: 10px;">
      <a href="https://buy.stripe.com/4gMbJ17JSasY8625SKasg00" target="_blank" style="color: #888; text-decoration: none;">
        ❤️ Support this extension
      </a>
    </div>
  `;

  // Insert as the first child of the sidebar
  secondary.insertBefore(container, secondary.firstChild);

  setLoadingState('Loading transcript…', { enabled: false });

  const askButton = document.getElementById('ask-button');
  const questionInput = document.getElementById('question-input');
  askButton.addEventListener('click', () => askQuestion(getVideoId()));
  questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askQuestion(getVideoId());
    }
  });
}

function renderAnswer(answerDiv, fullText) {
  // The model appends a "TIMESTAMPS:" section we render separately as
  // citations — hide it from the streamed answer prose.
  const idx = fullText.search(/TIMESTAMPS:/i);
  const answerText = idx >= 0 ? fullText.slice(0, idx) : fullText;
  answerDiv.innerHTML =
    `<strong>Answer:</strong> ${escapeHtml(answerText.trim()).replace(/\n/g, '<br>')}`;
}

function renderCitations(answerDiv, citations) {
  if (!citations || citations.length === 0) {
    const note = document.createElement('div');
    note.style.cssText = 'margin-top: 10px;';
    note.innerHTML =
      '<strong>Most Relevant Timestamps:</strong> No related content to your question was found.';
    answerDiv.appendChild(note);
    return;
  }

  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'margin-top: 10px;';
  let html = '<strong>Most Relevant Timestamps:</strong><ul style="padding-left: 16px; margin: 6px 0 0 0;">';
  citations.forEach(cite => {
    const label = formatTime(cite.seconds);
    const snippet = cite.snippet ? escapeHtml(cite.snippet) : '';
    html += `<li style="margin-bottom: 6px;">
      <a href="#" class="timestamp-link" data-seconds="${cite.seconds}" style="font-weight: bold;">${label}</a>
      ${snippet ? `<div style="font-size: 12px; color: #555; margin-top: 2px;">“${snippet}”</div>` : ''}
    </li>`;
  });
  html += '</ul>';
  wrapper.innerHTML = html;
  answerDiv.appendChild(wrapper);

  wrapper.querySelectorAll('.timestamp-link').forEach(link => {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      const seconds = parseInt(this.getAttribute('data-seconds'), 10);
      const video = document.querySelector('video');
      if (video && !isNaN(seconds)) {
        video.currentTime = seconds;
        video.play();
      }
    });
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

async function askQuestion(videoId) {
  const questionInput = document.getElementById('question-input');
  const answerDiv = document.getElementById('answer');
  const askButton = document.getElementById('ask-button');

  const question = questionInput.value.trim();
  const currentTime = Date.now();
  if (currentTime - last_question_asked < API_COOLDOWN) {
    showNotification('Please wait a moment before asking another question', 'error');
    return;
  }
  if (!question) {
    showNotification('Please enter a question', 'error');
    return;
  }

  askButton.textContent = 'Asking...';
  askButton.disabled = true;
  answerDiv.style.display = 'block';
  answerDiv.innerHTML = 'Loading answer...';

  try {
    const response = await fetch(`${API_BASE}/ask_question`, {
      method: 'POST',
      headers: apiHeaders(),
      body: JSON.stringify({
        video_id: videoId,
        question: question,
        n_results: N_RESULTS
      })
    });
    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';
    let startedAnswer = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split('\n\n');
      buffer = events.pop(); // keep the trailing partial event

      for (const event of events) {
        const line = event.replace(/^data:\s?/, '').trim();
        if (!line || line === '[DONE]') continue;

        let payload;
        try {
          payload = JSON.parse(line);
        } catch (_) {
          continue;
        }

        if (payload.type === 'token') {
          fullText += payload.text;
          startedAnswer = true;
          renderAnswer(answerDiv, fullText);
        } else if (payload.type === 'citations') {
          renderCitations(answerDiv, payload.citations);
        } else if (payload.type === 'error') {
          throw new Error(payload.message || 'Server error');
        }
      }
    }

    if (!startedAnswer) {
      answerDiv.innerHTML = 'No answer was returned. Please try again.';
    }
  } catch (err) {
    answerDiv.innerHTML = `Error: ${err.message}`;
    showNotification('Error getting answer', 'error');
  } finally {
    askButton.textContent = 'Ask Question';
    askButton.disabled = false;
    last_question_asked = currentTime;
  }
}

const waitForYoutubeVideo = (selector, callback) => {
  const interval = setInterval(() => {
    if (document.querySelector(selector)) {
      clearInterval(interval);
      const videoId = getVideoId();
      if (videoId) {
        console.log("Retrieved Video ID", videoId);
        loadTranscript(videoId);
      }
      callback();
    }
  }, 300);
};

waitForYoutubeVideo('ytd-watch-flexy', injectUI);
window.addEventListener('yt-navigate-finish', () => {
  waitForYoutubeVideo('ytd-watch-flexy', injectUI);
});
