const API_BASE_URL = 'http://localhost:8000';

// Store chat sessions
let chats = [];
let currentChatId = null;
let isWaitingForResponse = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadChatsFromStorage();
    setupEventListeners();
    
    // If no chats exist, create a new one
    if (chats.length === 0) {
        createNewChat();
    } else {
        // Load the most recent chat
        loadChat(chats[0].id);
    }
});

function setupEventListeners() {
    const sendBtn = document.getElementById('sendBtn');
    const messageInput = document.getElementById('messageInput');
    const newChatBtn = document.getElementById('newChatBtn');
    
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = messageInput.scrollHeight + 'px';
    });
    
    newChatBtn.addEventListener('click', createNewChat);
    
    // Example query buttons
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('example-query')) {
            messageInput.value = e.target.textContent;
            sendMessage();
        }
    });
}

function createNewChat() {
    const chat = {
        id: Date.now().toString(),
        title: 'New Chat',
        messages: [],
        createdAt: new Date().toISOString()
    };
    
    chats.unshift(chat);
    saveChatsToStorage();
    loadChat(chat.id);
    renderChatHistory();
}

function loadChat(chatId) {
    currentChatId = chatId;
    const chat = chats.find(c => c.id === chatId);
    
    if (!chat) return;
    
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '';
    
    if (chat.messages.length === 0) {
        // Show welcome message
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <h2>👋 Welcome!</h2>
                <p>I'm an AI agent with access to:</p>
                <ul>
                    <li>🔍 Web search capabilities</li>
                    <li>📄 Page reading tools</li>
                    <li>🤔 Multi-step reasoning</li>
                </ul>
                <p>Try asking me something like:</p>
                <div class="example-queries">
                    <button class="example-query">Who won the Super Bowl?</button>
                    <button class="example-query">What's the weather in Paris?</button>
                    <button class="example-query">Latest Python release features</button>
                </div>
            </div>
        `;
    } else {
        // Render all messages
        chat.messages.forEach(msg => {
            appendMessage(msg.role, msg.content, false);
        });
    }
    
    renderChatHistory();
    scrollToBottom();
}

function renderChatHistory() {
    const chatHistory = document.getElementById('chatHistory');
    chatHistory.innerHTML = '';
    
    chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = 'history-item';
        if (chat.id === currentChatId) {
            item.classList.add('active');
        }
        
        const title = document.createElement('div');
        title.className = 'history-item-title';
        title.textContent = chat.title;
        
        const preview = document.createElement('div');
        preview.className = 'history-item-preview';
        if (chat.messages.length > 0) {
            preview.textContent = chat.messages[0].content.substring(0, 50) + '...';
        } else {
            preview.textContent = 'No messages yet';
        }
        
        item.appendChild(title);
        item.appendChild(preview);
        item.addEventListener('click', () => loadChat(chat.id));
        
        chatHistory.appendChild(item);
    });
}

async function sendMessage() {
    if (isWaitingForResponse) return;
    
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    // Add user message
    appendMessage('user', message);
    addMessageToCurrentChat('user', message);
    
    // Update chat title if this is the first message
    const chat = chats.find(c => c.id === currentChatId);
    if (chat && chat.messages.length === 1) {
        chat.title = message.substring(0, 50) + (message.length > 50 ? '...' : '');
        saveChatsToStorage();
        renderChatHistory();
    }
    
    // Show thinking animation
    showThinking();
    isWaitingForResponse = true;
    document.getElementById('sendBtn').disabled = true;
    
    try {
        // Call API
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_message: message
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        
        const data = await response.json();
        
        // Remove thinking animation
        hideThinking();
        
        // Add assistant message
        appendMessage('assistant', data.content);
        addMessageToCurrentChat('assistant', data.content);
        
    } catch (error) {
        hideThinking();
        appendMessage('assistant', `Sorry, I encountered an error: ${error.message}`);
        addMessageToCurrentChat('assistant', `Sorry, I encountered an error: ${error.message}`);
    } finally {
        isWaitingForResponse = false;
        document.getElementById('sendBtn').disabled = false;
        messageInput.focus();
    }
}

function appendMessage(role, content, shouldScroll = true) {
    const chatMessages = document.getElementById('chatMessages');
    
    // Remove welcome message if it exists
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    
    if (shouldScroll) {
        scrollToBottom();
    }
}

function showThinking() {
    const chatMessages = document.getElementById('chatMessages');
    
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message assistant thinking';
    thinkingDiv.id = 'thinkingMessage';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🤖';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `
        <span>Thinking</span>
        <div class="thinking-dots">
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
        </div>
    `;
    
    thinkingDiv.appendChild(avatar);
    thinkingDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(thinkingDiv);
    scrollToBottom();
}

function hideThinking() {
    const thinkingMessage = document.getElementById('thinkingMessage');
    if (thinkingMessage) {
        thinkingMessage.remove();
    }
}

function addMessageToCurrentChat(role, content) {
    const chat = chats.find(c => c.id === currentChatId);
    if (chat) {
        chat.messages.push({ role, content });
        saveChatsToStorage();
    }
}

function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function saveChatsToStorage() {
    localStorage.setItem('chats', JSON.stringify(chats));
}

function loadChatsFromStorage() {
    const stored = localStorage.getItem('chats');
    if (stored) {
        chats = JSON.parse(stored);
    }
}
