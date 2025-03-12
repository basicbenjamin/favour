from flask import Flask,jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash, check_password_hash # Import for password hashing
from datetime import datetime # Import datetime for formatting dates

app = Flask(__name__)

# --- Database Configuration --- (keep your existing database configuration)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'favour.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app) # Initialize SQLAlchemy *without* the app for now

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

# --- New Create Favour Request Route ---
@app.route('/api/favours/request', methods=['POST'])
def create_favour_request():
    data = request.get_json()

    if not data:
        return jsonify({'message': 'Request data is required'}), 400

    # --- Temporarily get requester_id from request for simplicity (SECURITY RISK - to be improved later) ---
    requester_id = data.get('requester_id') # In real app, get from session/auth token

    favour_type = data.get('favour_type')
    description = data.get('description')
    credits_offered = data.get('credits_offered') 

    
    # --- START of Input Validation ---
    if not favour_type:
        return jsonify({'message': 'Favour type is required'}), 400
    if favour_type not in ['text', 'voice', 'video']: # Check against allowed favour types
        return jsonify({'message': 'Invalid favour type. Must be one of: text, voice, video'}), 400

    if not description:
        return jsonify({'message': 'Description is required'}), 400
    if len(description) < 10 or len(description) > 500: # Example description length limits
        return jsonify({'message': 'Description must be between 10 and 500 characters'}), 400

    try: # Validate credits_offered is a positive integer
        credits = int(credits_offered)
        if credits <= 0:
            return jsonify({'message': 'Credits offered must be a positive number'}), 400
        credits_offered = credits # Convert to integer if valid
    except (ValueError, TypeError):
        return jsonify({'message': 'Credits offered must be a valid positive integer'}), 400
    # --- END of Input Validation ---

    #- START of Credit Balance Check ---
    requester = User.query.get(requester_id) # Retrieve the User object from the database using requester_id
    if not requester: # Check if requester with given ID exists (defensive check)
        return jsonify({'message': 'Invalid requester ID'}), 400 # Or 404 Not Found - depends on desired behavior
    

    if requester.credit_balance < credits_offered: # Check if user has enough credits
        return jsonify({'message': 'Insufficient credits. You need more credits to request this favour.'}), 400 # Or 402 Payment Required, but 400 is OK for now
    # --- END of Credit Balance Check ---


    # --- START of Favour Request Creation and Database Saving ---
    new_favour_request = FavourRequest(
        favour_type=favour_type,
        description=description,
        credits_offered=credits_offered, # Use credits_cost here (or credits_offered, whichever you prefer consistently)
        requester_id=requester_id
    )
    db.session.add(new_favour_request) # Add the new favour request to the database session

    requester.credit_balance -= credits_offered # Deduct credits from the requester's balance
    # db.session.add(requester) # Not strictly needed as SQLAlchemy tracks changes to loaded objects
                                # but can be more explicit if preferred

    db.session.commit() # Commit the session to save both the new favour request and updated user balance
    # --- END of Favour Request Creation and Database Saving ---

    return jsonify({'message': 'Favour request created successfully',
                    'request_id': new_favour_request.request_id}), 201 # 201 Created - resource created successfully
    # --- End Create Favour Request Route ---

# --- Get Open Favour Requests Route (Modified) ---
@app.route('/api/favours/open', methods=['GET'])
def get_open_favour_requests():
    open_requests = FavourRequest.query.filter_by(status='open').all() # Query for open favour requests

    favour_requests_list = [] # Initialize an empty list to hold serialized favour requests
    for req in open_requests: # Iterate through each open favour request
        favour_requests_list.append({ # Create a dictionary for each request and append to the list
            'request_id': req.request_id,
            'favour_type': req.favour_type,
            'description': req.description,
            'credits_offered': req.credits_offered,
            'requester_username': req.requester.username, # Access requester username via relationship
            'request_date': req.request_date.isoformat() # Format datetime to ISO string for JSON
        })

    return jsonify({'open_favour_requests': favour_requests_list}), 200 # Return list of open favour requests in JSON
# --- End Get Open Favour Requests Route ---

if __name__ == '__main__':
    app.run(debug=True)