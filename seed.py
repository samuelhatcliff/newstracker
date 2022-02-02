from app import app
from models import db, User, Story, SavedStory, Comment


# db.drop_all()
db.create_all()

testuser = User(username="test", password="password", email="email@email.com", first_name="test", last_name="user",)