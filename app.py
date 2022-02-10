from re import L
from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session, g
from models import connect_db, db, User, Story, Note, SavedStory

from forms import RegisterForm, LoginForm, SearchForm
from api_calls import get_from_newsapi, get_search_results
from sent_analysis import parse, subjectize, tokenize, polarize, sa_sum


from langcodes import Language
import psycopg2
import datetime as dt
import requests
from dateutil import parser
from newsapi import NewsApiClient



from flask_debugtoolbar import DebugToolbarExtension 
from flask_bcrypt import Bcrypt


#libraries for parsing and sentiment analysis
# from bs4 import BeautifulSoup
# from newspaper import Article
# from sqlalchemy.exc import IntegrityError
# import nltk
# nltk.download('stopwords')
# nltk.download('punkt')
# from nltk.corpus import stopwords
# from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
# sia = SIA()
# from textblob import TextBlob

# import spacy
# nlp = spacy.load('en_core_web_sm', disable=["parser", "ner"])
# import re


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


def order_stories_recent(stories):
    ordered = sorted(stories, key = lambda story : story.published_at, reverse=True )
    return ordered
        

"""View functions for application"""

@app.route("/search/results")
def test():
    if CURR_USER_KEY in session:
        query = session.get("query")
        headlines = get_from_newsapi(query)
        print(headlines)
        print("head1")
        return render_template('/home.html', headlines=headlines)




@app.route('/', methods= ['GET', 'POST'])
def home_page():
    headlines = get_from_newsapi(None)
    return render_template('/home.html', headlines=headlines)

@app.route('/users/search', methods = ['GET', 'POST'])
def search_params():
    form = SearchForm()
    if form.validate_on_submit():
        try:
            # keyword = form.keyword.data
            # source = form.source.data
            # quantity = form.quantity.data
            # search_in = form.search_in.data
            # date_from = form.date_from.data
            # date_to = form.date_to.data
            # language = form.language.data
            # sort_by = form.sort_by.data
            # default = form.default.data

            dict = {}
            dict['keyword'] = form.keyword.data
            dict['source'] = form.source.data
            dict['quantity'] = form.quantity.data
            dict['date_from'] = form.date_from.data
            dict['date_to'] = form.date_to.data
            dict['search_in'] = form.search_in.data
            dict['language'] = form.language.data
            dict['sort_by'] = form.sort_by.data
            dict['default'] = form.default.data
            #check to see if this is a string of true or false, or the boolean type values

            # if default == True:
            #     User.default_search = dict1
            #     db.session.commit()
            print(dict['date_from'])
            print("date2")
            results = get_search_results(dict)
            query = results
            session["query"] = query
         
            return redirect('/search/results')

        except:
            print("LOL")
            flash("hmmmm. do this appear, or messages from form validators?", 'danger')
            return render_template('/users/search.html', form = form)
    
    
    else:
        print("something went wrong")
        return render_template('/users/search.html', form = form)
        

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
        ordered = order_stories_recent(user.saved_stories)
        user.saved_stories = ordered
        return render_template("/users/user.html", user = user)

@app.route('/story/<int:story_id>/open')
def open_story_link(story_id):   
        story = Story.query.get(story_id)
        user = User.query.get(g.user.id)
        user.history.append(story)
        # print(story.views)
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