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
        'DATABASE_URL', 'postgresql:///news-tracker7')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql:///news-tracker7').replace("://", "ql://", 1)

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


server_session = Session(app)


# Todo:

# rewrite session results as object to increase speed of look-up
# write logic for if saved query is current date: to = None
# Redeploy!
# re-write polarity ordering
# write else statement for if user not in session
# Redeploy!
# add more error handling, testing
# Redeploy!
# more permanent fix for slideshows
# create separate .env file for app config 
# change the date_from to automatically be one month out from present day, newstracker free tier only allows for one month in the past 



# When deploying:
# watch out for <link rel="stylesheet" href="http://127.0.0.1:5000/static/app.css"> that links css file. the absolute
# path of the local route was included to fix nested routes bootstrap bug. figure out how to fix this in production
# make sure api key is hidden and works
# connect redis to heroku

#TODONOW: 
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
        # return redirect("/login")
        no_user = True
        if g.user:
            no_user = False
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
        return render_template('/homepage.html', data=data, no_user=no_user)


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
        form = SearchForm()
        if form.validate_on_submit():
            try:
                query = make_session_query(form)
                if form.saved_query.data or form.default.data:
                    add_saved_query(g.user.id, form)
                advanced_search_call(query)
                return redirect('/search/results')
            except:
                return render_template('/search.html', form=form)
        else:
            return render_template('/search.html', form=form)
    else:
        flash("You do not have permission to view this page. Please log-in and try again.", "danger")
        return redirect("/login")

@app.route('/search/<int:query_id>')
def search_user_queries(query_id):
    """Makes advanced search call based off of pre-saved query"""
    if CURR_USER_KEY in session:
        query_obj = Query.query.get(query_id)
        query_dict = transfer_db_query_to_dict(query_obj)
        advanced_search_call(query_dict)
        return redirect('/search/results')
    else:
        flash("You do not have permission to make this action. Please log-in and try again.", "danger")
        return redirect("/login")


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
            return render_template('/show_stories.html', results=results)
    else:
        flash("You do not have permission to view this page. Please log-in and try again.", "danger")
        return redirect("/login")
    return render_template('/show_stories.html', results=results)


@app.route('/search/simple', methods=['GET'])
def search_simple():
    """API Call and Results for Simple Search"""
    keyword = request.args.get("search")
    results = simple_search_call(keyword)
    return render_template('/show_stories.html', results=results)

    
@app.route('/user/saved')
def user_saved():
    if CURR_USER_KEY in session:
        user = User.query.get(g.user.id)
        is_empty = False
        if len(user.saved_stories) == 0:
            is_empty = True
        if "saved" in session:
            session.pop("saved")
        session["saved"] = [story for story in user.saved_stories]
        return render_template("/user.html", user=user, is_empty=is_empty)
    else:
        flash("You do not have permission to view this page. Please log-in and try again.", "danger")
        return redirect("/login")


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
                      published_at=session_story['published_at'], id=session_story['id'], user_id = g.user.id)
        try:
            db.session.add(story)
            db.session.commit()

        except exc.SQLAlchemyError as e:
            if isinstance(e.orig, UniqueViolation):
                flash(f'The story "{story.headline}" already exists in your saved stories.', 'danger')
                return redirect("/user/saved")            
        return redirect("/user/saved")
    else:
        flash("You do not have permission to make this action. Please log-in and try again.", "danger")
        return redirect("/login")


@app.route('/story/<id>/delete_story', methods=["POST"])
def delete_story(id):
    if CURR_USER_KEY in session:
        Story.query.filter_by(id=id).delete()
        db.session.commit()
        return redirect("/user/saved")
    else:
        flash("You do not have permission to make this action. Please log-in and try again.", "danger")
        return redirect("/login")


@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form = RegisterForm(prefix='form-register-')
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
            flash("Congratulations! You have successfully created an account.", "success")
            do_login(new_user)
            return redirect('/headlines')
        except exc.SQLAlchemyError as e:
            if isinstance(e.orig, UniqueViolation):
                form.username.errors = [
                    "The username you entered is already taken. Please pick another one."]
            # https://www.youtube.com/embed/iBYCoLhziX4?showinfo=0&controls=1&rel=0&autoplay=1
    else:
        print("Form Not Validated")
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
            flash("Credentials verified. You are now logged in.", "success")
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
    if CURR_USER_KEY in session:
        flash(f"You have successfully logged out.", "success")
        user = User.query.get(g.user.id)
        do_logout(user)
        return redirect("/headlines")
    else:
        return redirect("/login")



"""Sentiment Analysis API for individual stories"""


@app.route('/story/<id>/polarity', methods=['POST'])
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

@app.route('/story/<id>/subjectivity', methods=['POST'])
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

@app.route('/user/<int:query_id>/delete', methods=['POST'])
def delete_query(query_id):
    if CURR_USER_KEY in session:
        Query.query.filter_by(id=query_id).delete()
        db.session.commit()
        return jsonify({'response': f"Query deleted!"})
    else:
        flash("You do not have permission to make this action. Please log-in and try again.", "danger")
        return redirect("/login")



"""Restful Server-Side API"""

"""USERS"""

@app.route('/users', methods=["GET"])
def get_all_users():
    """Gets all users"""
    if CURR_USER_KEY in session:
        users = User.query.all()
        dict_list = [transfer_db_user_to_dict(user) for user in users]
        return jsonify(users = dict_list)

@app.route('/users/delete', methods=["DELETE"])
def delete_all_users():
    """Deletes all users"""
    if CURR_USER_KEY in session:
        try:
            User.query.delete()
            db.session.commit()
        except exc.SQLAlchemyError as e:
            response = {"Unable to delete all users": f"{e.origin}"}
            return response
        return {"message":"Success! All users were deleted."}

@app.route('/users/<int:user_id>', methods=["GET"])
def get_user(user_id):
    """Gets a user by user_id"""
    if CURR_USER_KEY in session:
        user = User.query.get(user_id)
        dict = transfer_db_user_to_dict(user)
        return jsonify(user = dict)

@app.route('/users/<int:user_id>', methods=["DELETE"])
def delete_user(user_id):
    """Deletes a user by user_id"""
    if CURR_USER_KEY in session:
        try:
            User.query.filter_by(id=user_id).delete()
            db.session.commit()
            return {"message":"Success! User was deleted."}
        except exc.SQLAlchemyError as e:
            response = {"Unable to delete user": f"{e.origin}"}
            return response

@app.route('/users/new', methods=["POST"])
def new_user():
        """Creates a new user"""
        data = request.json['user']
        new_user = User.register(
            data['username'], data['password'], data['email'], data['first_name'], data['last_name'])
        try:
            db.session.add(new_user)
            db.session.commit()
            response = {"message": f"User {data['username']} added successfully."}
        except exc.SQLAlchemyError as e:
            if isinstance(e.orig, UniqueViolation):
                response = {"message": f"{e.origin}"}
            else:
                response = {"message": "Sorry, something went wrong. Unable to add new user to database."}
        return response

@app.route('/users/<int:user_id>/edit', methods=["PUT"])
def edit_user(user_id):
        """Edits a user's information by user_id"""
        user = User.query.get(user_id)
        data = request.json['user']
        user.username = data['username']
        hashed = bcrypt.generate_password_hash(data['password'])
        hashed_utf8 = hashed.decode("utf8")
        user.password = hashed_utf8
        user.email = data['email']
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        try:
            db.session.add(user)
            db.session.commit()
            dict = transfer_db_user_to_dict(user)
            return jsonify(updated_user = dict)
        except exc.SQLAlchemyError as e:
            if isinstance(e.orig, UniqueViolation):
                response = {"message": f"{e.origin}"}
            else: 
                response = {"message": "Sorry, something went wrong. Unable to update user."}
            return response

@app.route('/users/<int:user_id>/queries/new', methods=["POST"])
def new_query(user_id):
    """Creates a new query and associates it with user_id"""
    data = request.json['query']
    if data['sort_by'] == "subjectivity" or data['sort_by'] == "polarity":
        data['sa'] = data['sort_by']
        data['sort_by'] = 'relevancy'
    try:
        query = Query(user_id = user_id,
        name = data['name'],
        source = data['source'],
        quantity = data['quantity'], 
        date_from = data['date_from'],
        date_to = data['date_to'],
        language = data['language'], 
        sort_by = data['sort_by'],
        sa = data['sa'],
        type = data['type']
        )
        db.session.add(query)
        db.session.commit()
        dict = transfer_db_query_to_dict(query)
        return jsonify(new_query = dict)

    except exc.SQLAlchemyError as e:
        response = {"message": f"{e.origin}"}
        return response

@app.route('/users/<int:user_id>/queries/', methods=["GET"])
def get_all_queries_by_user(user_id):
    """Gets all queries matching user_id"""
    user = User.query.get(user_id)
    queries = user.queries
    dict_list = [transfer_db_query_to_dict(query) for query in queries]
    return jsonify(queries = dict_list)    

@app.route('/users/<int:user_id>/queries/<int:query_id>/edit', methods=["PUT"])
def edit_query(user_id, query_id):
    """Edits a User Query by User and Query ids"""
    data = request.json['query']
    query = Query.query.get(query_id)
    try:
        if user_id != query.user_id:
            raise ValueError("The user id is not associated with the query id.")
    except ValueError:
        response = {"Value Error": "The user id is not associated with the query id."}
        return response

    if data['sort_by'] == "subjectivity" or data['sort_by'] == "polarity":
        data['sa'] = data['sort_by']
        data['sort_by'] = 'relevancy'
    try:
        query.name = data['name'],
        query.source = data['source'],
        query.quantity = data['quantity'], 
        query.date_from = data['date_from'],
        query.date_to = data['date_to'],
        query.language = data['language'], 
        query.sort_by = data['sort_by'],
        query.sa = data['sa'],
        query.type = data['type']
        db.session.add(query)
        db.session.commit()
        dict = transfer_db_query_to_dict(query)
        return jsonify(updated_query = dict)

    except exc.SQLAlchemyError as e:
        response = {"Unable to update query": f"{e.origin}"}
        return response

@app.route('/users/<int:user_id>/queries/<int:query_id>/delete', methods=["DELETE"])
def delete_query(user_id, query_id):
    """Deletes a User Query by User and Query ids"""
    query = Query.query.get(query_id)
    try:
        if user_id != query.user_id:
            raise ValueError("The user id is not associated with the query id.")
    except ValueError:
        response = {"Value Error": "The user id is not associated with the query id."}
        return response

    try:
        Query.query.filter_by(id=query_id).delete()
        db.session.commit()
        return {"message":"Success! Query was deleted."}
    except exc.SQLAlchemyError as e:
        response = {"Unable to delete query": f"{e.origin}"}
        return response

"""QUERIES"""

@app.route('/queries', methods=["GET"])
def get_all_queries():
    """Gets all queries"""
    if CURR_USER_KEY in session:
        queries = Query.query.all()
        dict_list = [transfer_db_query_to_dict(query) for query in queries]
        return jsonify(queries = dict_list)

@app.route('/queries/<int:query_id>', methods=["GET"])
def get_query(query_id):
    """Gets a query by query_id"""
    if CURR_USER_KEY in session:
        query = Query.query.get(query_id)
        dict = transfer_db_query_to_dict(query)
        return jsonify(query= dict)


"""STORIES"""

@app.route('/stories', methods=["GET"])
def get_all_stories():
    """Gets all stories"""
    if CURR_USER_KEY in session:
        stories = Story.query.all()
        dict_list = [transfer_db_story_to_dict(story) for story in stories]
        return jsonify(stories = dict_list)

@app.route('/stories/<story_id>', methods=["GET"]) #story ids are non-numerical as they are inherited from sessions randomly generated uuid() ids
def get_story(story_id):
    """Gets story by story id"""
    if CURR_USER_KEY in session:
        story = Story.query.get(story_id)
        dict = transfer_db_story_to_dict(story)
        return jsonify(story = dict)





#sample query:
#{"query": {"name":"test222", "source":"fox news", "quantity":10, "date_from":"", "date_to":"", "language":"en", "sort_by":"subjectivity", "sa":"", "type":"Detailed Search"}}
#sample user:
# {"user": {"username":"coolguy41", "password":"hmmm", "email":"eee@mail.com", "first_name":"first", "last_name":"last"}}