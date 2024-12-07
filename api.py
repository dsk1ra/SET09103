from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from models import db, Message, User, Chat, ChatParticipant, BlockedUser, Notification

api = Blueprint('api', __name__)

@api.route('/get_messages/<chat_id>', methods=['GET'])
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
        'timestamp': message.timestamp.strftime('%H:%M'),
        'status': message.status
    } for message in messages]

    return jsonify({'success': True, 'messages': messages_data})

def register_user(username, password, email=None):
    if User.query.filter_by(username=username).first():
        return False  # Check if username already exists
    
    user_uuid = str(uuid.uuid4())  # Generate a new UUID
    hashed_password = generate_password_hash(password)  # Hash the password
    new_user = User(username=username, uuid=user_uuid, password=hashed_password, email=email) # Populate new user with data
    
    db.session.add(new_user)
    db.session.commit()  # Save the new user to the database
    return True

@api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if register_user(username, password, email):
        return jsonify({'success': True, 'username': username})
    else:
        return jsonify({'success': False, 'message': 'Username already exists.'})

@api.route('/login', methods=['POST'])
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

@api.route('/logout')
def logout():
    session.pop('username', None)
    return jsonify({'success': True})

@api.route('/add_contact', methods=['POST'])
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

    existing_chat = Chat.query.filter(
        ((Chat.user1_id == logged_in_user.id) & (Chat.user2_id == contact_user.id)) |
        ((Chat.user1_id == contact_user.id) & (Chat.user2_id == logged_in_user.id))
    ).first()

    if existing_chat:
        return jsonify({'success': False, 'message': 'This user is already your contact.'})

    new_chat = Chat(user1_id=logged_in_user.id, user2_id=contact_user.id, type='direct')
    db.session.add(new_chat)
    db.session.commit()

    new_participant_1 = ChatParticipant(chat_id=new_chat.id, user_id=logged_in_user.id)
    new_participant_2 = ChatParticipant(chat_id=new_chat.id, user_id=contact_user.id)
    db.session.add(new_participant_1)
    db.session.add(new_participant_2)
    db.session.commit()

    return jsonify({'success': True, 'chat_id': new_chat.id, 'message': 'Contact added successfully.'})

@api.route('/get_contacts', methods=['GET'])
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
                'chat_name': other_user.username
            })

    return jsonify({'success': True, 'contacts': contact_details})
