from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, DateField, BooleanField
from wtforms.validators import InputRequired, Optional, NumberRange

class RegisterForm(FlaskForm):
    '''form to add a new user. Username, password, and email required'''
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    email = StringField("Email")  
    first_name = StringField("First Name")
    last_name = StringField("Last Name")
    
    

class LoginForm(FlaskForm):
    '''form to login user with username and password'''
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])

class SearchForm(FlaskForm):
    keyword = StringField("Enter a search term", validators= [Optional()])
    #if this field is empty, the get_top_headlines function should be called instead
    source = StringField("Enter name of source", validators= [Optional()])
    # could potentially allow for multiple sources to be searched later. From API docs:
    #A comma-seperated string of identifiers (maximum 20) for the news sources or blogs you want headlines from. Use the /sources 
    # endpoint to locate these programmatically or look at the sources index.
    quantity = IntegerField("Enter of many articles you want returned (max 10)", validators = [NumberRange(min=1, max=10, message ="Please enter a number between 1 and 10")])
    #this is represented by the "pageSize" parameter in the API. The default and max are both set to 100.
    #figure out how to change this default to 10

    search_in = SelectField("Search for:", choices=[('headline', 'Headline'), ('description', 'Description'), ('content', 'Content')], validators= [Optional()])
    #SelectField as written here doesn't allow for data to be accessed from form in search_params(). Something here must be written wrong. Refer to previous other
    #assignments where i have used SelectField

    #default from api: all fields are searched
    date_from = DateField("Select a date range", validators= [Optional()])
    date_to = DateField("Up until which date?", validators= [Optional()])
   #API default if will be newest to oldest with no limit
    language = SelectField("Choose which language you want to see results from", choices = [
    ('en', 'English'), ('es', 'Spanish'), ('fr', 'French'), ('ar', 'Arabic'), ('he', 'Hebrew'), ('he', 'Hebrew'), ('it', 'Italian'),
    ('nl', 'Dutch'), ('no', 'Norwegian'),('pt', 'Portuguese'), ('ru', 'Russian'), ('zh', 'Chinese'), ('se', 'Swedish')],
    validators= [Optional()]
    )
    #can't find 'ud' language code (which is specificied by the api), try to run a search with ud as part of query to figure out what it is
    #API default is all languages. Set to english if this becomes problematic
    sort_by = SelectField("Search by", choices=[('relevancy', 'Relevant'), ('popularity', 'Popular'), ('publishedAt', 'Recent'), 
    ('polarity', 'Polarity'), ('subjectivity', 'Subjectivity')], validators= [Optional()])
    #API default: publishedAt. subjectivity and polarity might take more time as individual get requests are needed for each url. This data
    #comes from our own logic, rather than the API's
    default = BooleanField("Make this your default search settings for your home page feed")






    
