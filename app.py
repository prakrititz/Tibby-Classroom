from flask import Flask, render_template, redirect, url_for, session, request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from authlib.integrations.flask_client import OAuth
import os
from flask_login import current_user
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a real secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
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
    #i am creating a user thingyy
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User(email=user_info['email'], name=user_info.get('name', ''), picture=user_info.get('picture', ''))
        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    return redirect(url_for('home'))


@app.route('/my_learnings')#endpoints 
@login_required
def my_learnings():
    return render_template('my_learnings.html')

@app.route('/friends')
@login_required
def friends():
    return render_template('friends.html', friends=current_user.friends)

@app.route('/search_friends')
@login_required
def search_friends():
    query = request.args.get('query', '')
    users = User.query.filter(User.name.ilike(f'%{query}%')).all()
    return jsonify([{'id': user.id, 'name': user.name, 'picture': user.picture} for user in users])

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

@app.route('/chat')#endpoints 
@login_required
def chat():
    return render_template('chat.html')

if __name__ == '__main__':
    with app.app_context(): # This will drop all existing tables
        db.create_all()  # This will create all tables defined in your models
    app.run(debug=True)