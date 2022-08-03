from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, DateField, BooleanField, DateTimeField
from wtforms.validators import InputRequired, Optional, NumberRange
import datetime as dt


class RegisterForm(FlaskForm):
    '''form to add a new user. Username, password, and email required'''
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    email = StringField("Email")
    first_name = StringField("First Name")
    last_name = StringField("Last Name")


class LoginForm(FlaskForm):
    '''form to login user with username and password'''
    username = StringField("Username", validators=[
                           InputRequired(message="Please enter a username")])
    password = PasswordField("Password", validators=[
                             InputRequired(message="Please enter a password")])


class SearchForm(FlaskForm):
    keyword = StringField("Enter a search term:", validators=[Optional()])

    source = SelectField("Choose source:", choices=[
        ('', 'All'), ('abc-news', 'ABC News'), ('al-jazeera-english',
                                                'Al Jazeera'), ('associated-press', 'Associated Press'), ('axios', 'Axios'),
        ('bbc-news', 'BBC News'), ('bloomberg', 'Bloomberg'), ('cbc-news',
                                                               'CBC News'), ('cbs-news', 'CBS News'), ('cnn', 'CNN'), ('fox-news', 'Fox News'),
        ('google-news', 'Google News'), ('independent', 'Independent'), ('msnbc',
                                                                         'MSNBC'), ('nbc-news', 'NBC News'), ('politico', 'Politico'),
        ('reuters', 'Reuters'), ('the-hill', 'The Hill'), ('the-huffington-post',
                                                           'The Huffington Post'), ('the-wall-street-journal', 'The Wall Street Journal'),
        ('the-washington-post', "The Washington Post"), ('time', 'Time'), ('usa-today', 'USA Today'), ('vice-news', 'Vice News')],
        validators=[Optional()])

    quantity = IntegerField("Enter # of many articles you want returned (max 15):",
     default=10, validators=[
    NumberRange(min=1, max=15, # this is represented by the "pageSize" parameter in the API where default and max are both set to 100
    message="Please enter a number between 1 and 10")]) 


    date_from = DateField("Select a starting date:", validators=[Optional()])
    date_to = DateField("Up until which date?",  # API default if will be newest to oldest with no limit 
    default=dt.datetime.today, validators=[Optional()])

    language = SelectField("Choose which language you want to see results from:", choices=[ # API default is all languages

        ('en', 'English'), ('es', 'Spanish'), ('fr', 'French'),
        ('ar', 'Arabic'), ('he', 'Hebrew'), ('he', 'Hebrew'), ('it', 'Italian'),
        ('nl', 'Dutch'), ('no', 'Norwegian'), ('pt', 'Portuguese'), ('ru', 'Russian'),
        ('zh', 'Chinese'), ('se', 'Swedish')],
        validators=[Optional()]) # can't find 'ud' language code as specified by api

    sort_by = SelectField("Search by:", choices=[('relevancy', 'Relevant'), ('popularity', 'Popular'), ('publishedAt', 'Recent'), # API default: publishedAt 
                                                 ('polarity', 'Polarity (results ordered from positive to negative)'), 
                                                 ('subjectivity', 'Objectivity (results ordered from objective to subjective)')], validators=[Optional()])

    default = BooleanField(
        "Make this your default search settings for your home page feed?")

    saved_query = BooleanField(
        "Would you like to add this to your saved search queries?")

    name = StringField("Give your saved search query a name (if applicable)", validators=[Optional()])
