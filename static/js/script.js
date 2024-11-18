const socket = io();
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const usernameDisplay = document.getElementById('username-display');
const contactsList = document.getElementById('contacts-list');
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendMessageBtn = document.getElementById('send-message-btn');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const addContactUsername = document.getElementById('add-contact-username');
const addContactBtn = document.getElementById('add-contact-btn');
const addContactError = document.getElementById('add-contact-error');
const chatArea = document.getElementById('chat-area');

// Handle Login
loginForm.addEventListener('submit', function (event) {
    event.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    fetch('/login', {
        method: 'POST',
        body: new URLSearchParams({ username, password })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loginScreen.style.display = 'none';
                chatScreen.style.display = 'block';
                usernameDisplay.textContent = data.username;
                socket.emit('user_connected', data.username);
            } else {
                document.getElementById('login-error-message').textContent = data.message;
            }
        });
    fetch(`/get_contacts?user_id=${currentUserId}`)
        .then(response => response.json())
        .then(data => {
            data.contacts.forEach(contact => {
                const contactElement = document.createElement('li');
                contactElement.innerText = contact.username;
                contactList.appendChild(contactElement);
            });
        });

});

// Handle Registration
registerForm.addEventListener('submit', function (event) {
    event.preventDefault();
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;

    fetch('/register', {
        method: 'POST',
        body: new URLSearchParams({ username, password })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loginScreen.style.display = 'none';
                chatScreen.style.display = 'block';
                usernameDisplay.textContent = data.username;
                socket.emit('user_connected', data.username);
            } else {
                document.getElementById('register-error-message').textContent = data.message;
            }
        });
});

// Add Contact
addContactBtn.addEventListener('click', function () {
    const usernameToAdd = addContactUsername.value;
    socket.emit('find_contact', { username: usernameToAdd });
});

// Contact Found
socket.on('contact_found', function (data) {
    const contactElement = document.createElement('li');
    contactElement.textContent = data.username;
    contactElement.dataset.contactId = data.user_id;
    contactElement.classList.add('contact');
    contactsList.querySelector('ul').appendChild(contactElement);
    addContactUsername.value = '';
    addContactError.textContent = '';
});

// Contact Not Found
socket.on('contact_not_found', function (message) {
    addContactError.textContent = message;
});

// Load Chat with Selected Contact
contactsList.addEventListener('click', function (event) {
    if (event.target.classList.contains('contact')) {
        const contactId = event.target.dataset.contactId;
        socket.emit('load_chat_history', { contactId: contactId });
        chatArea.style.display = 'block';
        messageInput.disabled = false;
        sendMessageBtn.disabled = false;
    }
});

// Receive and Display Chat History
socket.on('chat_history', function (messages) {
    messagesDiv.innerHTML = '';
    messages.forEach((msg) => {
        const messageElement = document.createElement('div');
        messageElement.textContent = msg;
        messagesDiv.appendChild(messageElement);
    });
});

// Send and Receive Messages
sendMessageBtn.addEventListener('click', function () {
    const message = messageInput.value;
    socket.emit('message', { message: message });
    messageInput.value = '';
});

socket.on('message', function (data) {
    const messageElement = document.createElement('div');
    messageElement.textContent = data.message;
    messagesDiv.appendChild(messageElement);
});
