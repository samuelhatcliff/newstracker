# flask, config, and env imports
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
app = Flask(__name__)
if app.config["ENV"] == "production":
    app.config.from_object('config.ProductionConfig')
elif app.config["ENV"] == "development":
    app.config.from_object('config.DevelopmentConfig')
else:
    app.config.from_object('config.TestingConfig')

#server-side session
CURR_USER_KEY = "curr_user"
from flask_session import Session
server_session = Session(app)

#db set-up
from models import connect_db, db
connect_db(app)
db.create_all()

#view imports
from views import sa_views, site_views, api

#todo: write app.before_request middleware for security, include here 