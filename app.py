from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session
import psycopg2
import datetime as dt
from newsapi import NewsApiClient
# from key import api_key
from flask_debugtoolbar import DebugToolbarExtension 
from models import connect_db, db, User, Story, SavedStory
from flask_bcrypt import Bcrypt
from forms import RegisterForm, LoginForm

bcrypt = Bcrypt()


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///newstracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = "topsecret1"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
debug = DebugToolbarExtension(app)


# connect_db(app)

newsapi= NewsApiClient(api_key='b4f52eb738354e648912261c010632e7')

data = newsapi.get_everything(q="trump")
articles = data['articles']
def get_stories():
    for article in articles:
        headline = article['title']
        source = article["source"]["name"]
        content =article['content']
        author =article['author']
        description = article['description']
        url = article['url']
        image = article['urlToImage']
        published_at = dt.datetime.strptime(article['publishedAt'],"%Y-%m-%dT%H:%M:%SZ").date()
        story = Story(headline=headline, source=source, content=content,
        author=author, description=description, url=url, image=image,
        published_at= published_at)
        db.session.add(story)
        db.session.commit()




@app.route('/')
def home_page():
    return redirect('/register')


@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        new_user = User.register(username, password, email, first_name, last_name)
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
        return redirect('/')
    
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login_user():
    if "user_id" in session:
        return redirect(f"/users/{session['user_id']}")

    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user.id

            return redirect('/')
        else:
            form.username.errors=["Invalid username or password. Please try again."]
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout_user():
    session.pop('user_id')
    return redirect('/')