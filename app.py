# flask, local, and system imports
import os
from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session, g
from models import connect_db, db, User, Story, QueriedStory, TestQ

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

# from flask_debugtoolbar import DebugToolbarExtension
from flask_bcrypt import Bcrypt

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

# fix slideshow problem
# make demo user
# make sure im using proper RESTful terminology
# revisit show_pol_calls, show_sub_calls, understand what they're doing
# Figure out how to associate default query search with user. start by figuring out if migrations are neccessary
# Instead of changing current search query to sqlobject instead of session[dict],
# convert sqlobject to session[dict] when the time comes to incorporate that feature
# look up many to one relationships in sqlalchemy. saved_queries is a many to many relationship, but should be accessible as many to 1 with a simple foreign key. use user.filter to get foreign key
# implement saved queries (quick queries feauture)
# remove user history and notes from models and add to v2 branch
# change TestQ to "Query"
# change "QueriedStories" to "ReturnedStories" or "Call Results" or "Query Results"
# write parallel requests or loading progress bar
# add security
# add error handling, testing

# When deploying:
# watch out for <link rel="stylesheet" href="http://127.0.0.1:5000/static/app.css"> that links css file. the absolute
# path of the local route was included to fix nested routes bootstrap bug. figure out how to fix this in production
# make sure api key is hidden and works


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
        print("***saved queries", g.user.saved_queries)
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
    """View function for all results"""
    # todo: after changing all queries to database queries, combine route with "results" view function
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


@app.route('/simple', methods=['GET'])
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


@app.route('/search', methods=['GET', 'POST'])
def search_params():
    """This function creates a dictionary extracting data from the search form to be sent to the news-api"""
    if CURR_USER_KEY in session:
        form = SearchForm()
        if form.validate_on_submit():
            try:
                make_session_query(form)
                if form.saved_query.data:
                    add_saved_query(g.user.id, form)
                api_call(session['dict'], g.user.id)
                return redirect('/search_results')
            except:
                return render_template('/users/search.html', form=form)
        else:
            return render_template('/users/search.html', form=form)


@app.route('/search_results')
def handle_results():
    # write logic for if no results are found
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


@app.route(f'/<category>')
def show_for_category(category):
    """Display top headlines for given category based off of link clicked from homepage"""
    category = category.lower()
    results = cat_calls(category)
    return render_template('show_stories.html', results=results)


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


@app.route('/logout')
def logout():
    """Handle logout of user."""
    flash(f"You have successfully logged out.", "primary")
    do_logout()
    return redirect("/")


"""Helper Functions"""


def order_pol():
    """Loops over a User's Queried Stories results, orders by polarity,
    and filters stories with no results"""
    user = User.query.get(g.user.id)
    if user.queried_stories:
        results = []
        for story in user.queried_stories:
            # WRITE PARALLEL AXIOS REQUESTS
            id = story.id
            score = polarize(story)

            if score == None:
                QueriedStory.query.filter_by(story_id=id).delete()
                db.session.commit()

            else:
                result = score['article_res']['result']
                story.pol = str(result)
                db.session.commit()

        for result in user.queried_stories:
            results.append(result)

        ordered = sorted(user.queried_stories,
                         key=lambda story: story.pol,
                         reverse=True)

        return ordered


def order_sub():
    """Loops over a User's Queried Stories results, orders by subjectivity,
    and filters stories with no results"""
    user = User.query.get(g.user.id)
    if user.queried_stories:
        for story in user.queried_stories:
            id = story.id
            score = subjectize(story)
            if score == None:
                QueriedStory.query.filter_by(story_id=id).delete()
                db.session.commit()
            else:
                story.sub = str(score['measure'])
                db.session.commit()
        ordered = sorted(user.queried_stories,
                         key=lambda story: story.sub, reverse=True)
        # CHANGE THESE SO THAT THEY SORT BY SUBJECTIVITY NUMBERS NOT RESULT SAME WITH POLARITY
        # ASK TA IF THEY KNOW OF PROGRESS BAR
        return ordered


def transfer_db_query_to_session(query):
    """Converts a saved query to session[dict]"""
    dict = {}
    dict['keyword'] = query.keyword
    dict['source'] = query.source
    dict['quantity'] = query.quantity
    dict['date_from'] = query.date_from
    dict['date_to'] = query.date_to
    dict['language'] = query.language
    dict['sa'] = query.sa
    dict['sort_by'] = query.sort_by
    return dict


def make_session_query(form):
    dict = {}
    dict['keyword'] = form.keyword.data
    dict['source'] = form.source.data
    dict['quantity'] = form.quantity.data
    dict['date_from'] = form.date_from.data
    dict['date_to'] = form.date_to.data
    dict['language'] = form.language.data

    if form.sort_by.data == "subjectivity" or form.sort_by.data == "polarity":
        dict['sa'] = form.sort_by.data
        dict['sort_by'] = 'relevancy'
    else:
        dict['sort_by'] = form.sort_by.data
        dict['sa'] = None
    session['dict'] = dict

    return dict


def add_saved_query(user_id, form):
    """Adds saved query to associated user in db"""
    user = User.query.get(user_id)
    print('got userid')
    keyword = form.keyword.data
    source = form.source.data
    quantity = form.quantity.data
    date_from = form.date_from.data
    date_to = form.date_to.data
    language = form.language.data
    default = form.default.data
    if form.sort_by.data == "subjectivity" or form.sort_by.data == "polarity":
        sa = form.sort_by.data
        sort_by = 'relevancy'
    else:
        sort_by = form.sort_by.data
        sa = None
        query = TestQ(user_id=g.user.id,
                      keyword=keyword,
                      source=source,
                      quantity=quantity,
                      date_from=date_from,
                      date_to=date_to,
                      language=language,
                      default=default,
                      type="detailed_search",
                      sa=sa,
                      sort_by=sort_by
                      )

        db.session.add(query)
        db.session.commit()
        user.saved_queries.append(query)


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

    '''we need to make sure the response is in json for axios to retrieve it'''

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
