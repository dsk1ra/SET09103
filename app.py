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
            return render_template("chats.html", user_uuid=user_uuid, username=user.username)
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
    receiver_id = data['receiver_id']
    chat_id = data['chat_id']
    content = data['content']

    # Save the message to the database (example)
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
        'status': new_message.status
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

if __name__ == '__main__':
    socketio.run(app)