from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = "40628952"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'  # SQLite database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chat_id = db.Column(db.String(36), db.ForeignKey('chat.id'), nullable=False)  # Changed to use chat ID
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_deleted = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='sent')  # New status field: 'sent', 'delivered', 'read'
    read_at = db.Column(db.DateTime)  # Track when the message was read
    
    def __repr__(self):
        return f'<Message {self.id} from Chat {self.chat_id}>'

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    profile_picture = db.Column(db.String(200), nullable=True)  # New field for user profile picture
    status_message = db.Column(db.String(255), nullable=True)  # New field for user status message
    last_seen = db.Column(db.DateTime, nullable=True)  # New field for tracking last seen

# Chat model (direct or group)
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), default='direct')  # 'direct' or 'group'
    
    # Relationship to participants (users in the chat)
    participants = db.relationship('ChatParticipant', back_populates='chat', cascade='all, delete-orphan')
    
    def get_participants(self):
        return [participant.user for participant in self.participants]

# ChatParticipant model //TODO implement groupchat using this model
class ChatParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(36), db.ForeignKey('chat.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    chat = db.relationship('Chat', back_populates='participants')
    user = db.relationship('User')
    is_admin = db.Column(db.Boolean, default=False)  # For group chats, who is an admin?

# Blocked users model //TODO blocked users implementation
class BlockedUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blocked_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    blocker = db.relationship('User', foreign_keys=[blocker_id])
    blocked = db.relationship('User', foreign_keys=[blocked_id])

# Notification model //TODO push notifications from browser
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)  # Notification content
    read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create the database tables
with app.app_context():
    db.create_all()

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
    return render_template("index.html")  # Login/Register screen

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

@app.route('/get_messages/<chat_id>', methods=['GET'])
def get_messages(chat_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized access.'})

    user_uuid = session.get('uuid')
    user = User.query.filter_by(uuid=user_uuid).first()

    if not user:
        return jsonify({'success': False, 'message': 'User not found.'})

    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
    messages_data = [{
        'content': message.content,
        'sender_id': message.sender_id,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'status': message.status
    } for message in messages]

    return jsonify({'success': True, 'messages': messages_data})

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

    # Emit the message to all users in the chat room (broadcast=True)
    emit('receive_message', {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'chat_id': chat_id,
        'content': content,
        'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
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
