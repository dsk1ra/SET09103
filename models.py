from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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
