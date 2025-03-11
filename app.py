from flask import Flask,jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash, check_password_hash # Import for password hashing

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

    # --- START of Username Validation ---
    if not username:
        return jsonify({'message': 'Username cannot be empty'}), 400

    if len(username) < 3 or len(username) > 80: # Example length constraints
        return jsonify({'message': 'Username must be between 3 and 80 characters'}), 400

    existing_user = User.query.filter_by(username=username).first() # Check if username already exists in DB
    if existing_user:
        return jsonify({'message': 'Username already taken'}), 409 # 409 Conflict - username already exists
    # --- END of Username Validation ---

    # --- START of Password Validation ---
    if not password:
        return jsonify({'message': 'Password cannot be empty'}), 400 # Already handled by initial check, but good to have explicitly
    if len(password) < 6: # Example minimum password length
        return jsonify({'message': 'Password must be at least 6 characters long'}), 400
    # --- END of Password Validation ---

    # --- Password Hashing ---
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8) # Generate a secure password hash
    # --- End Password Hashing ---


    # --- Create and Save User to Database ---
    new_user = User(username=username, password_hash=hashed_password) # Create a new User object
    db.session.add(new_user) # Add the new user to the database session (staging area)
    db.session.commit() # Commit the session to write the changes to the database
    # --- End User Creation and Database Saving ---

    return jsonify({'message': 'User registered successfully', 'username': username}), 201 # 201 Created - resource created successfully

# --- New Login Route ---
@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required'}), 400

    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first() # Retrieve user from database by username

    if not user: # Check if user exists
        return jsonify({'message': 'Invalid credentials'}), 401 # 401 Unauthorized - user not found

    if check_password_hash(user.password_hash, password): # Check if provided password matches the stored hash
        return jsonify({'message': 'Login successful', 'username': username}), 200 # 200 OK - Login successful
    else:
        return jsonify({'message': 'Invalid credentials'}), 401 # 401 Unauthorized - password doesn't match
# --- End Login Route ---

if __name__ == '__main__':
    app.run(debug=True)