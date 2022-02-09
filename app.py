from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session, g
from langcodes import Language
import psycopg2
import datetime as dt
from newsapi import NewsApiClient
from flask_debugtoolbar import DebugToolbarExtension 
from models import connect_db, db, User, Story, Note, SavedStory
from flask_bcrypt import Bcrypt
from forms import RegisterForm, LoginForm, SearchForm
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
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
sia = SIA()
from textblob import TextBlob

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

def get_search_results(query):
    results = []
    return results
    
"""Sentiment Analysis Functions"""

def parse(headline):
    article = Article(headline.url)
    article.download()
    article.parse()
    parsed = article.text
    return parsed

def tokenize(headline):
    parsed = parse(headline)
    #tokenization from spacy and remove punctuations, convert to set to remove duplicates
    words = set([str(token) for token in nlp(parsed) if not token.is_punct])
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
    #import lists of stopwords from NLTK
    stop_words = set(stopwords.words('english'))
    words = [w for w in words if not w.lower() in stop_words]

    print("Below is length after stopwords filtered")
    print(len(words))

    # lemmization from spacy. doesn't appear to be doing anything. fix this
    words = [token.lemma_ for token in nlp(str(words)) if not token.is_punct]
    print("Below is length after Lemmatization")
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

def subjectize(headline):
    parsed = parse(headline)
    tblobbed = TextBlob(parsed)
    subjectivity = tblobbed.sentiment.subjectivity
    sub_obj = {}
    if subjectivity > .80:
        sub_obj['measure'] = "Very Objective"
    elif subjectivity > .60:
        sub_obj['measure'] = "Moderately Objective"
    elif subjectivity > .40:
        sub_obj['measure'] = "Neutral"
    elif subjectivity > .20:
        sub_obj['measure'] = "Moderately Subjective"
    else:
        sub_obj['measure'] = "Very Subjective"
    sub_obj['score'] = subjectivity
    return sub_obj

def polarize(headline):
    #function returns an object of two sepearate polarity scores; one based off the text of the article and the other
    #from just the headline alone. Each of these are represented in their own respective objects. 
    pol_obj = {}
    headline_res = {}
    article_res = {}

    """Logic for polarity from article text"""
    parsed = parse(headline)
    sentenced = nltk.tokenize.sent_tokenize(parsed)

    coms = []
    pos = []
    negs = []
    neus = []

    for sentence in sentenced:
        res = sia.polarity_scores(sentence)

        pos.append(res["pos"])
        negs.append(res["neg"])
        neus.append(res["neu"])
        if res['compound']:
            #sometimes the composite will be zero for certain sentences. We don't want to include that data. 
            coms.append(res['compound'])

    avg_com = sum(coms) / len(coms)
    avg_pos = sum(pos) / len(pos)
    avg_neu = sum(neus) / len(neus)
    avg_neg = sum(negs) / len(negs)

    """Logic for polarity from headline text"""

    headline = sia.polarity_scores(headline.headline)
    headline_res["com"] = headline['compound']
    headline_res["pos"] = headline['pos']
    headline_res["neg"] = headline['neg']
    headline_res["neu"] = headline['neu']

    if headline_res['com'] >= 0.2 :
        headline_res['result'] = "Positive"
 
    elif headline_res['com'] <= - 0.2 :
        headline_res['result'] = "Negative"
 
    else:
        headline_res['result'] = "Neutral"

    article_res["avg_com"] = avg_com
    article_res["avg_pos"] = avg_pos
    article_res["avg_neg"] = avg_neg
    article_res["avg_neu"] = avg_neu

    if avg_com >= 0.2 :
        article_res['result'] = "Positive"
 
    elif avg_com <= - 0.2 :
        article_res['result'] = "Negative"
 
    else :
        article_res['result'] = "Neutral"

    print(f"Average sentiment of each sentence in article: compound {avg_com}")
    print(f"sentence was rated as , {avg_neg *100}, % Negative")
    print(f"sentence was rated as , {avg_neu *100}, % Neutral")
    print(f"sentence was rated as , {avg_pos *100}, % Positive")

    pol_obj['headline_res'] = headline_res
    pol_obj['article_res'] = article_res
    return pol_obj

def sa_sum(headlines):
    for headline in headlines:
        sum = {}
        sum['parsed']  = parse(headline)
        sum['tokenized'] = tokenize(headline)
        sum['subjectivity'] = subjectize(headline)
        sum['polarity'] = polarize(headline)
        return sum

def order_stories_recent(stories):
    ordered = sorted(stories, key = lambda story : story.published_at, reverse=True )
    return ordered
        

"""View functions for application"""


@app.route('/', methods= ['GET', 'POST'])
def home_page():
    if session['query']:
        results = session['query']
    else:
        results = get_top_headlines()
    
    headlines = order_stories_recent(results)
    return render_template('/home.html', headlines=headlines)


"""Search Query Functions"""
@app.route('/user/search/submit', methods = ["POST"])
def search_params():
    form = SearchForm()
    if form.validate_on_submit():
        try:
        #     if form.data.default == True: (ADD TO USER TABLE IN DATABASE)
            
            keyword = form.keyword.data
            source = form.source.data
            quantity = form.quantity.data
            search_by = form.search_by.data
            date_from = form.date_from.data
            date_to = form.date_to.data
            language = form.language.data
            sort_by = form.sort_by.data
            default = form.defualt.data
            #check to see if this is a string of true or false, or the boolean type values
            dict = {}
            dict['keyword'] = keyword
            dict['source'] = source
            dict['quantity'] = quantity
            dict['date_from'] = date_from
            dict['date_to'] = date_to
            dict['search_by'] = search_by
            dict['language'] = language
            dict['sort_by'] = sort_by
            dict['default'] = default
            # if default == True:
            #     User.default_search = dict
            #     db.session.commit()
            results = get_search_results()
            session['query'] = results
            return redirect('/')

        except IntegrityError:
            flash("hmmmm. do this appear, or messages from form validators?", 'danger')
            return render_template('register.html', form=form)

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