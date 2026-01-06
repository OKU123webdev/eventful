import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for
from datetime import datetime
from database import db


# enviroments file
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
# Database
app.config['SQLALCHEMY_DATABASE_URI'] = ('mysql+pymysql://'+env.get('DB_USER')+':'+quote_plus(env.get('DB_PASSWORD'))+'@'+env.get('DB_HOST')+':'+env.get('DB_PORT')+'/'+env.get('DB_NAME'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app) # Initilise db
from models import User # import model

# Secret key
app.secret_key = env.get("APP_SECRET_KEY")

# Auth0
oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)


# ROUTES
# Homepage/Index
@app.route('/')
def homepage():
    return render_template('index.html')

# AUTH0
# login
@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

# callback route
@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token

    # DATABASE LOGIC
    auth0_id = token["userinfo"]["sub"] # get auth0 id (sub)
    # check db for user
    user = User.query.filter_by(auth0_id=auth0_id).first() 
    if user is None: # add is doesnt exist
        user = User(auth0_id=auth0_id)
        db.session.add(user)
        db.session.commit()
    session["user_id"] = user.user_id

    return redirect("/")

# logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("homepage", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)

