# flask, local, and system imports
import os
from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session, g
from models import connect_db, db, User, Story
# from flask_debugtoolbar import DebugToolbarExtension
from flask_bcrypt import Bcrypt

# external libraries
from forms import RegisterForm, LoginForm, SearchForm
from api_calls import api_call, cat_calls
from sent_analysis import subjectize, polarize

# sqlalchemy imports
from sqlalchemy import exc
from psycopg2.errors import UniqueViolation

# newsApi import
from newsapi.newsapi_client import NewsApiClient
import creds

# import all helper functions
from helpers import *

# set-up app
CURR_USER_KEY = "curr_user"
bcrypt = Bcrypt()
app = Flask(__name__)
production = False
if production:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql:///capstone').replace("://", "ql://", 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql:///capstone')

# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
# debug = DebugToolbarExtension(app)

# looks for heroku config variable first
my_api_key = os.environ.get("API_KEY", creds.api_key)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "nevertell")

newsapi = NewsApiClient(api_key=my_api_key)


connect_db(app)
# db.drop_all()
db.create_all()


# Todo:
# fix slideshow problem (as a temp fix remove arrows)
# write parallel requests or loading progress bar
# Redeploy!
# Figure out how to associate default query search with user. start by figuring out if migrations are neccessary. look up many to one relationships in sqlalchemy. saved_queries is a many to many relationship, but should be accessible as many to 1 with a simple foreign key. use user.filter to get foreign key
# implement saved queries (quick queries feauture)
# change TestQ to "Query"
# change "QueriedStories" to "ReturnedStories" or "Call Results" or "Query Results"
# Redeploy!
# add security
# add error handling, testing
# Redeploy!
# re-write aync sa functions as saving to the appropriate sqlalchemy obj in user.queried_stories, instead of dictionary. this will involve creating a new column "text" column and possibly a db migration


# When deploying:
# watch out for <link rel="stylesheet" href="http://127.0.0.1:5000/static/app.css"> that links css file. the absolute
# path of the local route was included to fix nested routes bootstrap bug. figure out how to fix this in production
# make sure api key is hidden and works

# Notes:
# Instead of changing current search query to sqlobject instead of session[dict],
# convert sqlobject to session[dict] when the time comes to incorporate that feature


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


"""View functions for application"""


@app.route('/')
def slideshow():
    """NewsTracker Homepage"""
    categories = ['business', 'entertainment',
                  'health', 'science', 'sports', 'technology']
    data = []
    for cat in categories:
        obj = {}
        obj['results'] = cat_calls(cat)
        obj['top_story'] = obj['results'].pop(0)
        obj['name'] = cat.capitalize()
        data.append(obj)

    return render_template('/homepage.html', data=data)


@app.route('/headlines', methods=['GET', 'POST'])
def home_page():
    if CURR_USER_KEY in session:
        user = User.query.get(g.user.id)
        if not user.queried_stories:
            """Generic Headlines with user logged in"""
            # if user does not have queried_stories, user hasn't arrived at route through search.
            # therefore, we want to make an api call requesting general headlines
            results = api_call(None)
            return render_template('/show_stories.html', results=results)

        """Search Results From User"""
        # this is just for development. get rid of this as well as if not user.queried stories statement
        results = user.queried_stories
        return render_template('/show_stories.html', results=results)
    else:
        """Generic Headlines without user logged in"""
        results = api_call(None)
        return render_template('/show_stories.html', results=results)


@app.route(f'/headlines/<category>')
def show_for_category(category):
    """Display top headlines for given category based off of link clicked from homepage"""
    category = category.lower()
    results = cat_calls(category)
    return render_template('show_stories.html', results=results)


@app.route('/search', methods=['GET', 'POST'])
def search_form():
    """This function creates a dictionary extracting data from the search form to be sent to the news-api"""
    if CURR_USER_KEY in session:
        form = SearchForm()
        if form.validate_on_submit():
            try:
                make_session_query(form)
                if form.saved_query.data:
                    add_saved_query(g.user.id, form)
                api_call(session['dict'], g.user.id)
                return redirect('/search/results')
            except:
                return render_template('/users/search.html', form=form)
        else:
            return render_template('/users/search.html', form=form)


@app.route('/search/simple', methods=['GET'])
def search_simple():
    """API Call and Results for Simple Search"""
    keyword = request.args.get("search")
    if CURR_USER_KEY in session:
        user = User.query.get(g.user.id)
        api_call(keyword, g.user.id)
        results = user.queried_stories
    else:
        results = api_call(keyword)

    return render_template('/show_stories.html', results=results)


@app.route('/search/results')
def handle_results():
    if CURR_USER_KEY in session:
        dict = session['dict']
        user = User.query.get(g.user.id)
        user_queried_stories = user.queried_stories
        results = user_queried_stories
        if dict['sa'] == 'polarity':
            results = order_pol()
        elif dict['sa'] == 'subjectivity':
            results = order_sub()
        else:
            return render_template('/show_stories.html', results=results)

    return render_template('/show_stories.html', results=results)


@app.route('/user/saved')
def user():
    if g.user.id != session[CURR_USER_KEY]:
        flash("Please log-in and try again.", "danger")
        return redirect("/")

    else:
        user = User.query.get(g.user.id)
        is_empty = False
        if len(user.saved_stories) == 0:
            is_empty = True
        return render_template("/users/user.html", user=user, is_empty=is_empty)


@app.route('/story/<int:story_id>/open')
def open_story_link(story_id):
    """Opens url associated with story when link is clicked"""
    story = Story.query.get(story_id)
    user = User.query.get(g.user.id)
    user.history.append(story)
    db.session.commit()
    return redirect(f"{story.url}")


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
        return redirect("/user/saved")


@app.route('/story/<int:story_id>/delete_story', methods=["POST"])
def delete_story(story_id):
    if g.user.id != session[CURR_USER_KEY]:
        flash("Please log-in and try again.", "danger")
        return redirect("/")

    else:
        story = Story.query.get(story_id)
        user = User.query.get(g.user.id)
        user.saved_stories.remove(story)
        db.session.commit()
        return redirect("/user/saved")


@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        new_user = User.register(
            username, password, email, first_name, last_name)

        try:
            db.session.add(new_user)
            db.session.commit()
            do_login(new_user)
            return redirect('/headlines')
        except exc.SQLAlchemyError as e:
            if isinstance(e.orig, UniqueViolation):
                form.username.errors = [
                    "The username you entered is already taken. Please pick another one."]

            # https://www.youtube.com/embed/iBYCoLhziX4?showinfo=0&controls=1&rel=0&autoplay=1

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
            flash("Credentials verified. Logging in...", "success")
            return redirect('/headlines')
        else:
            form.username.errors = [
                "Invalid username or password. Please try again."]

    return render_template('login.html', form=form)


@app.route('/login/demo', methods=['POST'])
def login_demo_user():
    username = 'demo-user'
    password = 'demouser'
    user = User.authenticate(username, password)
    if user:
        do_login(user)
        return redirect('/headlines')
    else:
        print("Something went wrong when trying to authenticate demo user. Attemping registration.")
        try:
            User.register(
                username, password, 'demo@user.com', 'demo', 'user')
            user = User.authenticate(username, password)
            if user:
                do_login(user)
                return redirect('/headlines')
        except:
            print("something went wrong when trying to register demo user")
    return redirect('/login')


@app.route('/logout')
def logout():
    """Handle logout of user."""
    flash(f"You have successfully logged out.", "primary")
    do_logout()
    return redirect("/")


"""Sentiment Analysis API for individual stories"""


@app.route('/<int:story_id>/polarity', methods=['POST'])
def show_pol_calls(story_id):
    story = Story.query.get(story_id)
    score = polarize(story)

    if score == None:
        story.pol = "No Data"
    else:
        score = score['article_res']['result']
        story.pol = str(score)

    db.session.commit()

    return jsonify({'response': story.pol})


@app.route('/<int:story_id>/subjectivity', methods=['POST'])
def show_sub_calls(story_id):

    story = Story.query.get(story_id)

    score = subjectize(story)
    if score == None:
        story.sub = "No Data"

    else:
        score = score['measure']
        story.sub = str(score)

    db.session.commit()

    return jsonify({'response': story.sub})


# test functions, remove when app is ready


# def sub(headlines):
#     for article in headlines:
#         result = subjectize(article)
#         print(headlines.index(article))
#         print(result)
#     return "all done"


# def pol(headlines):
#     for article in headlines:
#         result = polarize(article)
#         print(headlines.index(article))
#         print(result)
#     return "all done"


# @app.route('/')
# def slideshow():
#     if CURR_USER_KEY in session:
#         # DELETE THIS. this is only to limit the number of api calls
#         user = User.query.get(g.user.id)
#         user_queried_stories = user.queried_stories
#         first = user_queried_stories[0]
#         headlines = user_queried_stories
#         top_story = first
#         business = user_queried_stories
#         business1 = first
#         entertainment = user_queried_stories
#         entertainment1 = first
#         health = user_queried_stories
#         health1 = first
#         sports = user_queried_stories
#         sports1 = first
#         technology = user_queried_stories
#         technology1 = first
#         science = user_queried_stories
#         science1 = first

#         return render_template('/homepage.html',
#                                headlines=headlines,
#                                top_story=top_story,
#                                business=business,
#                                business1=business1,
#                                ent=entertainment,
#                                ent1=entertainment1,
#                                health=health,
#                                health1=health1,
#                                science=science,
#                                science1=science1,
#                                sports=sports,
#                                sports1=sports1,
#                                tech=technology,
#                                tech1=technology1
#                                )
