from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired

class RegisterForm(FlaskForm):
    '''form to add a new user. Username, password, and email required'''
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    email = StringField("Email")  
    first_name = StringField("First Name")
    last_name = StringField("Last Name")
    
    

class LoginForm(FlaskForm):
    '''form to login user with username and password'''
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    
