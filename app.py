from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, Message, User, Chat, ChatParticipant, BlockedUser, Notification
from api import api 

app = Flask(__name__)
app.config['SECRET_KEY'] = "40628952"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

with app.app_context():
    db.create_all()

app.register_blueprint(api, url_prefix='/api/v1')

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/signup')
def signup():
    return render_template("signup.html")

@app.route('/chats')
def chats():
    if 'username' in session:
        user_uuid = session.get('uuid')
        user = User.query.filter_by(uuid=user_uuid).first()
        if user:
            chats = Chat.query.join(ChatParticipant).filter(ChatParticipant.user_id == user.id).all()
            return render_template("chats.html", user_uuid=user_uuid, username=user.username, name=user.name, surname=user.surname, chats=chats)
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    user_uuid = session.get('uuid')
    if user_uuid:
        join_room(user_uuid)
        emit('user_connected', {'uuid': user_uuid}, room=user_uuid)

@socketio.on('disconnect')
def handle_disconnect():
    user_uuid = session.get('uuid')
    if user_uuid:
        leave_room(user_uuid)

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = data['sender_id']
    chat_id = data['chat_id']
    content = data['content']

    # Determine if the chat is a group chat
    chat = db.session.get(Chat, chat_id)
    if chat.type == 'group':
        receiver_id = None  # No specific receiver for group messages
    else:
        receiver_id = data.get('receiver_id')

    # Save the message to the database
    new_message = Message(sender_id=sender_id, receiver_id=receiver_id, chat_id=chat_id, content=content)
    db.session.add(new_message)
    db.session.commit()

    # Format the timestamp
    formatted_timestamp = new_message.timestamp.strftime('%H:%M')

    # Emit the message to the chat room
    emit('receive_message', {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'chat_id': chat_id,
        'content': content,
        'timestamp': formatted_timestamp,
        'status': new_message.status,
        'message_id': new_message.id
    }, room=chat_id)

    # Emit an event to update the contact item for all users
    emit('update_contact_item', {
        'chat_id': chat_id,
        'latest_message': content,
        'sender_id': sender_id
    }, broadcast=True)  # Broadcast to all clients
    
@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    response = api.upload_profile_picture()
    data = response.get_json()
    if data['success']:
        socketio.emit('update_profile_picture', {
            'user_uuid': data['user_uuid'],
            'profile_picture': data['profile_picture']
        }, broadcast=True)
    return response

@socketio.on('join_chat')
def handle_join_chat(data):
    chat_id = data['chat_id']
    user_uuid = session.get('uuid')
    if user_uuid:
        join_room(chat_id)
        emit('user_connected', {'uuid': user_uuid}, room=chat_id)

@socketio.on('create_group')
def handle_create_group(data):
    group_name = data['group_name']
    usernames = data['usernames']

    # Create the group chat
    new_chat = Chat(name=group_name, type='group')
    db.session.add(new_chat)
    db.session.commit()

    # Add the logged-in user as an admin
    logged_in_user = User.query.filter_by(uuid=session['uuid']).first()
    new_participant = ChatParticipant(chat_id=new_chat.id, user_id=logged_in_user.id, is_admin=True)
    db.session.add(new_participant)

    # Add other users to the group
    for username in usernames:
        user = User.query.filter_by(username=username).first()
        if user:
            new_participant = ChatParticipant(chat_id=new_chat.id, user_id=user.id)
            db.session.add(new_participant)

    db.session.commit()

    # Notify users about the new group
    for username in usernames:
        user = User.query.filter_by(username=username).first()
        if user:
            emit('group_created', {'chat_id': new_chat.id, 'group_name': group_name}, room=user.uuid)

    emit('group_created', {'chat_id': new_chat.id, 'group_name': group_name}, room=logged_in_user.uuid)


if __name__ == '__main__':
    socketio.run(app)