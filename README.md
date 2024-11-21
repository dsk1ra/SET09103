# Chat Application

This is my version of a real-time web messager I built using Flask. It allows users to log in/ register, create chats between users and chat in real time.
## Features

- User authentication (login and registration)
- Real-time messaging using WebSockets
- Dynamic message updating in the chat interface
- User-friendly interface for sending and receiving messages

## Technologies Used

- HTML
- CSS
- JavaScript
- jQuery
- WebSockets (Socket.io)

## Getting Started

### Prerequisites

- [Python](https://www.python.org/downloads/) installed on your machine.
- `pip` for installing Python packages.

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/dsk1ra/SET09103.git
   cd SET09103
   

2. Install the required dependencies:

  ```bash
  pip install -r requirements.txt

3. Start the server:

    ```bash
    python -m flask --app ./app.py run

4. Open preferred browser and go to `localhost:5000`

### Usage
1. **Register a New User**: Enter preferred username and password, then click `Register`"
2. **Login**: Enter your username and password, then click `Login`
3. **Create a New Chat**: Click `Add Contact` and enter the username of the user
4. **Send a Message**: Type your message in the input field and click `Send`
5. **View Messages**: Messages will be displayed in real-time in the chat interface
6. **Logout**: Click `Logout` to log out of your account


### License 
Distributed under the MIT License. See LICENSE.txt for more information.
