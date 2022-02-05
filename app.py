from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session, g
import psycopg2
import datetime as dt
from newsapi import NewsApiClient
from flask_debugtoolbar import DebugToolbarExtension 
from models import connect_db, db, User, Story, Comment, SavedStory
from flask_bcrypt import Bcrypt
from forms import RegisterForm, LoginForm
import requests
from dateutil import parser

#libraries for parsing and sentiment analysis
from bs4 import BeautifulSoup
from newspaper import Article
from sqlalchemy.exc import IntegrityError
import nltk
nltk.download('stopwords')
nltk.download('punkt')
from nltk.corpus import stopwords
import spacy
nlp = spacy.load('en_core_web_sm', disable=["parser", "ner"])
import re


CURR_USER_KEY = "curr_user"

bcrypt = Bcrypt()


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///nt'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = "topsecret1"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
debug = DebugToolbarExtension(app)





# def getHeadlines():
#     key = 'b4f52eb738354e648912261c010632e7'


connect_db(app)
db.create_all()
newsapi= NewsApiClient(api_key='b4f52eb738354e648912261c010632e7')


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""
    print(session[CURR_USER_KEY])
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


def get_top_headlines():
    data = newsapi.get_top_headlines(language="en")
    articles = data['articles']
    top_headlines = []
    for article in articles:
        headline = article['title']
        source = article["source"]["name"]
        if type(article["content"]) == None:
            print("ITS A NONE TYPE")
            content = "Click the following link to view story."
        else:
            content=article['content']
        
        author =article['author']
        description = article['description']
        url = article['url']
        image = article['urlToImage']
        api_date = article['publishedAt']
        published_at = parser.parse(api_date)
        views = 0
        story = Story(headline=headline, source=source, content=content,
        author=author, description=description, url=url, image=image,
        published_at= published_at, views=views)
        top_headlines.append(story)
        db.session.add(story)
        db.session.commit()

    return top_headlines



def scrap(headlines):
    headline = headlines[16]
    article = Article(headline.url)
    article.download()
    article.parse()
    print(headline.headline)

    print("Below is article.text")
    print(article.text)

    
    #tokenization and remove punctuations
    words = set([str(token) for token in nlp(article.text) if not token.is_punct])
    print("Below is length upon tokenization")
    print(len(words))
    # remove digits and other symbols except "@"--used to remove email
    words = list(words)
    words = [re.sub(r"[^A-Za-z@]", "", word) for word in words]
     #remove special characters
    words = [re.sub(r'\W+', '', word) for word in words]
    #remove websites and email addresses 
    words = [re.sub(r'\S+@\S+', "", word) for word in words]
    #remove empty spaces 
    words = [word for word in words if word!=""]
    
    print("Below is length before stopwords")
    print(len(words))
    #import other lists of stopwords
    stop_words = set(stopwords.words('english'))
    words = [w for w in words if not w.lower() in stop_words]

    print("Below is length after stopwords filtered")
    print(len(words))

    words = [token.lemma_ for token in nlp(str(words)) if not token.is_punct]
    print("Below is length after Lemmatization")
    #this doesn't appear to be doing anything
    print(len(words))

    vowels = ['a','e','i','o','u']
    words = [word for word in words if any(v in word for v in vowels)]
    print("Below is length after words with no vowels removed")
    print(len(words))  
    
    #eliminate duplicate words by turning list into a set
    words_set = set(words)
    print("Below is length after converted to set")
    print(len(words_set))  
    return words_set


    # sources: https://towardsdatascience.com/a-step-by-step-tutorial-for-conducting-sentiment-analysis-a7190a444366
    #https://datascience.stackexchange.com/questions/39960/remove-special-character-in-a-list-or-string
def order_stories(stories):
    ordered = sorted(stories, key = lambda story : story.published_at, reverse=True )
    return ordered
        




@app.route('/')
def home_page():
    top = get_top_headlines()
    headlines = order_stories(top)
    return render_template('/home.html', headlines=headlines)

@app.route('/show_story/<int:story_id>')
def show_story(story_id):
    story = Story.query.get(story_id)
 

    return render_template('/users/story.html', story = story)

@app.route('/user')
def user():
    if g.user.id != session[CURR_USER_KEY]:
        flash("Please log-in and try again.", "danger")
        return redirect("/")
    
    else:
        user = User.query.get(g.user.id)
        ordered = order_stories(user.saved_stories)
        user.saved_stories = ordered
        return render_template("/users/user.html", user = user)


@app.route('/story/<int:story_id>/open')
def open_story_link(story_id):   
        print("NICE")
        story = Story.query.get(story_id)
        user = User.query.get(g.user.id)
        user.history.append(story)
        print(story.views)
        story.views += 1
        
        db.session.commit()
        return redirect (f"{story.url}")

@app.route('/story/<int:story_id>/save_story', methods=["POST"])
def save_story(story_id):
    if g.user.id != session[CURR_USER_KEY]:
        flash("Please log-in and try again.", "danger")
        return redirect("/")
    
    else: 
        story = Story.query.get(story_id)
        user = User.query.get(g.user.id)
        if story in user.saved_stories:
            flash("This story already exists in your saved stories.", "danger")
            return redirect("/")
        user.saved_stories.append(story)
        db.session.commit()
        return redirect("/user")

@app.route('/story/<int:story_id>/delete_story')
def delete_story(story_id):
    if g.user.id != session[CURR_USER_KEY]:
        flash("Please log-in and try again.", "danger")
        return redirect("/")
    
    else: 
        story = Story.query.get(story_id)
        user = User.query.get(g.user.id)
        user.saved_stories.remove(story)
        db.session.commit()
        return redirect("/user")



@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            username = form.username.data
            password = form.password.data
            email = form.email.data
            first_name = form.first_name.data
            last_name = form.last_name.data
            new_user = User.register(username, password, email, first_name, last_name)
            db.session.add(new_user)
            db.session.commit()
            do_login(new_user)
            return redirect('/')
        
        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('register.html', form=form)
    
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login_user():


    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.authenticate(username, password)
        if user:
            do_login(user)

            return redirect('/')
        else:
            form.username.errors=["Invalid username or password. Please try again."]
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    """Handle logout of user."""
    flash(f"You have successfully logged out.")
    do_logout()
    return redirect("/")