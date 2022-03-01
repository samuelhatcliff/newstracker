from re import L
from flask import Flask, request, render_template, flash, redirect, render_template, jsonify, session, g
from models import connect_db, db, User, Story, QueriedStory, Note, SavedStory


from forms import RegisterForm, LoginForm, SearchForm
from api_calls import api_call, cat_calls
from sent_analysis import parse, subjectize, tokenize, polarize, sa_sum


from langcodes import Language
import psycopg2
import datetime as dt
import requests
from dateutil import parser
from newsapi import NewsApiClient



# from flask_debugtoolbar import DebugToolbarExtension 
from flask_bcrypt import Bcrypt

CURR_USER_KEY = "curr_user"


bcrypt = Bcrypt()


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///capstone'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = "topsecret1"
# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
# debug = DebugToolbarExtension(app)




# TODO: turn what is currently users/user.html into a template that is used for both the users saved stories, 
#as well as returning search results and loading the home page. Add error handling for stories where SA doesn't work
#then make sure the order functions are working (currently written under queries_stories model in db table, but proabably want)
#to change this. look up the difference between class methd and a regular method on a class

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


"""View functions for application"""
def math():
    user = User.query.get(g.user.id)
    if user.queried_stories:
        for story in user.queried_stories:
            story_id = story.id
            score = polarize(story)
     
            if score == None:
                QueriedStory.query.filter_by(id=story_id).delete()
                db.session.commit()
            else:
                result = score['article_res']['result']
                story.pol = str(result)
                db.session.commit()
        ordered = sorted(user.queried_stories, key = lambda story : story.pol, reverse=True )
      
        return ordered
        
def math2():
    user = User.query.get(g.user.id)
    if user.queried_stories:
        for story in user.queried_stories:
            id = story.id
            score = subjectize(story)
           
            if score == None:
   
                QueriedStory.query.filter_by(story_id =id).delete()
                db.session.commit()
        
            else:
                story.sub = str(score['measure'])
                db.session.commit()
        ordered = sorted(user.queried_stories, key = lambda story : story.sub, reverse=True )
        #CHANGE THESE SO THAT THEY SORT BY SUBJECTIVITY NUMBERS NOT RESULT SAME WITH POLARITY
        #ASK TA IF THEY KNOW OF PROGRESS BAR
        return ordered





@app.route('/sacalls/<int:story_id>/polarity', methods =['POST'])
def show_pol_calls(story_id):
 
    story = Story.query.get(story_id)

    score = polarize(story)
    if score == None:
        story.pol = "No Data"
        db.session.commit()
        return redirect('/user')
    

    score = score['article_res']['result']
    story.pol = str(score)
 
    db.session.commit()
    return redirect('/user')

@app.route('/sacalls/<int:story_id>/subjectivity', methods =['POST'])
def show_sub_calls(story_id):
    
    story = Story.query.get(story_id)
    
    score = subjectize(story)
    if score == None:
        story.sub = "No Data"
        db.session.commit()
        return redirect('/user')


    else:
        score = score['measure']

    story.sub = str(score)
    db.session.commit()
    return redirect('/user')



@app.route('/', methods= ['GET', 'POST'])
def home_page():
    if CURR_USER_KEY in session:
        user = User.query.get(g.user.id)
        if not user.queried_stories:
            headlines = api_call(None)
            return render_template('/show_stories.html', headlines=headlines)
        user_queried_stories = user.queried_stories

        headlines = user_queried_stories
 
        return render_template('/show_stories.html', headlines=headlines)
    else:
        headlines = api_call(None)
        return render_template('/show_stories.html', headlines=headlines)


@app.route('/search', methods= ['GET', 'POST'])
def search_params():
    """This function creates a dictionary extracting data from the search form to be sent to the news-api"""
    user = User.query.get(g.user.id)
    form = SearchForm()
    if form.validate_on_submit():
        try:
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
            dict['default'] = form.default.data
            
            if dict['default'] == True:
                default_str = str(dict)
                user.default_search = default_str
                db.session.commit()
            session['dict'] = dict
            #using the query information we make an api call and safe that data to user.searched_queries
            api_call(dict, g.user.id)
           
            return redirect('/results')

        except:
            flash("hmmmm. does this appear, or messages from form validators?", 'danger')
            return render_template('/users/search.html', form = form)
    else:
        return render_template('/users/search.html', form = form)
  

@app.route('/results')
def results():
    #write logic for if no results are found
    if CURR_USER_KEY in session:
        dict = session['dict']
        user = User.query.get(g.user.id)
        user_queried_stories = user.queried_stories
      
        headlines = user_queried_stories

        if dict['sa'] == 'polarity':
            headlines = math()
        elif dict['sa'] == 'subjectivity':
            headlines = math2()
        else:
            return render_template('/show_stories.html', headlines=headlines)

    return render_template('/show_stories.html', headlines=headlines)



 

@app.route('/slideshow')
def slideshow():
    if CURR_USER_KEY in session:
        #DELETE THIS. this is only to limit the number of api calls 
        user = User.query.get(g.user.id)
        user_queried_stories = user.queried_stories
        first = user_queried_stories[0]
        headlines = user_queried_stories
        top_story = first
        business = user_queried_stories
        business1 = first
        entertainment = user_queried_stories
        entertainment1 = first
        health =user_queried_stories
        health1 = first
        sports = user_queried_stories
        sports1 = first
        technology = user_queried_stories
        technology1 = first
        science = user_queried_stories
        science1 = first

        return render_template('/homepage.html',
    headlines=headlines,
    top_story=top_story, 
    business= business, 
    business1 = business1,
    ent = entertainment,
    ent1 = entertainment1,
    health = health,
    health1 = health1,
    science = science,
    science1 = science1,
    sports = sports,
    sports1 = sports1,
    tech = technology, 
    tech1 = technology1
    )

    headlines = api_call(None)
    top_story = headlines.pop(0)

    business = cat_calls('business')
    business1 = business.pop(0)

    entertainment = cat_calls('entertainment')
    entertainment1 = entertainment.pop(0)

    health = cat_calls('health')
    health1 = health.pop(0)

    science = cat_calls('science')
    science1 = science.pop(0)

    sports = cat_calls('sports')
    sports1 = sports.pop(0)

    technology = cat_calls('technology')
    technology1 = technology.pop(0)

    return render_template('/homepage.html',
    headlines=headlines,
    top_story=top_story, 
    business= business, 
    business1 = business1,
    ent = entertainment,
    ent1 = entertainment1,
    health = health,
    health1 = health1,
    science = science,
    science1 = science1,
    sports = sports,
    sports1 = sports1,
    tech = technology, 
    tech1 = technology1
    )


    # if CURR_USER_KEY in session:
    #     user = User.query.get(g.user.id)
    #     if not user.queried_stories:
    #         headlines = api_call(None)
    #         top_story = headlines.pop(0)
    #         return render_template('/homepage.html', headlines=headlines, top_story=top_story)
    #     user_queried_stories = user.queried_stories

    #     headlines = user_queried_stories
    #     top_story = headlines.pop(0)
    #     return render_template('/homepage.html', headlines=headlines, top_story=top_story)
    # else:
    #     headlines = api_call(None)
    #     top_story = headlines.pop(0)
    #     return render_template('/homepage.html', headlines=headlines, top_story=top_story)
 
    
    




@app.route('/simple', methods = ['GET'])
def search_simple():
    keyword = request.args.get("search")
    if CURR_USER_KEY in session:
        user = User.query.get(g.user.id)
        
        api_call(keyword, g.user.id)
        headlines = user.queried_stories
    else:
        results = api_call(keyword)
        headlines = results

    return render_template('/show_stories.html', headlines=headlines)


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
        # ordered = order_stories_recent(user.saved_stories)
        # user.saved_stories = ordered
        is_empty = False
        if len(user.saved_stories) == 0:
            is_empty = True
        return render_template("/users/user.html", user = user, is_empty = is_empty)


@app.route('/story/<int:story_id>/open')
def open_story_link(story_id):   
        story = Story.query.get(story_id)
        user = User.query.get(g.user.id)
        user.history.append(story)
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
            flash("Congratulations! You Have Successfully Created Your Account", "success")
            return redirect('/')

        except IntegrityError:
            form("Username already taken, please try again", 'danger')
            # or form.username.errors.append('Username already taken. Please pick another')
            #https://www.youtube.com/embed/iBYCoLhziX4?showinfo=0&controls=1&rel=0&autoplay=1
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
            flash("Credentials verified. Logging in...", "success")
            return redirect('/')

        else:
            form.username.errors=["Invalid username or password. Please try again."]

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    flash(f"You have successfully logged out.", "primary")
    do_logout()
    return redirect("/")


#test functions, remove when app ready

@app.route(f'/<category>')
def show_for_category(category):
    results = cat_calls(category)
    return render_template('show_stories.html', headlines = results)

    """Display top headlines for given category based off of link clicked from homepage"""

def sub(headlines):
    for article in headlines:
        result = subjectize(article)
        print(headlines.index(article))
        print(result)
    return "all done"

def pol(headlines):
    for article in headlines:
        result = polarize(article)
        print(headlines.index(article))
        print(result)
    return "all done"