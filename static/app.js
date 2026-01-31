const API_BASE_URL = 'http://localhost:8000';

// Application state
const state = {
    studentProfile: null,
    selectedSchool: null,
    interviewQuestions: [],
    currentQuestionIndex: 0,
    mediaRecorder: null,
    recordingChunks: [],
    recordingStartTime: null
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupSearchSection();
    setupApplicationSection();
    setupInterviewSection();
    loadStoredProfile();
});

// Navigation
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const section = item.dataset.section;
            switchSection(section);
        });
    });
}

function switchSection(sectionName) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === sectionName) {
            item.classList.add('active');
        }
    });
    
    // Update content
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`${sectionName}Section`).classList.add('active');
}

// ===== SEARCH SECTION =====
function setupSearchSection() {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('schoolSearchInput');
    const exampleChips = document.querySelectorAll('.example-chip');
    
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    exampleChips.forEach(chip => {
        chip.addEventListener('click', () => {
            searchInput.value = chip.textContent;
            performSearch();
        });
    });
    
    // Chat functionality
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatInput = document.getElementById('chatInput');
    
    chatSendBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

async function performSearch() {
    const searchInput = document.getElementById('schoolSearchInput');
    const query = searchInput.value.trim();
    
    if (!query) return;
    
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = '<div class="loading">🔍 Searching for schools...</div>';
    
    try {
        // TODO: Call the actual search API
        // For now, show placeholder
        setTimeout(() => {
            resultsContainer.innerHTML = `
                <div class="search-result-item">
                    <h4>📚 Search functionality will be implemented</h4>
                    <p>Query: ${query}</p>
                    <p class="note">This will search schools by ZIP code or name using the AI agent</p>
                </div>
            `;
            
            // Show chat section
            document.getElementById('schoolChat').classList.remove('hidden');
        }, 1000);
        
    } catch (error) {
        resultsContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    const chatMessages = document.getElementById('chatMessages');
    
    // Add user message
    appendChatMessage('user', message);
    chatInput.value = '';
    
    // Add thinking indicator
    appendChatMessage('assistant', '🤔 Thinking...');
    
    try {
        // TODO: Call the actual chat API
        // For now, show placeholder
        setTimeout(() => {
            removeLast AI message();
            appendChatMessage('assistant', 'Chat functionality will be implemented. This will use the AI agent to answer questions about schools.');
        }, 1500);
        
    } catch (error) {
        console.error('Chat error:', error);
    }
}

function appendChatMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-content">
            <strong>${role === 'user' ? '👤 You' : '🤖 Assistant'}:</strong>
            <p>${content}</p>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLastAIMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const messages = chatMessages.querySelectorAll('.chat-message.assistant');
    if (messages.length > 0) {
        messages[messages.length - 1].remove();
    }
}

// ===== APPLICATION SECTION =====
function setupApplicationSection() {
    const saveProfileBtn = document.getElementById('saveProfileBtn');
    const generateResponseBtn = document.getElementById('generateResponseBtn');
    
    saveProfileBtn.addEventListener('click', saveProfile);
    generateResponseBtn.addEventListener('click', generateResponse);
}

function saveProfile() {
    const profileText = document.getElementById('studentProfile').value.trim();
    
    if (!profileText) {
        alert('Please enter your profile information');
        return;
    }
    
    state.studentProfile = profileText;
    localStorage.setItem('studentProfile', profileText);
    
    // Update sidebar
    document.querySelector('.student-profile-summary .no-profile').innerHTML = 
        `<strong>Profile saved!</strong><br/>${profileText.substring(0, 50)}...`;
    
    alert('Profile saved successfully!');
}

function loadStoredProfile() {
    const stored = localStorage.getItem('studentProfile');
    if (stored) {
        state.studentProfile = stored;
        document.getElementById('studentProfile').value = stored;
        document.querySelector('.student-profile-summary .no-profile').innerHTML = 
            `<strong>Profile loaded</strong><br/>${stored.substring(0, 50)}...`;
    }
}

async function generateResponse() {
    const question = document.getElementById('applicationQuestion').value.trim();
    
    if (!question) {
        alert('Please enter an application question');
        return;
    }
    
    if (!state.studentProfile) {
        alert('Please save your profile first');
        return;
    }
    
    const responseArea = document.getElementById('applicationResponse');
    const generatedText = document.getElementById('generatedText');
    
    responseArea.classList.remove('hidden');
    generatedText.innerHTML = '✨ Generating personalized response...';
    
    try {
        // TODO: Call the actual API with profile, school context, and question
        setTimeout(() => {
            generatedText.innerHTML = `
                <p><strong>Note:</strong> Application writing functionality will be implemented.</p>
                <p>This will use your profile and school information to generate a personalized response to: "${question}"</p>
            `;
        }, 2000);
        
    } catch (error) {
        generatedText.innerHTML = `Error: ${error.message}`;
    }
}

// ===== INTERVIEW SECTION =====
function setupInterviewSection() {
    const generateQuestionsBtn = document.getElementById('generateQuestionsBtn');
    const recordBtn = document.getElementById('recordBtn');
    const nextQuestionBtn = document.getElementById('nextQuestionBtn');
    
    generateQuestionsBtn.addEventListener('click', generateQuestions);
    recordBtn.addEventListener('click', toggleRecording);
    nextQuestionBtn.addEventListener('click', loadNextQuestion);
}

async function generateQuestions() {
    if (!state.studentProfile) {
        alert('Please save your profile first');
        return;
    }
    
    const questionsContainer = document.getElementById('interviewQuestions');
    const questionsList = document.getElementById('questionsList');
    
    questionsContainer.classList.remove('hidden');
    questionsList.innerHTML = '<div class="loading">✨ Generating interview questions...</div>';
    
    try {
        // TODO: Call the actual API to generate questions
        setTimeout(() => {
            const placeholderQuestions = [
                'Why are you interested in attending our school?',
                'Tell us about a challenge you overcame.',
                'What are your academic interests and goals?',
                'How do you contribute to your community?',
                'What makes you a good fit for our school?'
            ];
            
            state.interviewQuestions = placeholderQuestions;
            state.currentQuestionIndex = 0;
            
            questionsList.innerHTML = '';
            placeholderQuestions.forEach((q, index) => {
                const item = document.createElement('div');
                item.className = 'question-item';
                item.innerHTML = `<strong>Q${index + 1}:</strong> ${q}`;
                item.addEventListener('click', () => startPracticing(index));
                questionsList.appendChild(item);
            });
            
            document.getElementById('recordingArea').classList.remove('hidden');
            loadQuestion(0);
        }, 2000);
        
    } catch (error) {
        questionsList.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

function startPracticing(index) {
    state.currentQuestionIndex = index;
    loadQuestion(index);
    document.getElementById('recordingArea').scrollIntoView({ behavior: 'smooth' });
}

function loadQuestion(index) {
    const question = state.interviewQuestions[index];
    document.getElementById('currentQuestion').textContent = question;
    document.getElementById('transcriptionArea').classList.add('hidden');
    resetRecorder();
}

function loadNextQuestion() {
    state.currentQuestionIndex++;
    if (state.currentQuestionIndex >= state.interviewQuestions.length) {
        state.currentQuestionIndex = 0;
    }
    loadQuestion(state.currentQuestionIndex);
}

async function toggleRecording() {
    const recordBtn = document.getElementById('recordBtn');
    
    if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.mediaRecorder = new MediaRecorder(stream);
        state.recordingChunks = [];
        state.recordingStartTime = Date.now();
        
        state.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                state.recordingChunks.push(event.data);
            }
        };
        
        state.mediaRecorder.onstop = processRecording;
        
        state.mediaRecorder.start();
        
        // Update UI
        const recordBtn = document.getElementById('recordBtn');
        recordBtn.classList.add('recording');
        recordBtn.querySelector('.record-icon').textContent = '⏹';
        recordBtn.querySelector('.record-label').textContent = 'Stop Recording';
        
        // Start timer
        updateTimer();
        
        // Auto-stop after 60 seconds
        setTimeout(() => {
            if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
                stopRecording();
            }
        }, 60000);
        
    } catch (error) {
        alert('Error accessing microphone: ' + error.message);
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
        state.mediaRecorder.stop();
        state.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        
        // Update UI
        const recordBtn = document.getElementById('recordBtn');
        recordBtn.classList.remove('recording');
        recordBtn.querySelector('.record-icon').textContent = '⏺';
        recordBtn.querySelector('.record-label').textContent = 'Start Recording';
    }
}

function updateTimer() {
    if (!state.recordingStartTime || !state.mediaRecorder || state.mediaRecorder.state !== 'recording') {
        return;
    }
    
    const elapsed = Math.floor((Date.now() - state.recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    const totalMinutes = 1;
    const totalSeconds = 0;
    
    document.getElementById('recordTimer').textContent = 
        `${minutes}:${seconds.toString().padStart(2, '0')} / ${totalMinutes}:${totalSeconds.toString().padStart(2, '0')}`;
    
    if (elapsed < 60) {
        requestAnimationFrame(updateTimer);
    }
}

function resetRecorder() {
    document.getElementById('recordTimer').textContent = '0:00 / 1:00';
    const recordBtn = document.getElementById('recordBtn');
    recordBtn.classList.remove('recording');
    recordBtn.querySelector('.record-icon').textContent = '⏺';
    recordBtn.querySelector('.record-label').textContent = 'Start Recording';
}

async function processRecording() {
    const audioBlob = new Blob(state.recordingChunks, { type: 'audio/webm' });
    
    // Show transcription area
    document.getElementById('transcriptionArea').classList.remove('hidden');
    document.getElementById('transcriptionText').textContent = '🎙️ Transcribing...';
    document.getElementById('feedbackContent').textContent = '⏳ Analyzing...';
    
    try {
        // TODO: Call the actual transcription API
        setTimeout(() => {
            document.getElementById('transcriptionText').textContent = 
                'Transcription functionality will be implemented. This will transcribe your audio response and display it here.';
            
            document.getElementById('feedbackContent').innerHTML = `
                <p><strong>Note:</strong> AI feedback will be provided on:</p>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>Grammar and clarity</li>
                    <li>Relevance to the question</li>
                    <li>Alignment with school values</li>
                    <li>Suggestions for improvement</li>
                </ul>
            `;
        }, 2000);
        
    } catch (error) {
        document.getElementById('transcriptionText').textContent = 'Error: ' + error.message;
        document.getElementById('feedbackContent').textContent = 'Could not generate feedback.';
    }
}
