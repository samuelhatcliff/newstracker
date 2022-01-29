from app import app
from models import db, User, Story, SavedStory, Comment


# db.drop_all()
db.create_all()