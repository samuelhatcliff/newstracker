# flask, local, and system imports
import os
import creds
from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session, g
from models import connect_db, db, User, Story, Query
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()

# imports from other modules in directory
from forms import RegisterForm, LoginForm, SearchForm
from api_calls import *
from sent_analysis import subjectize, polarize

# sqlalchemy imports
from sqlalchemy import exc
from psycopg2.errors import UniqueViolation

# import all helper functions
from helpers import *

# set-up app
CURR_USER_KEY = "curr_user"
app = Flask(__name__)
production = False
if not production:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql:///news-tracker6')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql:///news-tracker6').replace("://", "ql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
secret_key = os.environ.get(creds.secret_key)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", creds.secret_key)

connect_db(app)
# db.drop_all()
db.create_all()

#server-side session
from flask_session import Session
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_PERMANENT'] = False
#CHANGE THIS FOR REDEPLOYMENT
# app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:5000')

server_session = Session(app)


# Todo:

# write logic for if saved query is current date: to = None
# Redeploy!
# re-write polarity ordering
# write else statement for if user not in session
# Redeploy!
# add error handling, testing
# Redeploy!
# more permanent fix for slideshows
# find better way than "nested" to determine bootstrap path for nested routes
# create separate .env file for app config 


# When deploying:
# watch out for <link rel="stylesheet" href="http://127.0.0.1:5000/static/app.css"> that links css file. the absolute
# path of the local route was included to fix nested routes bootstrap bug. figure out how to fix this in production
# make sure api key is hidden and works
# connect redis to heroku

#TODONOW: -move templates out of nested structure
#-rewrite code and distinguish between session['saved] and session['results]

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


def do_logout(user):
    """Logout user."""
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


"""View functions for application"""

with app.app_context():
    @app.route('/')
    def homepage():
        """NewsTracker Homepage"""
        categories = ['business', 'entertainment',
                    'health', 'science', 'sports', 'technology']
        data = []
        results = async_reqs(categories)
        for index, result in enumerate(results):
            obj = {}
            obj['results'] = result
            obj['top_story'] = result[0]
            obj['name'] = categories[index].capitalize()
            data.append(obj)
        return render_template('/homepage.html', data=data, no_user=True)


@app.route('/headlines', methods=['GET', 'POST'])
def headlines():
    """Default Search Query if user logged in with a saved query as default"""
    if CURR_USER_KEY in session:
        user = User.query.get(g.user.id)
        queries = user.queries
        default = [query for query in queries if query.default]
        if default:
            return redirect(f"search/{default[0].id}")
        else:
            """Otherwise, Generic Top Headlines"""
            results = top_headlines_call()
            return render_template('/show_stories.html', results=results)
    results = top_headlines_call()
    return render_template('/show_stories.html', results=results)


@app.route(f'/headlines/<category>')
def show_for_category(category):
    """Display top headlines for given category based off link clicked from homepage"""
    category = category.lower()
    results = cat_calls(category, slideshow=False)
    return render_template('show_stories.html', results=results)


@app.route('/search', methods=['GET', 'POST'])
def search_form():
    """This function creates a dictionary extracting data from the search form to be sent to the news-api"""
    if CURR_USER_KEY in session:
        # todo: check to make sure I can't access this route if im not logged in
        form = SearchForm()
        if form.validate_on_submit():
            try:
                query = make_session_query(form)
                if form.saved_query.data or form.default.data:
                    add_saved_query(g.user.id, form)
                advanced_search_call(query)
                return redirect('/search/results')
            except:
                return render_template('/search.html', form=form, nested=True)
        else:
            return render_template('/search.html', form=form, nested=True)

@app.route('/search/<int:query_id>')
def search_user_queries(query_id):
    """Makes advanced search call based off of pre-saved query"""
    if CURR_USER_KEY in session:
        # todo: check to make sure I can't access this route if im not logged in
        query_obj = Query.query.get(query_id)
        query_dict = transfer_db_query_to_session(query_obj)
        advanced_search_call(query_dict)
        return redirect('/search/results')


@app.route('/search/results')
def handle_results():
    if CURR_USER_KEY in session:
        query = session['query']
        results = session['results']
        if query['sa'] == 'polarity':
            results = order_pol()
        elif query['sa'] == 'subjectivity':
            results = order_sub()
        else:
            return render_template('/show_stories.html', results=results, nested=True)
    return render_template('/show_stories.html', results=results, nested=True)


@app.route('/search/simple', methods=['GET'])
def search_simple():
    """API Call and Results for Simple Search"""
    keyword = request.args.get("search")
    results = simple_search_call(keyword)
    return render_template('/show_stories.html', results=results, nested=True)

    
@app.route('/saved')
def user():
    if CURR_USER_KEY in session:
        user = User.query.get(g.user.id)
        is_empty = False
        if len(user.saved_stories) == 0:
            is_empty = True
        if "saved" in session:
            session.pop("saved")
        session["saved"] = [story for story in user.saved_stories]
        return render_template("/user.html", user=user, is_empty=is_empty, nested=True)
    else:
        flash("Please log-in and try again.", "danger")
        return redirect("/")


@app.route('/story/<id>/open')
def open_story_link(id):
    """Opens url associated with story when link is clicked"""
    try:
        story = Story.query.get(id)
        return redirect(f"{story.url}")
    except:
        results = session['results']
        story = [story for story in results if story['id'] == id][0]
        return redirect(f"{story['url']}")

@app.route('/story/<id>/save_story', methods=["POST"])
def save_story(id):
    if CURR_USER_KEY in session:
        results = session["results"]
        session_story = [story for story in results if story['id'] == id][0]
        story = Story(headline=session_story['headline'], source=session_story['source'], content=session_story['content'],
                      author=session_story['author'], description=session_story['description'], url=session_story['url'], image=session_story['image'],
                      published_at=session_story['published_at'], id=session_story['id'])
        user = User.query.get(g.user.id)
        # REWRITE 
        # if story in user.saved_stories:
        #     flash("This story already exists in your saved stories.", "danger")
        #     return redirect("/")
        user.saved_stories.append(story)
        db.session.commit()
        return redirect("/saved")
    else:
        flash("Please log-in and try again.", "danger")
        return redirect("/")


@app.route('/story/<id>/delete_story', methods=["POST"])
def delete_story(id):
    if CURR_USER_KEY in session:
        story = Story.query.get(id)
        user = User.query.get(g.user.id)
        user.saved_stories.remove(story)
        db.session.commit()
        return redirect("/saved")
    else:
        flash("Please log-in and try again.", "danger")
        return redirect("/")


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
    user = User.query.get(g.user.id)
    do_logout(user)
    return redirect("/")


"""Sentiment Analysis API for individual stories"""


@app.route('/<id>/polarity', methods=['POST'])
def show_pol_calls(id):
    try:
        # check to see if id represents a sqlalchemy object that needs converted to dict to be fed to SA functions
        # write logic to save score to db if story saved
        db_story = Story.query.get(id)
        story = transfer_db_story_to_dict(db_story)
    except:
        results = session['results']
        story = [story for story in results if story['id'] == id][0]
    score = polarize(story)
    if not score:
        story['pol'] = "No Data"
    else:
        score = score['article_res']['result']
        story['pol'] = str(score)
    return jsonify({'response': story['pol']})

@app.route('/<id>/subjectivity', methods=['POST'])
def show_sub_calls(id):
    try:
        # check to see if id represents a sqlalchemy object that needs converted to dict to be fed to SA functions
        db_story = Story.query.get(id)
        story = transfer_db_story_to_dict(db_story)
    except:
        results = session['results']
        story = [story for story in results if story['id'] == id][0]
    score = subjectize(story)
    if not score:
        story['sub'] = "No Data"
    else:
        score = score['measure']
        story['sub']= str(score)
    return jsonify({'response': story['sub']})

@app.route('/query/<int:query_id>/delete', methods=['POST'])
def delete_query(query_id):
    #add security
    Query.query.filter_by(id=query_id).delete()
    db.session.commit()
    return jsonify({'response': f"Query deleted!"})


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
