// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages = null;
let chatInput = null;
let sendButton = null;
let totalCourses = null;
let courseTitles = null;
let newChatButton = null;

// Initialize
document.addEventListener('DOMContentLoaded', initializeApp);

function initializeApp() {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');

    setupEventListeners();
    createNewSession();
    loadCourseStats();
}

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', handleEnterKey);
    newChatButton.addEventListener('click', handleNewChat);

    // Suggested questions
    const suggestedButtons = document.querySelectorAll('.suggested-item');
    suggestedButtons.forEach(button => {
        button.addEventListener('click', handleSuggestedQuestion);
    });
}

function handleEnterKey(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function handleSuggestedQuestion(event) {
    const question = event.target.getAttribute('data-question');
    chatInput.value = question;
    sendMessage();
}

function handleNewChat() {
    createNewSession();
    chatInput.focus();
}

// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    setInputState(false);
    chatInput.value = '';

    // Add user message
    addMessage(query, 'user');

    // Add loading message
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    scrollToBottom();

    try {
        const response = await queryAPI(query);
        handleQueryResponse(response, loadingMessage);
    } catch (error) {
        handleQueryError(error, loadingMessage);
    } finally {
        setInputState(true);
        chatInput.focus();
    }
}

function setInputState(enabled) {
    chatInput.disabled = !enabled;
    sendButton.disabled = !enabled;
}

async function queryAPI(query) {
    const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: query,
            session_id: currentSessionId
        })
    });

    if (!response.ok) {
        throw new Error('Query failed');
    }

    return response.json();
}

function handleQueryResponse(data, loadingMessage) {
    // Update session ID if new
    if (!currentSessionId) {
        currentSessionId = data.session_id;
    }

    // Replace loading message with response
    loadingMessage.remove();
    addMessage(data.answer, 'assistant', data.sources);
}

function handleQueryError(error, loadingMessage) {
    // Replace loading message with error
    loadingMessage.remove();
    addMessage(`Error: ${error.message}`, 'assistant');
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageDiv = createMessageElement(type, isWelcome);
    const displayContent = formatMessageContent(content, type);

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        html += createSourcesHtml(sources);
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function createMessageElement(type, isWelcome) {
    const messageDiv = document.createElement('div');
    const classes = ['message', type];
    if (isWelcome) {
        classes.push('welcome-message');
    }
    messageDiv.className = classes.join(' ');
    return messageDiv;
}

function formatMessageContent(content, type) {
    if (type === 'assistant') {
        return marked.parse(content);
    }
    return escapeHtml(content);
}

function createSourcesHtml(sources) {
    const sourceItems = sources.map(source => {
        if (source.url) {
            return `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer" class="source-pill">${escapeHtml(source.title)}</a>`;
        }
        return `<span class="source-pill source-pill--no-link">${escapeHtml(source.title)}</span>`;
    }).join('');

    return `
        <details class="sources-collapsible">
            <summary class="sources-header">Sources</summary>
            <div class="sources-list">${sourceItems}</div>
        </details>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';

    const welcomeMessage = 'Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?';
    addMessage(welcomeMessage, 'assistant', null, true);
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);

        if (!response.ok) {
            throw new Error('Failed to load course stats');
        }

        const data = await response.json();
        console.log('Course data received:', data);

        updateCourseStats(data);
    } catch (error) {
        console.error('Error loading course stats:', error);
        displayCourseStatsError();
    }
}

function updateCourseStats(data) {
    // Update total courses
    if (totalCourses) {
        totalCourses.textContent = data.total_courses;
    }

    // Update course titles
    if (!courseTitles) return;

    if (data.course_titles && data.course_titles.length > 0) {
        const titlesHtml = data.course_titles
            .map(title => `<div class="course-title-item">${title}</div>`)
            .join('');
        courseTitles.innerHTML = titlesHtml;
    } else {
        courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
    }
}

function displayCourseStatsError() {
    if (totalCourses) {
        totalCourses.textContent = '0';
    }
    if (courseTitles) {
        courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
    }
}