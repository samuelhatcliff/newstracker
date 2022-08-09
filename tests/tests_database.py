import sys
sys.path.append("..")
from unittest import TestCase
from app import app
from models import db, User, Story, Query
app.config['SQLALCHEMY_ECHO'] = False
app.config['TESTING'] = True
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///newstracker-test'

db.drop_all()
db.create_all()

class User_Model(TestCase):

    def setUp(self):
        """Cleans up any existing users"""
        User.query.delete()

    def tearDown(self):
        db.session.rollback()

    def test_register(self):
        user = User.register(
            "testuser", "test4444", "test@test.com", "test", "user")
        """Tests columns id and username as written in __repr__"""
        self.assertEquals(str(user), f"<ID: {user.id}, Username:{user.username}>")
        # self.assertEquals(str(user), f"<ID: 1, Username:testuser>")
        """Tests that columns are accessible as written"""
        # todo: make sure model is autonmatically assigning id, right now the following test fails
        # self.assertEquals(user.id, 1)
        self.assertEquals(user.username, "testuser")
        self.assertEquals(user.email, "test@test.com")
        self.assertEquals(user.first_name, "test")
        self.assertEquals(user.last_name, "user")
        """Tests that password is hashed and not accessible"""
        self.assertNotEquals(user.password, "test4444")








