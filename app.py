import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request
from forms import EventDetailsForm
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
from models import User, Event, EventType, VendorType, EventTypeVendors, EventChecklist

# Secret key
app.secret_key = env.get("APP_SECRET_KEY")
GOOGLE_MAPS_API_KEY = env.get("GOOGLE_MAPS_API_KEY")

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

    # check is user has events
    has_event = Event.query.filter_by(user_id=user.user_id).first() is not None
    if has_event:
        return redirect(url_for("my_events"))
    else:
        return redirect(url_for("newEvent_type"))


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

# MY EVENTS
@app.route("/my-events", methods=["GET", "POST"])
def my_events():
    # check user logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]

    # find users events
    events = (
        db.session.query(Event)
        .filter(Event.user_id == user_id)
        .all()
    )

    # saved selected event to session
    if request.method == "POST":
        selected_event_id = int(request.form["event_id"])

        # check belongs to user
        event = Event.query.filter_by(event_id=selected_event_id, user_id=user_id)
        
        session["event_id"] = selected_event_id
        return redirect(url_for("eventDashboard"))


    return render_template("events/myEvents.html", events=events)

# NEW EVENT
# event type
@app.route('/new-event/type', methods=["GET", "POST"])
def newEvent_type():
    # check user logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # POST: save type to session
    if request.method == "POST":
        session["newEvent_typeID"] = int(request.form["event_type_id"])
        # remove event details if user changes type
        session.pop("newEvent_details", None)
        return redirect(url_for("newEvent_details"))
    # GET: populate form with event types
    event_types = EventType.query.all()
    return render_template(
        "events/newEvent_type.html", event_types=event_types
    )

# event details 
@app.route("/new-event/details", methods=["GET", "POST"])
def newEvent_details():
    # check fk in session
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if "newEvent_typeID" not in session:
        return redirect(url_for("newEvent_type"))
    
    saved = session.get("newEvent_details")

    form = EventDetailsForm() # show form
    
    # POST: save in session if validation passed
    if form.validate_on_submit():
        session["newEvent_details"] = {
            "event_name": form.event_name.data.strip(),
            "overall_budget": request.form.get("overall_budget", ""),
            "capacity": request.form.get("capacity", ""),
            "event_date": request.form.get("event_date", ""),
            "location_id": request.form.get("location_id", ""),
            "location_name": request.form.get("location_name", ""),
        }
        return redirect(url_for("newEvent_todolist"))

    saved = session.get("newEvent_details", {})
    return render_template(
        "events/newEvent_details.html", google_api=GOOGLE_MAPS_API_KEY, form=form, saved=saved
    )

# TO DO LIST / SAVE NEW EVENT TO DB
@app.route("/new-event/todolist", methods=["GET", "POST"])
def newEvent_todolist():
    # check fk in session
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if "newEvent_typeID" not in session:
        return redirect(url_for("newEvent_type"))
    
    if "newEvent_details" not in session:
        return redirect(url_for("newEvent_details"))
    
    # get session data
    user_id = session["user_id"]
    event_type_id = int(session["newEvent_typeID"])
    details = session["newEvent_details"]

    # get recommended vendors by event type id
    vendors = (
        db.session.query(VendorType)
        .join(EventTypeVendors, VendorType.vendor_type_id == EventTypeVendors.vendor_type_id)
        .filter(EventTypeVendors.event_type_id == event_type_id)
        .order_by(VendorType.vendor_type.asc())
        .all()
    )

    # POST
    if request.method == "POST":
        # save selected vendor ids
        selected_checklist = request.form.getlist("checklist")

        # convert str back to correct data type
        capacity = int(details["capacity"])
        event_date = datetime.strptime(details["event_date"], "%Y-%m-%d").date()

        # create new event
        new_event = Event(
            user_id=user_id,
            event_type_id=event_type_id,
            event_name=details["event_name"],
            overall_budget=details["overall_budget"],
            capacity=capacity,
            event_date=event_date,
            location_id=details["location_id"],
        )

        # commit new_event
        db.session.add(new_event)
        db.session.commit()

        for vendor_type_id in selected_checklist:
            checklist = EventChecklist(
                event_id=new_event.event_id,
                vendor_type_id=int(vendor_type_id)
            )
            db.session.add(checklist)
        db.session.commit()

        session.pop("newEvent_typeID", None)
        session.pop("newEvent_details", None)

        return redirect(url_for("eventDashboard"))



    return render_template("events/newEvent_todolist.html", vendors=vendors)


# EVENT DASHBOARD
@app.route("/event-dashboard")
def eventDashboard():
    return render_template("eventDashboard.html")

if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)

