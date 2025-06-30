function getYoutubeVideo() {
  const videoId = getVideoId();
  console.log('videoId Obtained', videoId);
  return `https://www.youtube.com/watch?v=${videoId}`;
}

// only returns the query portion of the link 

function getVideoId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("v");
}

function loadTranscript(videoId) {
  console.log('typeof videoId', typeof videoId); 
  console.log('videoId', videoId);
  fetch('http://localhost:8000/load_transcript', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }, 
    body: JSON.stringify({video_id: videoId})
  })
    .then(response => response.json())
    .then(data => {
      console.log('Transcript Loaded:', data);
      showNotification('Transcript loaded successfully!', 'success');
    })
    .catch(err => {
      console.error('Error Loading transcript:', err);
      showNotification('Error loading transcript', 'error');
    });
}

function showNotification(message, type='success') {
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
    setTimeout(injectUI, 500);
    return;
  }

  // Avoid duplicate insertion
  if (document.getElementById('youtube-rag-ui')) return;

  // Create your UI container
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
              style="width: 80%; height: 80px; padding-right: 16px; border: 1px solid #ddd; border-radius: 4px; resize: vertical; margin-bottom: 10px;"></textarea>
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

  // Add event listener for ask button
  
  const videoId = getVideoId(); 
  
  document.getElementById('ask-button').addEventListener('click',() => askQuestion(videoId))
  document.getElementById('question-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askQuestion(videoId);
    }
  }); 
}

const API_COOLDOWN = 1000 // rate limit
let last_question_asked = 0

function askQuestion(videoId) {
  const questionInput = document.getElementById('question-input');
  const answerDiv = document.getElementById('answer');
  const askButton = document.getElementById('ask-button');
  
  const question = questionInput.value.trim();
  const currentTime = Date.now()
  if (currentTime - last_question_asked < API_COOLDOWN) {
    showNotification('Please wait a moment before asking another question', 'error')
    return; 
  }
  if (!question) {
    showNotification('Please enter a question', 'error');
    return;
  }
  
  // Show loading state
  askButton.textContent = 'Asking...';
  askButton.disabled = true;
  answerDiv.style.display = 'block';
  answerDiv.innerHTML = 'Loading answer...';
  
  fetch('http://localhost:8000/ask_question', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      video_id: videoId, 
      question: question,
      n_results: 20
    })
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json();
    })
    .then(data => {
      const response = data.response;
      const textResponseMatch = response.match(/^(.*?)\s*TIMESTAMPS:/s);
      let html = ""; 
      if (textResponseMatch) {
        html += `<strong>Answer:</strong><br>${textResponseMatch[1].trim()}<br><br>`;
      }
      // else {
      //   html += `<strong>Answer:</strong><br>${response}<br><br>`;
      // }
      // add s to match newlines as well (dot doesn't)
      const timestampMatch = response.match(/TIMESTAMPS:\s*(.+)/s)
      console.log("Timestamp Match", timestampMatch)
      if (timestampMatch) {
        html += `<strong>Most Relevant Timestamps: </strong>`;
        if (timestampMatch[1] == 'NONE' || timestampMatch[1] == 'none') {
          html += `No related content to your question was found at any timestamps. Please check your spelling or ask another question.`
        } else {
          const timestampStrings = timestampMatch[1].split(',').map(s => s.trim());
          html += '<ul style="padding-left: 16px;">';
          timestampStrings.forEach(timeStr => {
            const seconds = Math.floor(parseFloat(timeStr));
            let formattedTime; 
            const time = new Date(seconds * 1000);
            if (seconds >= 3600) {
              formattedTime = moment(time).format('HH:mm:ss');
            } else {
              formattedTime = moment(time).format('mm:ss');
            }
            console.log("formatted time", formattedTime);
            html += `<li>
              <a href="#" class="timestamp-link" data-seconds="${seconds}">${formattedTime}</a>
            </li>`;
          });
          html += '</ul>';
        }
      }
      
      answerDiv.innerHTML = html;

      document.querySelectorAll('.timestamp-link').forEach(link => {
        link.addEventListener('click', function(e) {
          e.preventDefault();
          const seconds = parseInt(this.getAttribute('data-seconds'), 10);
          const video = document.querySelector('video');
          if (video && !isNaN(seconds)) {
            video.currentTime = seconds;
            video.play();
          }
        });
      });
    })
    .catch(err => {
      answerDiv.innerHTML = `Error: ${err.message}`;
      showNotification('Error getting answer', 'error');
    })
    .finally(() => {
      askButton.textContent = 'Ask Question';
      askButton.disabled = false;
      last_question_asked = currentTime; // Reset rate limiting on both success and error
    });
}

const waitForYoutubeVideo = (selector, callback) => {
  const interval = setInterval(() => {
    if (document.querySelector(selector)) {
      clearInterval(interval);
      // Get video ID and load transcript
      const videoId = getVideoId();
      if (videoId) {
        console.log("Retrieved Video ID", videoId)
        loadTranscript(videoId);
      }
      callback();
    }
  }, 300)
}

waitForYoutubeVideo('ytd-watch-flexy', injectUI)
