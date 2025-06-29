// // DOM Front-End 
// function Overlay() {
//   if (document.getElementById('rag-overlay')) { // if doesn't exist
//     return; 
//   }
//   const overlay = document.createElement('rag-overlay')
//   overlay.id = 'rag-overlay';

//   document.body.appendChild(overlay)
  
//   overlay.innerHTML = `
//     <h4>Ask questions about this video</h4>
//     <textarea id="rag-question" style="width: 100%; height: 60px;"></textarea>
//     <button id="rag-submit">Ask</button>
//     <div id="answer"></div>
//   `
//   // isnt it easier just to add html here
//   // const overlay_submit = document.createElement('rag-submit')
//   // overlay_submit = 'rag-submit'
  
//   // overlay.appendChild(overlay_submit)
//   chrome.action.onClicked.addListener((tab) => {
    
//     chrome.scripting.executeScript({
//       target: { tabId: tab.id },
//       files: ['content.js'],
//     });
//     // send the video id, the question to teh backend 
//     document.getElementById('rag-submit').addEventListener('click', () => {
//       const question = document.getElementById('rag-question').value;
//       const videoId = URLSearchParams(window.location.search.get('v'));
    
//       // message with call back fucnito n
    
//       // can send an object as message and display answer
//       chrome.runtime.sendMessage({
//         type: 'fetch-answer',
//         videoId: videoId,
//         question: question,
//       }, (response) => {
//         document.getElementById('rag-answer').innerText = response
//       })
//     })
//   });
// }

// Overlay(); 
