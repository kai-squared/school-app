const API_BASE_URL = window.location.origin;

// Application state
const state = {
    studentProfile: null,
    watchlist: [],
    selectedSchool: null,
    searchContext: '',
    interviewQuestions: [],
    currentQuestionIndex: 0,
    mediaRecorder: null,
    recordingChunks: [],
    recordingStartTime: null,
    currentSearchQuery: null,
    currentSearchType: null,
    currentMiles: 10,
    loadedSchools: [],
    allSchoolsLoaded: false
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadFromLocalStorage();
    setupNavigation();
    setupSearchSection();
    setupProfileModal();
    setupApplicationSection();
    setupInterviewSection();
    updateUIFromState();
});

//===== LOCAL STORAGE =====
function loadFromLocalStorage() {
    const profile = localStorage.getItem('studentProfile');
    const watchlist = localStorage.getItem('watchlist');
    
    if (profile) {
        try {
            state.studentProfile = JSON.parse(profile);
        } catch (e) {
            console.error('Error loading profile:', e);
        }
    }
    
    if (watchlist) {
        try {
            state.watchlist = JSON.parse(watchlist);
        } catch (e) {
            console.error('Error loading watchlist:', e);
        }
    }
}

function saveToLocalStorage() {
    localStorage.setItem('studentProfile', JSON.stringify(state.studentProfile));
    localStorage.setItem('watchlist', JSON.stringify(state.watchlist));
}

function updateUIFromState() {
    updateProfileButton();
    updateWatchlist();
    updateSchoolSelectors();
}

//===== NAVIGATION =====
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
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === sectionName) {
            item.classList.add('active');
        }
    });
    
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`${sectionName}Section`).classList.add('active');
}

//===== PROFILE MODAL =====
function setupProfileModal() {
    const manageProfileBtn = document.getElementById('manageProfileBtn');
    const profileForm = document.getElementById('profileForm');
    
    manageProfileBtn.addEventListener('click', openProfileModal);
    profileForm.addEventListener('submit', handleProfileSubmit);
    
    // Populate form if profile exists
    if (state.studentProfile) {
        populateProfileForm(state.studentProfile);
    }
}

function openProfileModal() {
    document.getElementById('profileModal').classList.remove('hidden');
}

function closeProfileModal() {
    document.getElementById('profileModal').classList.add('hidden');
}

function populateProfileForm(profile) {
    const form = document.getElementById('profileForm');
    Object.keys(profile).forEach(key => {
        const input = form.elements[key];
        if (input) {
            input.value = profile[key] || '';
        }
    });
}

function handleProfileSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const profile = {};
    
    formData.forEach((value, key) => {
        profile[key] = value;
    });
    
    state.studentProfile = profile;
    saveToLocalStorage();
    updateProfileButton();
    closeProfileModal();
    
    alert('Profile saved successfully! ✅');
}

function updateProfileButton() {
    const btn = document.getElementById('manageProfileBtn');
    const btnText = document.getElementById('profileBtnText');
    
    if (state.studentProfile) {
        btnText.textContent = state.studentProfile.studentName || 'View Profile';
        btn.classList.add('has-profile');
    } else {
        btnText.textContent = 'Create Profile';
        btn.classList.remove('has-profile');
    }
}

//===== WATCHLIST =====
function addToWatchlist(school) {
    // Check if already in watchlist
    const exists = state.watchlist.find(s => s.name === school.name);
    if (exists) {
        alert('School already in watchlist');
        return;
    }
    
    state.watchlist.push(school);
    saveToLocalStorage();
    updateWatchlist();
    updateSchoolSelectors();
}

function removeFromWatchlist(schoolName) {
    state.watchlist = state.watchlist.filter(s => s.name !== schoolName);
    saveToLocalStorage();
    updateWatchlist();
    updateSchoolSelectors();
}

function updateWatchlist() {
    const container = document.getElementById('watchlistContainer');
    
    if (state.watchlist.length === 0) {
        container.innerHTML = '<p class="empty-watchlist">No schools added yet</p>';
        return;
    }
    
    container.innerHTML = state.watchlist.map(school => `
        <div class="watchlist-item" data-school="${school.name}">
            <div class="watchlist-item-name">${school.name}</div>
            <div class="watchlist-item-type">${school.type || 'School'}</div>
            <button class="remove-watchlist" onclick="removeFromWatchlist('${school.name.replace(/'/g, "\\'")}')">×</button>
        </div>
    `).join('');
}

function updateSchoolSelectors() {
    const appSelect = document.getElementById('appSchoolSelect');
    const interviewSelect = document.getElementById('interviewSchoolSelect');
    
    const options = state.watchlist.map(school => 
        `<option value="${school.name}">${school.name}</option>`
    ).join('');
    
    appSelect.innerHTML = '<option value="">Select a school...</option>' + options;
    interviewSelect.innerHTML = '<option value="">Select a school...</option>' + options;
    
    // Enable/disable buttons
    const analyzeBtn = document.getElementById('analyzeQuestionBtn');
    const generateBtn = document.getElementById('generateQuestionsBtn');
    
    appSelect.addEventListener('change', (e) => {
        analyzeBtn.disabled = !e.target.value;
    });
    
    interviewSelect.addEventListener('change', (e) => {
        generateBtn.disabled = !e.target.value;
    });
}

//===== SEARCH SECTION =====
function setupSearchSection() {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('schoolSearchInput');
    const exampleChips = document.querySelectorAll('.example-chip');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatInput = document.getElementById('chatInput');
    const milesSlider = document.getElementById('milesSlider');
    const milesValue = document.getElementById('milesValue');
    const milesControl = document.getElementById('milesControl');
    const searchTypeRadios = document.querySelectorAll('input[name="searchType"]');
    
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    
    // Handle search type changes
    searchTypeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const type = e.target.value;
            updatePlaceholder(type);
            updateMilesControlVisibility(type, searchInput.value);
        });
    });
    
    // Show/hide miles control based on input
    searchInput.addEventListener('input', () => {
        const selectedType = document.querySelector('input[name="searchType"]:checked').value;
        updateMilesControlVisibility(selectedType, searchInput.value);
    });
    
    // Update miles value display
    milesSlider.addEventListener('input', (e) => {
        milesValue.textContent = e.target.value;
    });
    
    exampleChips.forEach(chip => {
        chip.addEventListener('click', () => {
            searchInput.value = chip.textContent;
            // Auto-select search type based on example
            if (/^\d{5}$/.test(chip.textContent)) {
                document.querySelector('input[name="searchType"][value="zip"]').checked = true;
            } else {
                document.querySelector('input[name="searchType"][value="name"]').checked = true;
            }
            updatePlaceholder(document.querySelector('input[name="searchType"]:checked').value);
            searchInput.dispatchEvent(new Event('input'));
            performSearch();
        });
    });
    
    chatSendBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

function updatePlaceholder(searchType) {
    const searchInput = document.getElementById('schoolSearchInput');
    const placeholders = {
        zip: 'Enter ZIP code (e.g., 10001)',
        city: 'Enter city name (e.g., New York)',
        state: 'Enter state name (e.g., New York)',
        name: 'Enter school name (e.g., Phillips Academy)'
    };
    searchInput.placeholder = placeholders[searchType] || 'Enter search query';
}

function updateMilesControlVisibility(searchType, value) {
    const milesControl = document.getElementById('milesControl');
    // Show miles control for ZIP or city searches with valid input
    if ((searchType === 'zip' && /^\d{1,5}$/.test(value)) || 
        (searchType === 'city' && value.trim().length > 0)) {
        milesControl.classList.remove('hidden');
    } else {
        milesControl.classList.add('hidden');
    }
}

async function performSearch() {
    const searchInput = document.getElementById('schoolSearchInput');
    const query = searchInput.value.trim();
    
    if (!query) return;
    
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = '<div class="loading">🔍 Searching for schools...</div>';
    
    // Get selected search type
    const searchType = document.querySelector('input[name="searchType"]:checked').value;
    
    // Get miles value for ZIP/city search
    const miles = (searchType === 'zip' || searchType === 'city') ? 
        parseInt(document.getElementById('milesSlider').value) : 10;
    
    // Reset state for new search
    state.currentSearchQuery = query;
    state.currentSearchType = searchType;
    state.currentMiles = miles;
    state.loadedSchools = [];
    state.allSchoolsLoaded = false;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/schools/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, search_type: searchType, miles: miles })
        });
        
        // Check if response is actually JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            console.error('Non-JSON response received:', contentType);
            throw new Error('Server returned an invalid response. Please try again.');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Search failed');
        }
        
        if (searchType === 'name') {
            displaySchoolDetails(data.school);
        } else {
            // ZIP, city, or state search - display list
            const displayMiles = data.miles || miles;
            const locationText = searchType === 'zip' ? `ZIP ${query}` : 
                               searchType === 'city' ? `${query}` : 
                               `${query} state`;
            const distanceText = (searchType === 'zip' || searchType === 'city') ? 
                               ` within ${displayMiles} miles` : '';
            
            // Save loaded schools
            state.loadedSchools = data.schools || [];
            displaySchoolList(state.loadedSchools, locationText, distanceText);
        }
        
        // Show chat section
        document.getElementById('schoolChat').classList.remove('hidden');
        state.searchContext = JSON.stringify(data);
        
    } catch (error) {
        console.error('Search error:', error);
        resultsContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

function displaySchoolList(schools, location, distanceText) {
    const resultsContainer = document.getElementById('searchResults');
    
    if (schools.length === 0) {
        resultsContainer.innerHTML = `
            <div class="error">No schools found in ${location}${distanceText}. Try adjusting your search.</div>
        `;
        return;
    }
    
    const loadMoreButton = !state.allSchoolsLoaded ? `
        <div class="load-more-container">
            <button id="loadMoreBtn" class="primary-btn" onclick="loadMoreSchools()">
                Load More Schools
            </button>
        </div>
    ` : '';
    
    const html = `
        <div class="search-results-header">
            <h3>Schools in ${location}${distanceText}</h3>
            <p>${schools.length} schools loaded</p>
        </div>
        ${schools.map(school => createSchoolCard(school, false)).join('')}
        ${loadMoreButton}
    `;
    
    resultsContainer.innerHTML = html;
}

async function loadMoreSchools() {
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (!loadMoreBtn) return;
    
    loadMoreBtn.disabled = true;
    loadMoreBtn.textContent = 'Loading...';
    
    try {
        // Get list of already loaded school names to exclude
        const excludeSchools = state.loadedSchools.map(s => s.name);
        
        const response = await fetch(`${API_BASE_URL}/api/schools/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: state.currentSearchQuery, 
                search_type: state.currentSearchType, 
                miles: state.currentMiles,
                exclude_schools: excludeSchools
            })
        });
        
        // Check if response is actually JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            console.error('Non-JSON response received:', contentType);
            throw new Error('Server returned an invalid response. Please try again.');
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load more schools');
        }
        
        const newSchools = data.schools || [];
        
        if (newSchools.length === 0) {
            state.allSchoolsLoaded = true;
            loadMoreBtn.textContent = 'No more schools found';
            setTimeout(() => {
                loadMoreBtn.style.display = 'none';
            }, 2000);
            return;
        }
        
        // Add new schools to loaded list
        state.loadedSchools = [...state.loadedSchools, ...newSchools];
        
        // Re-render the list
        const locationText = state.currentSearchType === 'zip' ? `ZIP ${state.currentSearchQuery}` : 
                           state.currentSearchType === 'city' ? `${state.currentSearchQuery}` : 
                           `${state.currentSearchQuery} state`;
        const distanceText = (state.currentSearchType === 'zip' || state.currentSearchType === 'city') ? 
                           ` within ${state.currentMiles} miles` : '';
        
        displaySchoolList(state.loadedSchools, locationText, distanceText);
        
    } catch (error) {
        console.error('Load more error:', error);
        loadMoreBtn.textContent = 'Error loading more';
        loadMoreBtn.disabled = false;
    }
}

function displaySchoolDetails(school) {
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = createSchoolCard(school, true);
}

function createSchoolCard(school, expanded = false) {
    const isInWatchlist = state.watchlist.some(s => s.name === school.name);
    
    return `
        <div class="school-card" data-school-name="${school.name}">
            <div class="school-card-header">
                <div>
                    <div class="school-card-title">${school.name}</div>
                    <div class="school-card-type">${school.type || 'Private'} ${school.grade_range ? '• ' + school.grade_range : ''}</div>
                </div>
                <div class="school-card-actions">
                    <button class="icon-btn ${isInWatchlist ? 'added' : ''}" onclick="toggleWatchlist('${school.name.replace(/'/g, "\\'")}', ${JSON.stringify(school).replace(/"/g, '&quot;')})" title="Add to watchlist">
                        ${isInWatchlist ? '✓' : '+'}
                    </button>
                    ${!expanded ? `<button class="icon-btn" onclick="loadSchoolDetails('${school.name.replace(/'/g, "\\'")}')" title="Search School Details">ℹ️</button>` : ''}
                </div>
            </div>
            ${school.niche_ranking ? `<div class="school-card-meta"><span class="niche-badge">🏅 ${school.niche_ranking}</span></div>` : ''}
            ${school.address ? `<div class="school-card-meta">📍 ${school.address}</div>` : ''}
            ${school.website ? `<div class="school-card-meta">🌐 <a href="${school.website}" target="_blank" onclick="event.stopPropagation()">${school.website}</a></div>` : ''}
            <div class="school-card-description">${school.brief_description || school.description || ''}</div>
            ${expanded ? `
                <div class="school-card-details expanded">
                    ${school.tuition ? `<div class="detail-item"><div class="detail-label">💰 Tuition</div><div class="detail-value">${school.tuition}</div></div>` : ''}
                    ${school.rating ? `<div class="detail-item"><div class="detail-label">⭐ Rating</div><div class="detail-value">${school.rating}</div></div>` : ''}
                    ${school.academic_ranking ? `<div class="detail-item"><div class="detail-label">🏆 Academic Ranking</div><div class="detail-value">${school.academic_ranking}</div></div>` : ''}
                    ${school.school_info ? `<div class="detail-item"><div class="detail-label">ℹ️ School Information</div><div class="detail-value">${school.school_info}</div></div>` : ''}
                    ${school.community ? `<div class="detail-item"><div class="detail-label">🏘️ Community</div><div class="detail-value">${school.community}</div></div>` : ''}
                    ${school.college_placement ? `<div class="detail-item"><div class="detail-label">🎓 College Placement</div><div class="detail-value">${school.college_placement}</div></div>` : ''}
                    ${school.core_values ? `<div class="detail-item"><div class="detail-label">💎 Core Values</div><div class="detail-value">${school.core_values}</div></div>` : ''}
                </div>
            ` : ''}
        </div>
    `;
}

async function loadSchoolDetails(schoolName) {
    // Find the school card
    const schoolCard = document.querySelector(`[data-school-name="${schoolName}"]`);
    if (!schoolCard) return;
    
    // Disable transitions temporarily
    schoolCard.style.transition = 'none';
    
    // Show loading state
    const originalHTML = schoolCard.innerHTML;
    schoolCard.innerHTML = '<div class="loading" style="padding: 40px; text-align: center;">📚 Loading detailed information...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/schools/details`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ school_name: schoolName })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load details');
        }
        
        // Create a new card element
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = createSchoolCard(data.school, true);
        const newCard = tempDiv.firstElementChild;
        
        // Disable transition on new card too
        newCard.style.transition = 'none';
        
        // Replace the card
        schoolCard.parentNode.replaceChild(newCard, schoolCard);
        
        // Force reflow
        newCard.offsetHeight;
        
        // Re-enable transitions after a brief delay
        setTimeout(() => {
            newCard.style.transition = '';
        }, 50);
        
        // Update search context
        state.searchContext = JSON.stringify(data.school);
        
    } catch (error) {
        schoolCard.innerHTML = originalHTML + `<div class="error" style="margin-top: 12px;">Error loading details: ${error.message}</div>`;
        // Re-enable transitions
        setTimeout(() => {
            schoolCard.style.transition = '';
        }, 50);
    }
}

function toggleWatchlist(schoolName, schoolData) {
    const school = typeof schoolData === 'string' ? JSON.parse(schoolData.replace(/&quot;/g, '"')) : schoolData;
    const exists = state.watchlist.find(s => s.name === schoolName);
    
    if (exists) {
        removeFromWatchlist(schoolName);
    } else {
        addToWatchlist(school);
    }
    
    // Update button state without refreshing search
    const button = event.target;
    const isNowInWatchlist = state.watchlist.some(s => s.name === schoolName);
    button.textContent = isNowInWatchlist ? '✓' : '+';
    button.classList.toggle('added', isNowInWatchlist);
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    const chatMessages = document.getElementById('chatMessages');
    appendChatMessage('user', message);
    chatInput.value = '';
    
    appendChatMessage('assistant', '🤔 Thinking...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/schools/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                context: state.searchContext
            })
        });
        
        const data = await response.json();
        
        removeLastAssistantMessage();
        
        if (!data.success) {
            throw new Error(data.error || 'Chat failed');
        }
        
        appendChatMessage('assistant', data.response);
        
    } catch (error) {
        removeLastAssistantMessage();
        appendChatMessage('assistant', `Error: ${error.message}`);
    }
}

function appendChatMessage(role, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.innerHTML = `
        <strong>${role === 'user' ? '👤 You' : '🤖 Assistant'}</strong>
        <p>${content}</p>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLastAssistantMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const messages = chatMessages.querySelectorAll('.chat-message.assistant');
    if (messages.length > 0) {
        messages[messages.length - 1].remove();
    }
}

//===== APPLICATION SECTION =====
function setupApplicationSection() {
    const analyzeBtn = document.getElementById('analyzeQuestionBtn');
    analyzeBtn.addEventListener('click', analyzeAndGenerateResponse);
}

async function analyzeAndGenerateResponse() {
    if (!state.studentProfile) {
        alert('Please create a student profile first!');
        document.getElementById('manageProfileBtn').click();
        return;
    }
    
    const schoolSelect = document.getElementById('appSchoolSelect');
    const schoolName = schoolSelect.value;
    const question = document.getElementById('applicationQuestion').value.trim();
    
    if (!schoolName || !question) {
        alert('Please select a school and enter a question');
        return;
    }
    
    const schoolData = state.watchlist.find(s => s.name === schoolName);
    const schoolContext = JSON.stringify(schoolData);
    
    const responseArea = document.getElementById('applicationResponse');
    const analysisContent = document.getElementById('analysisContent');
    const generatedResponse = document.getElementById('generatedResponse');
    
    responseArea.classList.remove('hidden');
    analysisContent.innerHTML = '⏳ Analyzing question...';
    generatedResponse.innerHTML = '✍️ Generating response...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/application/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                school_name: schoolName,
                school_context: schoolContext,
                question: question,
                student_profile: state.studentProfile
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Analysis failed');
        }
        
        const analysis = data.analysis;
        
        // Display analysis
        let analysisHTML = '';
        if (analysis.analysis) {
            analysisHTML += `<p><strong>What this question is asking:</strong> ${analysis.analysis}</p>`;
        }
        if (analysis.key_points && analysis.key_points.length > 0) {
            analysisHTML += `<p><strong>Key points to address:</strong></p><ul style="margin-left: 20px;">`;
            analysis.key_points.forEach(point => {
                analysisHTML += `<li>${point}</li>`;
            });
            analysisHTML += `</ul>`;
        }
        analysisContent.innerHTML = analysisHTML || '<p>Analysis complete</p>';
        
        // Display generated response
        generatedResponse.innerHTML = analysis.suggested_response ? 
            analysis.suggested_response.replace(/\n\n/g, '</p><p>').replace(/^/, '<p>').replace(/$/, '</p>') : 
            'No response generated';
        
    } catch (error) {
        analysisContent.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        generatedResponse.innerHTML = '';
    }
}

function regenerateResponse() {
    analyzeAndGenerateResponse();
}

function copyResponse() {
    const response = document.getElementById('generatedResponse').innerText;
    navigator.clipboard.writeText(response).then(() => {
        alert('Response copied to clipboard! 📋');
    });
}

//===== INTERVIEW SECTION =====
function setupInterviewSection() {
    const generateBtn = document.getElementById('generateQuestionsBtn');
    const recordBtn = document.getElementById('recordBtn');
    const nextQuestionBtn = document.getElementById('nextQuestionBtn');
    
    generateBtn.addEventListener('click', generateInterviewQuestions);
    recordBtn.addEventListener('click', toggleRecording);
    nextQuestionBtn.addEventListener('click', loadNextQuestion);
}

async function generateInterviewQuestions() {
    if (!state.studentProfile) {
        alert('Please create a student profile first!');
        document.getElementById('manageProfileBtn').click();
        return;
    }
    
    const schoolSelect = document.getElementById('interviewSchoolSelect');
    const schoolName = schoolSelect.value;
    
    if (!schoolName) {
        alert('Please select a school');
        return;
    }
    
    const schoolData = state.watchlist.find(s => s.name === schoolName);
    const schoolContext = JSON.stringify(schoolData);
    
    const questionsContainer = document.getElementById('interviewQuestions');
    const questionsList = document.getElementById('questionsList');
    
    questionsContainer.classList.remove('hidden');
    questionsList.innerHTML = '<div class="loading">✨ Generating interview questions...</div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/interview/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                school_name: schoolName,
                school_context: schoolContext,
                student_profile: state.studentProfile
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Generation failed');
        }
        
        state.interviewQuestions = data.questions;
        state.currentQuestionIndex = 0;
        state.selectedSchool = schoolData;
        
        questionsList.innerHTML = '';
        data.questions.forEach((q, index) => {
            const item = document.createElement('div');
            item.className = 'question-item';
            item.innerHTML = `<strong>Q${index + 1} (${q.category || 'General'}):</strong> ${q.question}`;
            item.addEventListener('click', () => startPracticing(index));
            questionsList.appendChild(item);
        });
        
        document.getElementById('recordingArea').classList.remove('hidden');
        loadQuestion(0);
        
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
    document.getElementById('currentQuestion').textContent = question.question;
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
        
        const recordBtn = document.getElementById('recordBtn');
        recordBtn.classList.add('recording');
        recordBtn.querySelector('.record-icon').textContent = '⏹';
        recordBtn.querySelector('.record-label').textContent = 'Stop Recording';
        
        updateTimer();
        
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
    
    document.getElementById('recordTimer').textContent = 
        `${minutes}:${seconds.toString().padStart(2, '0')} / 1:00`;
    
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
    
    document.getElementById('transcriptionArea').classList.remove('hidden');
    document.getElementById('transcriptionText').textContent = '🎙️ Transcribing audio...';
    document.getElementById('feedbackContent').textContent = '⏳ Analyzing response...';
    
    try {
        // Create form data for audio upload
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'recording.webm');
        
        // Transcribe audio
        const transcribeResponse = await fetch(`${API_BASE_URL}/api/interview/transcribe`, {
            method: 'POST',
            body: formData
        });
        
        const transcribeData = await transcribeResponse.json();
        
        if (!transcribeData.success) {
            throw new Error(transcribeData.error || 'Transcription failed');
        }
        
        const transcription = transcribeData.transcription;
        document.getElementById('transcriptionText').textContent = transcription;
        
        // Get feedback
        const currentQuestion = state.interviewQuestions[state.currentQuestionIndex];
        const feedbackResponse = await fetch(`${API_BASE_URL}/api/interview/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: currentQuestion.question,
                school_context: JSON.stringify(state.selectedSchool),
                student_profile: state.studentProfile,
                transcription: transcription
            })
        });
        
        const feedbackData = await feedbackResponse.json();
        
        if (!feedbackData.success) {
            throw new Error(feedbackData.error || 'Feedback generation failed');
        }
        
        displayFeedback(feedbackData.feedback);
        
    } catch (error) {
        document.getElementById('transcriptionText').textContent = 'Error: ' + error.message;
        document.getElementById('feedbackContent').textContent = 'Could not generate feedback.';
    }
}

function displayFeedback(feedback) {
    let html = '';
    
    if (feedback.overall_score) {
        html += `<p><strong>Overall Score:</strong> ${feedback.overall_score}</p><hr style="margin: 12px 0; border: none; border-top: 1px solid rgba(102, 126, 234, 0.2);">`;
    }
    
    if (feedback.grammar) {
        html += `<p><strong>Grammar & Clarity (${feedback.grammar.score || 'N/A'}):</strong> ${feedback.grammar.feedback}</p>`;
    }
    
    if (feedback.relevance) {
        html += `<p><strong>Relevance to Question (${feedback.relevance.score || 'N/A'}):</strong> ${feedback.relevance.feedback}</p>`;
    }
    
    if (feedback.alignment) {
        html += `<p><strong>School Alignment (${feedback.alignment.score || 'N/A'}):</strong> ${feedback.alignment.feedback}</p>`;
    }
    
    if (feedback.strengths && feedback.strengths.length > 0) {
        html += `<p><strong>✅ Strengths:</strong></p><ul style="margin-left: 20px;">`;
        feedback.strengths.forEach(s => html += `<li>${s}</li>`);
        html += `</ul>`;
    }
    
    if (feedback.improvements && feedback.improvements.length > 0) {
        html += `<p><strong>📈 Areas for Improvement:</strong></p><ul style="margin-left: 20px;">`;
        feedback.improvements.forEach(i => html += `<li>${i}</li>`);
        html += `</ul>`;
    }
    
    if (feedback.suggestions && feedback.suggestions.length > 0) {
        html += `<p><strong>💡 Suggestions:</strong></p><ul style="margin-left: 20px;">`;
        feedback.suggestions.forEach(s => html += `<li>${s}</li>`);
        html += `</ul>`;
    }
    
    document.getElementById('feedbackContent').innerHTML = html || '<p>Feedback generated successfully.</p>';
}

// Expose functions to global scope for onclick handlers
window.closeProfileModal = closeProfileModal;
window.removeFromWatchlist = removeFromWatchlist;
window.toggleWatchlist = toggleWatchlist;
window.loadSchoolDetails = loadSchoolDetails;
window.regenerateResponse = regenerateResponse;
window.copyResponse = copyResponse;
