from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import logging
from models import db, Message, User, Chat, ChatParticipant, BlockedUser, Notification

app = Flask(__name__)
app.config['SECRET_KEY'] = "40628952"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'  # SQLite database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create the database tables
with app.app_context():
    db.create_all()

# User API
@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username} for user in users])

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    if user:
        return jsonify({'id': user.id, 'username': user.username})
    return jsonify({'error': 'User  not found'}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if register_user(username, password, email):
        return jsonify({'success': True, 'username': username}), 201
    return jsonify({'success': False, 'message': 'Username already exists.'}), 400

# Message API
@app.route('/api/messages/<int:chat_id>', methods=['GET'])
def get_chat_messages(chat_id):  # Renamed function to avoid conflict
    messages = Message.query.filter_by(chat_id=chat_id).all()
    return jsonify([{
        'id': message.id,
        'content': message.content,
        'sender_id': message.sender_id,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for message in messages])

@app.route('/api/messages', methods=['POST'])
def create_message():
    data = request.get_json()
    new_message = Message(
        sender_id=data['sender_id'],
        receiver_id=data['receiver_id'],
        chat_id=data['chat_id'],
        content=data['content']
    )
    db.session.add(new_message)
    db.session.commit()
    return jsonify({'success': True, 'message_id': new_message.id}), 201

# Existing route for getting messages (keep this if you need it)
@app.route('/get_messages/<chat_id>', methods=['GET'])
def get_messages(chat_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized access.'})

    user_uuid = session.get('uuid')
    user = User.query.filter_by(uuid=user_uuid).first()

    if not user:
        return jsonify({'success': False, 'message': 'User  not found.'})

    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
    messages_data = [{
        'content': message.content,
        'sender_id': message.sender_id,
        'timestamp': message.timestamp.strftime('%H:%M'),
        'status': message.status
    } for message in messages]

    return jsonify({'success': True, 'messages': messages_data})
# Chat API
@app.route('/api/chats', methods=['GET'])
def get_chats():
    chats = Chat.query.all()
    return jsonify([{'id': chat.id, 'user1_id': chat.user1_id, 'user2_id': chat.user2_id} for chat in chats])

@app.route('/api/chats', methods=['POST'])
def create_chat():
    data = request.get_json()
    new_chat = Chat(user1_id=data['user1_id'], user2_id=data['user2_id'])
    db.session.add(new_chat)
    db.session.commit()
    return jsonify({'success': True, 'chat_id': new_chat.id}), 201

# Register user function
def register_user(username, password, email=None):
    if User.query.filter_by(username=username).first():
        return False  # Check if username already exists
    
    user_uuid = str(uuid.uuid4())  # Generate a new UUID
    hashed_password = generate_password_hash(password)  # Hash the password
    new_user = User(username=username, uuid=user_uuid, password=hashed_password, email=email) # Populate new user with data
    
    db.session.add(new_user)
    db.session.commit()  # Save the new user to the database
    return True

@app.route('/')
def index():
    return render_template("index.html")  # Login

@app.route('/signup')
def signup():
    return render_template("signup.html")  # Sign Up

@app.route('/chats')
def chats():
    if 'username' in session:
        user_uuid = session.get('uuid')
        return render_template("chats.html", user_uuid=user_uuid)
    return redirect(url_for('index')) # redirect user to login screen if not logged in


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if register_user(username, password, email):
        return jsonify({'success': True, 'username': username})
    else:
        return jsonify({'success': False, 'message': 'Username already exists.'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session['uuid'] = user.uuid  # Store UUID instead of just username
        session['username'] = username  # keep username in session
        return jsonify({'success': True, 'redirect': url_for('chats')})
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password.'})


@app.route('/logout')
def logout():
    session.pop('username', None)
    return jsonify({'success': True})

@app.route('/add_contact', methods=['POST'])
def add_contact():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'User not logged in.'})

    data = request.get_json()
    contact_username = data.get('username')

    logged_in_user = User.query.filter_by(username=session['username']).first()
    contact_user = User.query.filter_by(username=contact_username).first()

    if not contact_user:
        return jsonify({'success': False, 'message': 'User not found.'})

    if logged_in_user.username == contact_username:
        return jsonify({'success': False, 'message': 'You cannot add yourself as a contact.'})

    # Grouping conditions in chat existence query
    existing_chat = Chat.query.filter(
        ((Chat.user1_id == logged_in_user.id) & (Chat.user2_id == contact_user.id)) |
        ((Chat.user1_id == contact_user.id) & (Chat.user2_id == logged_in_user.id))
    ).first()


    if existing_chat:
        return jsonify({'success': False, 'message': 'This user is already your contact.'})

    # Create a new chat and assign user1_id and user2_id
    new_chat = Chat(user1_id=logged_in_user.id, user2_id=contact_user.id, type='direct')
    db.session.add(new_chat)
    db.session.commit()

    # Add participants to the chat (ChatParticipant)
    new_participant_1 = ChatParticipant(chat_id=new_chat.id, user_id=logged_in_user.id)
    new_participant_2 = ChatParticipant(chat_id=new_chat.id, user_id=contact_user.id)
    db.session.add(new_participant_1)
    db.session.add(new_participant_2)
    db.session.commit()

    return jsonify({'success': True, 'chat_id': new_chat.id, 'message': 'Contact added successfully.'})

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'User not logged in.'})

    #find user by username in database (User)
    logged_in_user = User.query.filter_by(username=session['username']).first()

    #create chat between users
    contacts = Chat.query.join(ChatParticipant).filter(ChatParticipant.user_id == logged_in_user.id).all()

    #init empty list
    contact_details = []
    
    for chat in contacts:
        #find other participants
        other_participant = [participant for participant in chat.participants if participant.user_id != logged_in_user.id]
        
        #get the other user
        other_user = other_participant[0].user if other_participant else None
        
        #append contact details
        if other_user:
            contact_details.append({
                'chat_id': chat.id,
                'chat_name': other_user.username  # Use the username of the other user
            })

    return jsonify({'success': True, 'contacts': contact_details})


#unuique room assignment
@socketio.on('connect')
def handle_connect():
    user_uuid = session.get('uuid')
    if user_uuid:
        join_room(user_uuid)  # Assign user to their unique room
        emit('user_connected', {'uuid': user_uuid}, room=user_uuid)

@socketio.on('disconnect')
def handle_disconnect():
    user_uuid = session.get('uuid')
    if user_uuid:
        leave_room(user_uuid)  # Remove user from their room


@socketio.on('send_message')
def handle_send_message(data):
    chat_id = data['chat_id']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']  # Get the receiver_id from the data
    content = data['content']

    # Save the message in the database
    new_message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,  # Set the receiver_id
        chat_id=chat_id,
        content=content
    )
    db.session.add(new_message)
    db.session.commit()
    
    timestamp_display = new_message.timestamp.strftime('%H:%M')

    # Emit the message to all users in the chat room
    emit('receive_message', {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'chat_id': chat_id,
        'content': content,
        'timestamp': timestamp_display,  # Only display hh:mm
        'status': new_message.status
    }, room=chat_id)


@socketio.on('join_chat')
def handle_join_chat(data):
    chat_id = data['chat_id']
    user_uuid = session.get('uuid')
    if user_uuid:
        join_room(chat_id)  # Join the chat room based on chat_id
        emit('user_connected', {'uuid': user_uuid}, room=chat_id)

if __name__ == '__main__':
    app.run(debug=True)
