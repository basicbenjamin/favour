from flask import Flask,jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash # Import for password hashing

app = Flask(__name__)

# --- Database Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__)) # Get the absolute path of the current directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'favour.db') # SQLite database file in the same directory
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable modification tracking for performance

db = SQLAlchemy(app) # Initialize SQLAlchemy with your Flask app

# --- Data Models ---
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False) # For now, we'll just store a placeholder, password hashing will come later
    credit_balance = db.Column(db.Integer, default=0)
    registration_date = db.Column(db.DateTime, default=db.func.now()) # Automatically set to current time

    def __repr__(self):
        return f'<User {self.username}>'
    
class FavourRequest(db.Model):
    request_id = db.Column(db.Integer, primary_key=True)
    favour_type = db.Column(db.String(50), nullable=False) # e.g., "text", "voice", "video"
    description = db.Column(db.Text, nullable=False) # Text type for longer descriptions
    credits_offered = db.Column(db.Integer, nullable=False) # Credits the requester will SPEND
    status = db.Column(db.String(20), default='open') # e.g., "open", "claimed", "completed", "cancelled"
    request_date = db.Column(db.DateTime, default=db.func.now())
    requester_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False) # Foreign key to User table
    fulfiller_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=True) # Foreign key to User table, can be null initially

    requester = db.relationship('User', foreign_keys=[requester_id], backref=db.backref('requested_favours', lazy=True))
    fulfiller = db.relationship('User', foreign_keys=[fulfiller_id], backref=db.backref('fulfilled_favours', lazy=True))

    def __repr__(self):
        return f'<FavourRequest {self.request_id} - {self.favour_type}>'
    
# --- Create Database Tables (run only once initially) ---
#with app.app_context():
 #   db.create_all()
 #  print("Database tables created/updated!")

@app.route('/')
def hello_world():
    return 'Hello, World! from Favour Backend. SQL Alchemy is working!'

@app.route('/api/register', methods=['POST']) # Only allow POST requests
def register_user():
    data = request.get_json() # Get JSON data from the request body

    if not data or not data.get('username') or not data.get('password'): # Basic check for username and password in request
        return jsonify({'message': 'Username and password are required'}), 400 # 400 Bad Request

    username = data.get('username')
    password = data.get('password')

    # --- Placeholder for validation and user creation (we'll add this in the next steps) ---
    return jsonify({'message': 'Registration endpoint hit', 'username': username}), 201 # 201 Created

if __name__ == '__main__':
    app.run(debug=True)