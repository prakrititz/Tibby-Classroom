from flask import Flask, render_template, redirect, url_for, session, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from authlib.integrations.flask_client import OAuth
import os
from flask_login import current_user
import uuid
from new_summary import generate_visual_teaching, generate_background_images, save_teaching_to_json
import uuid
from werkzeug.utils import secure_filename
from langchain.document_loaders import PyPDFLoader
from populate_database import split_documents, add_to_chroma
from myquiz import *
from query_data import query_rag
TEST_USER = 'TEST_USER'

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a real secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = './uploads'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# OAuth 2 client setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='862041045226-soojb5uhcu3ieddn2ga9hh37oooair0i.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

friends = db.Table('friends',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    picture = db.Column(db.String(200))
    bio = db.Column(db.String(200), default='NewBie')
    points = db.Column(db.Integer, default=0)
    tags = db.Column(db.PickleType, default=["AI Generative", "Python", "All those other stuff"])
    completed_topics = db.Column(db.PickleType, default=[])
    badges = db.Column(db.PickleType, default=[])
    achievements = db.Column(db.PickleType, default=[])
    friends = db.relationship('User', 
                              secondary=friends,
                              primaryjoin=(friends.c.user_id == id),
                              secondaryjoin=(friends.c.friend_id == id),
                              backref=db.backref('friended_by', lazy='dynamic'),
                              lazy='dynamic')

    def add_friend(self, user):
        if user not in self.friends:
            self.friends.append(user)
            user.friends.append(self)

    def remove_friend(self, user):
        if user in self.friends:
            self.friends.remove(user)
            user.friends.remove(self)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    redirect_uri = url_for('auth_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/auth_google')
def auth_google():
    token = oauth.google.authorize_access_token()
    resp = oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User(email=user_info['email'], name=user_info.get('name', ''), picture=user_info.get('picture', ''))
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for('home'))

@app.route('/my_learnings')
@login_required
def my_learnings():
    return render_template('my_learnings.html', user=current_user)

@app.route('/friends')
@login_required
def friends():
    return render_template('friends.html', user=current_user)

@app.route('/search_friends')
@login_required
def search_friends():
    query = request.args.get('query', '')
    users = User.query.filter(User.name.ilike(f'%{query}%')).all()
    return jsonify([{'id': user.id, 'name': user.name, 'picture': user.picture, 'points': user.points} for user in users])

@app.route('/add_friend/<int:friend_id>', methods=['POST'])
@login_required
def add_friend(friend_id):
    friend = User.query.get(friend_id)
    if friend:
        current_user.add_friend(friend)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    user = User.query.get(user_id)
    if user:
        return render_template('profile.html', user=user)
    return redirect(url_for('friends'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html', user=current_user)

@app.route('/generate_summary', methods=['POST'])
@login_required
def generate_summary():
    topic = request.json.get('topic')
    chat_id = str(uuid.uuid4())
    
    teaching_sequence = generate_visual_teaching(topic, chat_id=chat_id)
    
    if teaching_sequence:
        generate_background_images(teaching_sequence)
        json_filename = f"{topic.replace(' ', '_').lower()}_summary.json"
        file_path = save_teaching_to_json(teaching_sequence, json_filename)
        tags = teaching_sequence.model_dump()["tags"]
        print(tags)
        current_user.tags.extend(tags)
        db.session.commit()
        print("successfully commited")
        print(current_user.tags)
        return jsonify({
            "summary": teaching_sequence.model_dump(),
            "file_path": file_path
        })
    else:
        return jsonify({"error": "Failed to generate summary"}), 400

@app.route('/get_background_image/<path:filename>')
def get_background_image(filename):
    return send_from_directory('backgrounds', filename)

@app.route('/create_quiz', methods=['POST'])
@login_required
def create_quiz():
    topic = request.json.get('topic')
    num_questions = request.json.get('num_questions', 5)
    
    quiz = generate_quiz(topic, num_questions)
    
    if quiz:
        quiz_data = quiz.model_dump()
        session['current_quiz'] = quiz_data
        return jsonify(quiz_data)
    else:
        return jsonify({"error": "Failed to generate quiz"}), 400

@app.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    user_answers = request.json.get('answers')
    quiz_data = session.get('current_quiz')
    
    if not quiz_data:
        return jsonify({"error": "No active quiz found"}), 400
    
    score = 0
    total_questions = len(quiz_data['questions'])
    
    for i, question in enumerate(quiz_data['questions']):
        if user_answers.get(str(i)) == next(option['text'] for option in question['options'] if option['is_correct']):
            score += 1
    
    percentage = (score / total_questions) * 100
    
    # Update user's points and completed topics
    current_user.points += score
    if quiz_data['topic'] not in current_user.completed_topics:
        current_user.completed_topics.append(quiz_data['topic'])
    db.session.commit()
    
    return jsonify({
        "correct_answers":[{"text":option['text'],"explanation":question["explanation"]} for i, question in enumerate(quiz_data['questions']) for option in question['options'] if option['is_correct']],
        "score": score,
        "total_questions": total_questions,
        "percentage": percentage
    })

@app.route('/quiz')
@login_required
def quiz():
    return render_template('quiz.html', user=current_user)
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        chat_id = TEST_USER
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            process_pdf(file_path, chat_id=chat_id)
            return jsonify({"message": "File uploaded and processed successfully"}), 200
        return jsonify({"error": "Invalid file type"}), 400
    except Exception as e:
        app.logger.error(f"Error in upload_pdf: {str(e)}")
        return jsonify({"error": "An internal server error occurred"}), 500


def process_pdf(file_path, chat_id):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    chunks = split_documents(documents)
    add_to_chroma(chunks, chat_id)

@app.route('/get_pdf_list')
def get_pdf_list():
    pdf_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.pdf')]
    return jsonify({'pdfs': pdf_files})

@app.route('/get_document/<filename>')
def get_document(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/ragchat', methods=['POST'])
def ragchat():
    message = request.json.get('message')
    chat_id = TEST_USER
    response, sources = query_rag(message, chat_id)
    return jsonify({'response': response, 'sources': sources})



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
