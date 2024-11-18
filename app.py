from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = "hello"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'  # Use SQLite for simplicity
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

# Chat model (for direct or group chats)
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), default='direct')  # 'direct' or 'group'
    
    # Relationship to participants (users in the chat)
    participants = db.relationship('ChatParticipant', back_populates='chat', cascade='all, delete-orphan')
    
    def get_participants(self):
        return [participant.user for participant in self.participants]

# ChatParticipant model (to support multiple participants in group chats)
class ChatParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(36), db.ForeignKey('chat.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    chat = db.relationship('Chat', back_populates='participants')
    user = db.relationship('User')
    is_admin = db.Column(db.Boolean, default=False)  # For group chats, who is an admin?

# A new table to store information about blocked users (optional)
class BlockedUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blocked_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blocked_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    blocker = db.relationship('User', foreign_keys=[blocker_id])
    blocked = db.relationship('User', foreign_keys=[blocked_id])

# For notifications (optional)
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
        return False  # Username already exists
    
    user_uuid = str(uuid.uuid4())  # Generate a new UUID
    hashed_password = generate_password_hash(password)  # Hash the password
    new_user = User(username=username, uuid=user_uuid, password=hashed_password, email=email)
    
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
    return redirect(url_for('index'))


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
        session['username'] = username  # Optional: keep username in session
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

    # Fix for grouping conditions in chat existence query
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

    # Add participants to the chat (ChatParticipant table)
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

    logged_in_user = User.query.filter_by(username=session['username']).first()

    contacts = Chat.query.join(ChatParticipant).filter(ChatParticipant.user_id == logged_in_user.id).all()

    contact_details = []
    for chat in contacts:
        other_participant = [participant for participant in chat.participants if participant.user_id != logged_in_user.id]
        other_user = other_participant[0].user if other_participant else None
        
        if other_user:
            contact_details.append({
                'chat_id': chat.id,
                'chat_name': other_user.username  # Use the username of the other user
            })

    return jsonify({'success': True, 'contacts': contact_details})

@app.route('/get_messages/<string:chat_id>', methods=['GET'])
def get_messages(chat_id):
    try:
        messages = Message.query.filter_by(chat_id=chat_id, is_deleted=False).order_by(Message.timestamp).all()
        messages_data = [
            {
                "id": message.id,
                "sender_id": message.sender_id,
                "content": message.content,
                "timestamp": message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "status": message.status,  # Include message status
                "read_at": message.read_at.strftime('%Y-%m-%d %H:%M:%S') if message.read_at else None
            }
            for message in messages
        ]
        return jsonify({"success": True, "messages": messages_data})
    except Exception as e:
        app.logger.error(f"Error retrieving messages: {str(e)}")
        return jsonify({"success": False, "message": "Failed to retrieve messages."})

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
    try:
        chat_id = data['chat_id']
        sender_id = data['sender_id']
        receiver_id = data['receiver_id']
        content = data['content']
        
        new_message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            chat_id=chat_id,
            content=content
        )

        db.session.add(new_message)
        db.session.commit()

        # Emit to the respective chat room
        emit('receive_message', {
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'chat_id': chat_id,
            'content': content,
            'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'status': new_message.status
        }, room=chat_id)  # Room per chat_id
    except Exception as e:
        app.logger.error(f"Error sending message: {str(e)}")



if __name__ == '__main__':
    app.run(debug=True)
