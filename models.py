# from imaplib import _CommandResults
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime


db = SQLAlchemy()

bcrypt = Bcrypt()


def connect_db(app):
    """Connect to database."""

    db.app = app
    db.init_app(app)

    

class User(db.Model):
    
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20),
                     nullable=False, 
                     unique=True)
    password = db.Column(db.Text,
                     nullable=False)
    email = db.Column(db.String(50),
                     nullable=False, 
                     unique=True)
    first_name = db.Column(db.String(30),
                     nullable=False)
    last_name = db.Column(db.String(30),
                     nullable=False)
    saved_stories = db.relationship('Story', secondary='saved_stories', backref= 'users')
    queried_stories = db.relationship('Story', secondary= 'queried_stories', backref = 'user_queries')
    #this is used to easily group all stories in a selected search query by the user. Useful for adding 
    #polarity and subjectivity when specified in searches, and for deleting each story from db to optimize space
    history = db.relationship('Story', secondary='user_history', backref= "viewed_by")
    notes = db.relationship('Note', backref= 'user') 

    default_search = db.Column(db.Text)
    # user to get headlines on home page

    
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



    def __repr__(self):
        return f"<ID: {self.id}, Username:{self.username}>"



class Story(db.Model):
    __tablename__ = "stories"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    """information taken from newsapi request"""
    headline = db.Column(db.String, nullable=False)
    source = db.Column(db.String, nullable=False)
    content= db.Column(db.String)
    author = db.Column(db.String)
    description = db.Column(db.String)
    url = db.Column(db.Text)
    image = db.Column(db.Text)
    published_at = db.Column(db.DateTime)

    """information related to its interaction with app"""
    notes = db.relationship('Note', backref= 'story')
    views = db.Column(db.Integer)
    sub = db.Column(db.Text)
    pol = db.Column(db.Text)

    def __repr__(self):
        return f"<ID: {self.id}, H:{self.headline}, S:{self.source}>"

class SavedStory(db.Model):
    __tablename__ = "saved_stories"
    id = db.Column(db.Integer,
    primary_key=True,
    autoincrement=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable = False)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f"<ID: {self.id}, User ID#:{self.user_id}, Story ID#:{self.story_id}>"

class QueriedStory(db.Model):
    __tablename__ = "queried_stories"
    id = db.Column(db.Integer,
    primary_key=True,
    autoincrement=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable = False)
    def __repr__(self):
        return f"<ID: {self.id}, User ID#:{self.user_id}, Story ID#:{self.story_id}>"
    
    def order_stories_date(self, stories):
        ordered = sorted(stories, key = lambda story : story.published_at, reverse=True )
        return ordered

    def order_stories_pol(self, stories):
        #TODO loop through storie. for stories that dont yet have pol, add pol. For articles that have come back as an error
        #make sure their avgcom is set to 0 and appear last in the list
        # db.session.commit()
        ordered = sorted(stories, key = lambda story : story.article_res.avg_com, reverse=True )
        return ordered
    
    def order_stories_sub(self, stories):
        #TODO loop through storie. for stories that dont yet have sub, add sub. For articles that have come back as an error
        #make sure their avgcom is set to 0 and appear last in the list
        # db.session.commit()
        ordered = sorted(stories, key = lambda story : story.subjectivity, reverse=True )
        return ordered

class UserHistory(db.Model):
    __tablename__ = "user_history"
    id = db.Column(db.Integer,
    primary_key=True,
    autoincrement=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable = False)
    #add date viewed

    def __repr__(self):
        return f"<ID: {self.id}, User ID#:{self.user_id}, Story ID#:{self.story_id}>"

class Note(db.Model):
    #originally used as comments
    __tablename__ = "notes"
    id = db.Column(db.Integer,
    primary_key=True,
    autoincrement=True)

    parent_note = db.Column(db.Integer, db.ForeignKey('notes.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable = False)
    content = db.Column(db.Text, nullable = False)
    date = db.Column(db.DateTime)


    def __repr__(self):
        return f"<ID: {self.id}, User ID#:{self.user_id}, Story ID#:{self.story_id}>"

