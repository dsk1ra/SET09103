from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
from models import db, Message, User, Chat, ChatParticipant, BlockedUser, Notification
import base64


api = Blueprint('api', __name__, url_prefix='/api/v1')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@api.route('/messages/<int:chat_id>', methods=['GET'])
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

@api.route('/users', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if register_user(username, password, email):
        return jsonify({'success': True, 'username': username})
    else:
        return jsonify({'success': False, 'message': 'Username already exists.'})
    
@api.route('/sessions', methods=['POST'])
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

@api.route('/sessions', methods=['DELETE'])
def logout():
    session.pop('username', None)
    return jsonify({'success': True})

@api.route('/contacts', methods=['POST'])
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

@api.route('/contacts', methods=['GET'])
def get_contacts():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'User not logged in.'})

    logged_in_user = User.query.filter_by(username=session['username']).first()
    if not logged_in_user:
        return jsonify({'success': False, 'message': 'User not found.'})

    # Get all chats the user participates in
    contacts = Chat.query.join(ChatParticipant).filter(ChatParticipant.user_id == logged_in_user.id).all()

    contact_details = []

    for chat in contacts:
        # Find the other participant in the chat
        other_participant = [
            participant for participant in chat.participants
            if participant.user_id != logged_in_user.id
        ]
        other_user = other_participant[0].user if other_participant else None

        # Get the latest message for this chat
        latest_message = (
            Message.query.filter_by(chat_id=chat.id)
            .order_by(Message.timestamp.desc())
            .first()
        )

        if other_user:
            contact_details.append({
                'chat_id': chat.id,
                'chat_name': other_user.username,
                'latest_message': latest_message.content if latest_message else None,
                'latest_message_timestamp': latest_message.timestamp.strftime('%H:%M') if latest_message else None  # Add timestamp
            })

    return jsonify({'success': True, 'contacts': contact_details})

@api.route('/messages', methods=['POST'])
def send_message():
    data = request.get_json()
    chat_id = data['chat_id']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data['content']

    # Create and save the message
    new_message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        chat_id=chat_id,
        content=content
    )
    db.session.add(new_message)
    db.session.commit()

    # Format the timestamp
    formatted_timestamp = new_message.timestamp.strftime('%H:%M')

    return jsonify({
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'chat_id': chat_id,
        'content': content,
        'timestamp': formatted_timestamp,
        'status': new_message.status
    })
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'User not logged in.'})

    if 'profile_picture' not in request.files:
        return jsonify({'success': False, 'message': 'No file part.'})

    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file.'})

    if file and allowed_file(file.filename):
        user = User.query.filter_by(username=session['username']).first()
        user.profile_picture = file.read()  # Store the image data as binary
        db.session.commit()

        # Return the necessary data for emitting the WebSocket event
        image_data = base64.b64encode(user.profile_picture).decode('utf-8')
        return jsonify({'success': True, 'message': 'File successfully uploaded.', 'user_uuid': user.uuid, 'profile_picture': image_data})
    else:
        return jsonify({'success': False, 'message': 'File type not allowed.'})

@api.route('/profile_picture', methods=['GET'])
def get_profile_picture():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'User not logged in.'})

    user = User.query.filter_by(username=session['username']).first()
    if user and user.profile_picture:
        image_data = base64.b64encode(user.profile_picture).decode('utf-8')
        return jsonify({'success': True, 'profile_picture': image_data})
    else:
        return jsonify({'success': False, 'message': 'No profile picture found.'})