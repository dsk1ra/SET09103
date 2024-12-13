
document.addEventListener("DOMContentLoaded", () => {
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    const addContactBtn = document.getElementById('add-contact-btn');
    const createGroupBtn = document.getElementById('create-group-btn');
    const logoutBtn = document.getElementById('logout-slide-btn');
    const sendBtn = document.getElementById('send-btn');
    const addContactPopup = document.getElementById('add-contact-popup');
    const createGroupPopup = document.getElementById('create-group-popup');
    const confirmAddContactBtn = document.getElementById('confirm-add-contact-btn');
    const confirmCreateGroupBtn = document.getElementById('confirm-create-group-btn');
    const cancelAddContactBtn = document.getElementById('cancel-add-contact-btn');
    const cancelCreateGroupBtn = document.getElementById('cancel-create-group-btn');
    const addUserToGroupBtn = document.getElementById('add-user-to-group-btn');
    const groupUsersList = document.getElementById('group-users-list');
    const contactList = document.getElementById('contact-list');
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const contactName = document.getElementById('contact-name');
    const popupOverlay = document.getElementById('popup-overlay');

    // Toggle slide menu functionality
    const slideMenu = document.querySelector('.slide-menu');
    const toggleButton = document.getElementById('toggle-slide-menu');
    const closeButton = document.getElementById('close-slide-menu');
    const container = document.querySelector('.container');

    const usernameSpan = document.getElementById('username');
    usernameSpan.innerText = loggedInUsername;

    let activeContactId = null;
    let activeContactName = null;
    let groupUsers = [];

    messageInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            if (event.shiftKey) {
                // If Shift + Enter is pressed, add a newline
                messageInput.value += '\n'; // Add a newline character
                event.preventDefault(); // Prevent default action
            } else {
                // If only Enter is pressed, prevent the default action and trigger send
                event.preventDefault(); // Prevent the default form submission
                sendBtn.click(); // Trigger the send button click
            }
        }
    });
    messageInput.addEventListener('input', function () {
        this.style.height = 'auto'; // Reset height
        this.style.height = Math.min(this.scrollHeight, 60) + 'px'; // Set height to scrollHeight, max 120px (3 rows)
    });

    // Function to hide all overlays
    function hideAllOverlays() {
        addContactPopup.classList.remove('show');
        createGroupPopup.classList.remove('show');
    }

    // Show add contact popup
    addContactBtn.addEventListener("click", () => {
        hideAllOverlays();
        addContactPopup.classList.add('show');
    });

    // Hide add contact popup
    cancelAddContactBtn.addEventListener("click", () => {
        addContactPopup.classList.remove('show');
    });

    // Show create group popup
    createGroupBtn.addEventListener("click", () => {
        hideAllOverlays();
        createGroupPopup.classList.add('show');
    });

    // Hide create group popup
    cancelCreateGroupBtn.addEventListener("click", () => {
        createGroupPopup.classList.remove('show');
        groupUsers = [];
        groupUsersList.innerHTML = '';
    });

    addUserToGroupBtn.addEventListener("click", () => {
        const username = document.getElementById('group-user-username').value.trim();
        if (username && !groupUsers.includes(username)) {
            groupUsers.push(username);
            const listItem = document.createElement('li');
            listItem.innerText = username;
            groupUsersList.appendChild(listItem);
            document.getElementById('group-user-username').value = '';
        }
    });

    // Confirm add contact
    confirmAddContactBtn.addEventListener("click", () => {
        const contactUsername = document.getElementById('contact-username').value.trim();
        if (contactUsername) {
            fetch('/api/v1/contacts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: contactUsername })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        fetchContacts(); // Refresh contact list
                        addContactPopup.classList.remove('show');
                    } else {
                        alert(data.message);
                    }
                })
                .catch(err => console.error("Error adding contact:", err));
        }
    });

    // Confirm create group
    confirmCreateGroupBtn.addEventListener("click", () => {
        const groupName = document.getElementById('group-name').value.trim();
        if (groupName && groupUsers.length > 0) {
            fetch('/api/v1/group_chats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: groupName, users: groupUsers })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        fetchContacts(); // Refresh contact list
                        createGroupPopup.classList.remove('show');
                        groupUsers = [];
                        groupUsersList.innerHTML = '';
                    } else {
                        alert(data.message);
                    }
                })
                .catch(err => console.error("Error creating group chat:", err));
        }
    });

    const chatInfo = document.getElementById('chat-info');

    function updateChatHeader(chat) {
        if (chat.type === 'group') {
            contactName.innerText = chat.name;
            chatInfo.innerText = 'Group Chat';
        } else {
            contactName.innerText = chat.name;
            chatInfo.innerText = '';
        }
    }

    function selectChat(chatId) {
        fetch(`/api/v1/chats/${chatId}`)
            .then(response => response.json())
            .then(chat => {
                updateChatHeader(chat);
                // Load chat messages and other logic
            })
            .catch(err => console.error("Error fetching chat:", err));
    }

    // Add event listeners to chat elements
    document.querySelectorAll('.chat-info').forEach(item => {
        item.addEventListener('click', () => {
            const chatId = item.getAttribute('data-chat-id');
            selectChat(chatId);
        });
    });

    // Update contact list
    function fetchContacts() {
        fetch('/api/v1/contacts')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateContactList(data.contacts);
                } else {
                    alert("Error loading contacts.");
                }
            })
            .catch(err => console.error("Error fetching contacts:", err));
    }

    function updateContactList(contacts) {
        const contactList = document.getElementById('contact-list');
        contactList.innerHTML = ''; // Clear existing list
        contacts.forEach(contact => {
            const contactItem = document.createElement('div');
            contactItem.classList.add('contact-item', 'flex');
            contactItem.dataset.chatId = contact.chat_id; // Set the chat ID

            // Add profile picture
            const profilePicture = document.createElement('img');
            profilePicture.classList.add('profile-picture');
            profilePicture.src = contact.profile_picture ? `data:image/png;base64,${contact.profile_picture}` : 'static/images/placeholder.png';
            profilePicture.alt = 'Profile Picture';
            profilePicture.width = 20;
            profilePicture.height = 20;

            // Add chat-info container
            const chatInfo = document.createElement('div');
            chatInfo.classList.add('chat-info');

            // Add contact name (h4)
            const contactName = document.createElement('h4');
            contactName.innerText = contact.chat_name;

            // Add latest message (h5)
            const latestMessage = document.createElement('h5');
            latestMessage.innerText = truncateMessage(contact.latest_message || 'No messages yet');

            // Add timestamp (span)
            const timestamp = document.createElement('span');
            timestamp.classList.add('timestamp'); // Add a class for styling
            timestamp.innerText = contact.latest_message_timestamp || ''; // Use the timestamp if available

            // Append elements to chat-info
            chatInfo.appendChild(contactName);
            chatInfo.appendChild(latestMessage);
            chatInfo.appendChild(timestamp); // Append the timestamp

            // Append elements to contact-item
            contactItem.appendChild(profilePicture);
            contactItem.appendChild(chatInfo);

            // Add click event to load chat
            contactItem.addEventListener('click', () => {
                loadChat(contact.chat_id, contact.chat_name);
            });

            contactList.appendChild(contactItem);
        });
    }

    function truncateMessage(message) {
        if (message.length > 15) {
            return message.substring(0, 15) + "..."; // Truncate and add "..."
        }
        return message; // Return the original message if it's within the limit
    }

    socket.on('update_contact_list', (data) => {
        const contactList = document.getElementById('contact-list');
        const contactItems = contactList.getElementsByClassName('contact-item');

        let contactUpdated = false;

        // Check if the chat already exists in the contact list
        for (let contactItem of contactItems) {
            const chatId = contactItem.dataset.chatId; // Assuming you store chat_id in a data attribute
            if (chatId === data.chat_id.toString()) {
                // Update the latest message
                const latestMessage = contactItem.querySelector('h5');
                latestMessage.innerText = data.latest_message;
                contactUpdated = true;

                // Optionally, move the updated contact to the top of the list
                contactList.prepend(contactItem);
                break;
            }
        }

        // If the chat is not in the list, add it (optional, for new chats)
        if (!contactUpdated) {
            const newContactItem = document.createElement('div');
            newContactItem.classList.add('contact-item', 'flex');
            newContactItem.dataset.chatId = data.chat_id;

            const chatInfo = `
            <h4>${data.chat_name}</h4>
            <h5>${data.latest_message}</h5>
        `;
            newContactItem.innerHTML = chatInfo;

            contactList.prepend(newContactItem);

            // Add event listener for loading the chat
            newContactItem.addEventListener('click', () => {
                loadChat(data.chat_id, data.chat_name);
            });
        }
    });

    // Load chat messages
    function loadChat(contactId, contactUsername, chatType) {
        activeContactId = contactId;
        activeContactName = contactUsername;

        contactName.innerText = contactUsername; // Update chat header
        chatMessages.innerHTML = ''; // Clear existing messages

        // Join the selected chat room
        socket.emit('join_chat', { chat_id: contactId });

        // Fetch previous chat messages
        fetch(`/api/v1/messages/${contactId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    data.messages.forEach(message => {
                        const senderType = message.sender_id === loggedInUserId ? 'self' : 'other';
                        displayMessage(message.content, senderType, message.timestamp, message.status, message.id);
                    });
                }
            })
            .catch(err => console.error("Error fetching messages:", err));
    }

    // Display a single message in the chat
    function displayMessage(message, senderType, timestamp, status, messageId) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', senderType === "self" ? 'self-message' : 'other-message');
        messageDiv.id = `message-${messageId}`;

        const timestampDiv = document.createElement('span');
        timestampDiv.classList.add('timestamp');
        timestampDiv.innerText = timestamp;

        const statusDiv = document.createElement('span');
        statusDiv.classList.add('status');
        statusDiv.innerText = status; // e.g., "sent", "read"

        messageDiv.innerHTML = `${message} <div>${timestampDiv.outerHTML} ${statusDiv.outerHTML}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the latest message

        // Mark message as read if it's from the other user
        if (senderType === "other" && status !== "read") {
            fetch('/api/v1/messages/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_id: messageId })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusDiv.innerText = 'read';
                        // Emit status update to WebSocket server
                        socket.emit('status_update', { messageId: messageId, status: 'read' });
                    }
                })
                .catch(err => console.error("Error marking message as read:", err));
        }
    }

    // Send message
    sendBtn.addEventListener("click", () => {
        const message = messageInput.value.trim();
        if (message && activeContactId) {
            fetch('/api/v1/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: activeContactId,
                    sender_id: loggedInUserId,
                    content: message
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        displayMessage(data.content, 'self', data.timestamp, data.status, data.id);
                        messageInput.value = '';
                        messageInput.style.height = 'auto'; // Reset height
                    }
                })
                .catch(err => console.error("Error sending message:", err));
            socket.emit('send_message', {
                chat_id: activeContactId,
                sender_id: loggedInUserId,
                content: message
            });
        }
    });

    socket.on('update_contact_item', (data) => {
        const contactList = document.getElementById('contact-list');
        const contactItems = contactList.getElementsByClassName('contact-item');

        // Loop through contact items to find the one that matches the chat_id
        for (let contactItem of contactItems) {
            if (contactItem.dataset.chatId === data.chat_id.toString()) {
                // Update the latest message with truncation
                const latestMessage = contactItem.querySelector('h5');
                latestMessage.innerText = truncateMessage(data.latest_message);

                // Optionally, you can move the updated contact to the top of the list
                contactList.prepend(contactItem);
                break;
            }
        }
    });

    // Listen for incoming messages
    socket.on('receive_message', (data) => {
        // Display the message if it's from the active contact
        if (data.chat_id === activeContactId) {
            if (data.sender_id !== loggedInUserId) { // Only display if it's not from the current user
                displayMessage(data.content, "other", data.timestamp, data.status, data.message_id);
            } else {
                displayMessage(data.content, "self", data.timestamp, data.status, data.message_id);
            }
        }

        // Update the contact item for all users
        const contactList = document.getElementById('contact-list');
        const contactItems = contactList.getElementsByClassName('contact-item');

        // Loop through contact items to find the one that matches the chat_id
        for (let contactItem of contactItems) {
            if (contactItem.dataset.chatId === data.chat_id.toString()) {
                // Update the latest message
                const latestMessage = contactItem.querySelector('h5');
                latestMessage.innerText = data.content; // Update to the latest message
                break;
            }
        }
        messageInput.value = '';
    });

    // Logout functionality
    logoutBtn.addEventListener("click", () => {
        fetch('/api/v1/sessions', {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/';
                }
            })
            .catch(err => console.error("Error logging out:", err));
    });

    // Toggle slide menu
    toggleButton.addEventListener('click', () => {
        const isActive = slideMenu.classList.contains('active');
        slideMenu.classList.toggle('active', !isActive);
        //container.classList.toggle('blur', !isActive);
    });

    // Close slide menu
    closeButton.addEventListener('click', () => {
        slideMenu.classList.remove('active');
        //container.classList.remove('blur');
    });

    // Load contacts on page load
    fetchContacts();

    // Show create group popup
    createGroupBtn.addEventListener("click", () => {
        hideAllOverlays();
        createGroupPopup.classList.add('show');
    });

    // Hide create group popup
    cancelCreateGroupBtn.addEventListener("click", () => {
        createGroupPopup.classList.remove('show');
        groupUsers = [];
        groupUsersList.innerHTML = '';
    });


    // Confirm create group
    confirmCreateGroupBtn.addEventListener("click", () => {
        const groupName = document.getElementById('group-name').value.trim();
        if (groupName && groupUsers.length > 0) {
            fetch('/api/v1/create_group', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ group_name: groupName, usernames: groupUsers })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        fetchContacts(); // Refresh contact list
                        createGroupPopup.classList.remove('show');
                        groupUsers = [];
                        groupUsersList.innerHTML = '';
                    } else {
                        alert(data.message);
                    }
                })
                .catch(err => console.error("Error creating group:", err));
        }
    });

    const settingsBtn = document.getElementById('settings-btn');
    const settingsOverlay = document.getElementById('settings-overlay');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const profilePictureForm = document.getElementById('profile-picture-form');
    const profilePictureInput = document.getElementById('profile-picture-input');
    const profilePicture = document.getElementById('profile-picture');

    settingsBtn.addEventListener('click', () => {
        settingsOverlay.style.display = 'flex';
    });

    closeSettingsBtn.addEventListener('click', () => {
        settingsOverlay.style.display = 'none';
    });
    function appendMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        messageElement.innerHTML = `
            <div class="message-content">${message.content}</div>
            <div class="message-timestamp">${message.timestamp}</div>
        `;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
    }
    profilePictureForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const file = profilePictureInput.files[0];
        if (file && file.size <= 1048576) { // 1MB = 1048576 bytes
            const formData = new FormData();
            formData.append('profile_picture', file);

            fetch('/api/v1/upload_profile_picture', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Profile picture uploaded successfully!');
                        profilePicture.src = data.profile_picture_url; // Update the profile picture in the UI
                        settingsOverlay.style.display = 'none';
                    } else {
                        alert(data.message);
                    }
                })
                .catch(err => console.error('Error uploading profile picture:', err));
        } else {
            alert('File size exceeds 1MB limit.');
        }
    });

    socket.on('update_profile_picture', (data) => {
        const { user_uuid, profile_picture } = data;
        if (user_uuid === loggedInUserId) {
            const profilePicture = document.getElementById('profile-picture');
            profilePicture.src = `data:image/png;base64,${profile_picture}`;
        }
    });

    // Fetch and display the profile picture
    function fetchProfilePicture() {
        fetch('/api/v1/profile_picture')
            .then(response => response.json())
            .then(data => {
                const profilePicture = document.getElementById('profile-picture');
                if (data.success && data.profile_picture) {
                    profilePicture.src = `data:image/png;base64,${data.profile_picture}`;
                } else {
                    profilePicture.src = 'static/images/placeholder.png'; // Default profile picture
                }
            })
            .catch(err => {
                console.error('Error fetching profile picture:', err);
                const profilePicture = document.getElementById('profile-picture');
                profilePicture.src = 'static/images/placeholder.png'; // Default profile picture on error
            });
    }

    // Call the function to fetch the profile picture on page load
    fetchProfilePicture();

    const searchContactsInput = document.getElementById('search-contacts');

    // Filter contacts based on search input
    searchContactsInput.addEventListener('input', function () {
        const searchTerm = this.value.toLowerCase();
        const contactItems = document.querySelectorAll('.contact-item');

        contactItems.forEach(contactItem => {
            const contactName = contactItem.querySelector('h4').innerText.toLowerCase();
            if (contactName.includes(searchTerm)) {
                contactItem.style.display = 'flex'; // Show matching contact
            } else {
                contactItem.style.display = 'none'; // Hide non-matching contact
            }
        });
    });
    const customFileUploadLabel = document.querySelector('.custom-file-upload');

    customFileUploadLabel.addEventListener('click', () => {
        profilePictureInput();
    });
    const profilePicturePreview = document.getElementById('profile-picture-preview');

    profilePictureInput.addEventListener('change', () => {
        const file = profilePictureInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                profilePicturePreview.src = e.target.result;
                profilePicturePreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            profilePicturePreview.src = '';
            profilePicturePreview.style.display = 'none';
        }
    });


});

$(document).ready(function () {
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

    // Refresh messages dynamically using AJAX
    function fetchMessages(chatId) {
        $.ajax({
            url: `/api/get_messages/${chatId}`,  // Updated endpoint
            type: "GET",
            success: function (data) {
                if (data.success) {
                    updateMessages(data.messages);
                }
            },
            error: function () {
                alert("Failed to fetch messages.");
            }
        });
    }

    // Update messages dynamically in the DOM
    function updateMessages(messages) {
        const chatMessages = $('#chat-messages');
        chatMessages.empty(); // Clear current messages
        messages.forEach(msg => {
            const senderType = msg.sender_id === loggedInUserId ? 'self' : 'other';
            const messageElement = `
                <div class="message ${senderType}-message">
                    <p>${msg.content}</p>
                    <span class="timestamp">${msg.timestamp}</span>
                </div>`;
            chatMessages.append(messageElement);
        });
    }

    // Send a new message
    $('#send-btn').on('click', function () {
        const messageInput = $('#message-input');
        const message = messageInput.val().trim();
        if (message && activeContactId) {
            socket.emit('send_message', {
                chat_id: activeContactId,
                content: message,
                sender_id: loggedInUserId
            });

            messageInput.val(''); // Clear input field
        }
        // Emit an event to update the contact list
        socket.emit('update_contact_list', {
            chat_id: activeContactId,
            latest_message: message,
            chat_name: activeContactName
        });
    });

});