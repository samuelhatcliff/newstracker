from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()

bcrypt = Bcrypt()


def connect_db(app):
    """Connect to database."""

    db.app = app
    db.init_app(app)
    

class User(db.Model):
    
    __tablename__ = "users"
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True)
    username = db.Column(db.String(20),
                     nullable=False)
    password = db.Column(db.Text,
                     nullable=False)
    email = db.Column(db.String(50),
                     nullable=False)
    first_name = db.Column(db.String(30),
                     nullable=False)
    last_name = db.Column(db.String(30),
                     nullable=False)
    saved_stories = db.relationship('Story', secondary='saved_stories', backref= 'users')

    
    @classmethod
    def register(cls, username, pwd, email, first_name, last_name):
        hashed= bcrypt.generate_password_hash(pwd)
        
        hashed_utf8 = hashed.decode("utf8")
        
        new_user = cls(username=username, password=hashed_utf8, email=email, first_name=first_name, last_name=last_name)
        db.session.add(new_user)
        return new_user
    
    
    @classmethod
    def authenticate(cls, username, pwd):
        u = User.query.filter_by(username=username).first()
        
        if u and bcrypt.check_password_hash(u.password, pwd):
            return u
        else:
            return False

class Story(db.Model):
    __tablename__ = "stories"
    id = db.Column(db.Integer,
    primary_key=True,
    autoincrement=True)
    headline = db.Column(db.text, nullable=False)
    publisher = db.Column(db.text, nullable=False)
    author = db.Column(db.text)



class SavedStory(db.Model):
    __tablename__ = "saved_stories"
    id = db.Column(db.Integer,
    primary_key=True,
    autoincrement=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable = False)