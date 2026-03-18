import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request, jsonify
from forms import EventDetailsForm
from datetime import datetime
from datetime import date
from database import db

# ORM - join db queries
from sqlalchemy.orm import joinedload
# sql functions
from sqlalchemy import func

# ENVIROMENTS FILE
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)

# DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mysql+pymysql://'
    +env.get('DB_USER')
    +':'+quote_plus(env.get('DB_PASSWORD'))
    +'@'+env.get('DB_HOST')+':'
    +env.get('DB_PORT')
    +'/'+env.get('DB_NAME')
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app) # Initilise db

# IMPORT MODELS
from models import User, Event, EventType, VendorType, EventTypeVendors, EventChecklist, VendorInteractions, VendorBudget, Spending

# IMPORT CRUD FUNCTIONS
from vendors.vendor_crud import (
    mark_as_interested,
    get_selected_vendors,
    remove_interested_vendor,
    update_vendor_interaction,
    toggle_favourite,
    toggle_booked
)

from budget.budget_crud import (
    get_vendor_types, 
    get_quotes, 
    get_vendor_budgets, 
    save_budgets,
    add_spending_item,
    delete_spending_item
)

# budget calculations
from budget.budget_calculations import compare_insights
from budget_ai_insights.budget_analysis import BudgetInsightsCalculator
from budget_ai_insights.budget_summary import BudgetInsightsSummary
from budget_ai_insights.budget_ai_context import vendor_quote_data
# integrations
from integrations.vendor_ai import ai_rank_vendors
from integrations.google_places import get_location_data, search_nearby_vendors, get_vendor_details

# GOOGLE MAPS
app.secret_key = env.get("APP_SECRET_KEY")
GOOGLE_MAPS_API_KEY = env.get("GOOGLE_MAPS_API_KEY")

# OpenAI
from openai import OpenAI
client = OpenAI()

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


# ........................................ROUTES................................
# Homepage/Index
@app.route('/')
def homepage():
    return render_template('index.html')

# ..................AUTH0..................
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
    auth0_id = token["userinfo"]["sub"] # get auth0 id
    # check db for user
    user = User.query.filter_by(auth0_id=auth0_id).first() 
    if user is None: # add if doesnt exist
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

# .................MY EVENTS................
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
        event = Event.query.filter_by(event_id=selected_event_id, user_id=user_id).first()
        if event is None:
            return redirect(url_for("my_events"))
        
        session["event_id"] = selected_event_id
        return redirect(url_for("eventDashboard"))

    return render_template("events/myEvents.html", events=events)

# ................NEW EVENT..................
# EVENT TYPE PAGE
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

# EVENT DETAILS PAGE
@app.route("/new-event/details", methods=["GET", "POST"])
def newEvent_details():
    # check fk in session
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if "newEvent_typeID" not in session:
        return redirect(url_for("newEvent_type"))
    
    saved = session.get("newEvent_details")

    form = EventDetailsForm() # wtforms
    
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

        # save event id to go to dashboard
        session["event_id"] = new_event.event_id

        # update checklist in db
        for vendor_type_id in selected_checklist:
            checklist = EventChecklist(
                event_id=new_event.event_id,
                vendor_type_id=int(vendor_type_id)
            )
            db.session.add(checklist)
        db.session.commit()

        # remove old session data
        session.pop("newEvent_typeID", None)
        session.pop("newEvent_details", None)

        return redirect(url_for("eventDashboard"))

    return render_template("events/newEvent_todolist.html", vendors=vendors)


# ................. EVENT DASHBOARD ......................
@app.route("/event-dashboard", methods=["GET", "POST"])
def eventDashboard():
    # check logged in
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]

    # check event_id
    if "event_id" not in session:
        # check for event in db
        has_event = Event.query.filter_by(user_id=user_id).first() is not None
        return redirect(url_for("my_events" if has_event else "newEvent_type"))

    event_id = session["event_id"]

    # check event_id matches user_id
    event = Event.query.filter_by(event_id=event_id, user_id=user_id).first()
    if event is None:
        session.pop("event_id", None)
        return redirect(url_for("my_events"))
    
    # event countdown
    days_to_go = None
    if event.event_date:
        days_to_go = max(0, (event.event_date - date.today()).days)

    # overall budget
    overall_budget = float(event.overall_budget or 0)

    # total spent
    total_spent = (
        db.session.query(func.coalesce(func.sum(Spending.amount), 0))
        .filter(Spending.event_id == event_id)
        .scalar()
    )
    total_spent = float(total_spent or 0)

    # remaining budget
    remaining_budget = overall_budget - total_spent

    # spend percent
    spend_percent = 0
    if overall_budget > 0:
        spend_percent = round((total_spent / overall_budget) * 100)
        spend_percent = max(0, min(100, spend_percent))

    # POST: UPDATE CHECKLIST
    if request.method == "POST":
        selected_ids = request.form.getlist("checklist_id")
        if selected_ids:
            items = EventChecklist.query.filter(
                EventChecklist.checklist_id.in_(selected_ids),
                EventChecklist.event_id == event_id
            ).all()

            # mark complete
            if "mark_complete" in request.form:
                for item in items:
                    item.is_complete = True
            # undo complete
            if "undo_complete" in request.form:
                for item in items:
                    item.is_complete = False

            db.session.commit()
        return redirect(url_for("eventDashboard"))
    
    # GET: get checklist items
    checklist_items = (
        EventChecklist.query
        .join(VendorType, VendorType.vendor_type_id == EventChecklist.vendor_type_id)
        .options(joinedload(EventChecklist.vendor_type))
        .filter(EventChecklist.event_id == event_id)
        .order_by(EventChecklist.is_complete.asc(), VendorType.vendor_type_id.asc())
        .all()
    )

    # next rec task
    next_item=next((i for i in checklist_items if not i.is_complete), None)

    return render_template(
        "eventDashboard.html", 
        event=event, 
        checklist_items=checklist_items, 
        days_to_go=days_to_go,
        overall_budget=overall_budget,
        total_spent=total_spent,
        remaining_budget=remaining_budget,
        spend_percent=spend_percent,
        next_item=next_item
    )

# .................... VENDOR DIRECTORY .....................
# AI SUGGESTIONS
@app.route("/vendor-directory/ai-rank")
def vendorDirectoryAiRank():
    # get vendor type from query
    vendor_type = request.args.get("vendor_type")

    if not vendor_type:
        return jsonify({"error": "missing_vendor_type"}), 400

    # session data
    event_id = session.get("event_id")
    user_id = session.get("user_id")

    # find event
    event = Event.query.filter_by(event_id=event_id, user_id=user_id).first()
    if not event:
        return jsonify({"error": "no_event_selected", "detail": "No event found in session."}), 400

    # get event location
    location = get_location_data(event.location_id)
    if not location:
        return jsonify({"error": "no_location", "detail": "Could not fetch location data"}), 400

    lat, lng = location

    # gplaces - search nearby
    vendors, _ = search_nearby_vendors(
        lat=lat,
        lng=lng,
        vendor_type=vendor_type,
        event_type=event.event_type_rel.event_type
    )

    # request ai api
    try:
        ai = ai_rank_vendors(
            client=client,
            event_type=event.event_type_rel.event_type,
            vendor_type=vendor_type,
            vendors=vendors
        )
        return jsonify(ai)

    except Exception as e:
        return jsonify({"error": "ai_failed", "detail": str(e)}), 500

# TOGGLE FAVOURITE
@app.route("/toggle-favourite/<place_id>", methods=["POST"])
def toggle_favourite_star(place_id):
    # session data
    if "user_id" not in session:
        return jsonify(success=False, error="Not logged in"), 401

    user_id = session["user_id"]
    event_id = session.get("event_id")

    if not event_id:
        return jsonify(success=False, error="No event selected"), 400

    # toggle fav function
    interaction = toggle_favourite(user_id=user_id, event_id=event_id, place_id=place_id)
    if not interaction:
        return jsonify(success=False, error="Vendor not found"), 404

    return jsonify(success=True, is_favourite=bool(interaction.is_favourite))

# VENDOR DIRECTORY
@app.route("/vendor-directory")
def vendorDirectory():
    vendor_type = request.args.get("vendor_type")
    next_token = request.args.get("page_token")  # page token
    sort_by = request.args.get("sort_by")  # sorting parameter
    
    # page number
    current_page = request.args.get("page",1, type=int)

    # redirect if no vendor type
    if not vendor_type:
        return redirect(url_for("eventDashboard"))
    
    # get event details
    event_id = session.get("event_id")
    user_id = session.get("user_id")
    event = Event.query.filter_by(event_id=event_id, user_id=user_id).first()
    
    # get location data
    location = get_location_data(event.location_id)
    lat, lng = location if location else (None, None)

    # search nearby vendors
    vendors, new_page_token = search_nearby_vendors(
        lat=lat,
        lng=lng,
        vendor_type=vendor_type,
        event_type=event.event_type_rel.event_type,
        page_token=next_token
    )

    # get selected vendors
    selected_vendors = get_selected_vendors(
        user_id=user_id, 
        event_id=event_id,
        vendor_type=vendor_type,
        sort_by=sort_by
    )

    # get interested ids 
    interested_ids = {v.vendor_place_id for v in selected_vendors}

    return render_template(
        "vendorDirectory.html", 
        vendors=vendors, 
        selected_vendors=selected_vendors,
        interested_ids=interested_ids,
        vendor_type=vendor_type, 
        next_page_token=new_page_token,
        current_page=current_page,
        gmaps_api_key=GOOGLE_MAPS_API_KEY
    )

# MARK INTERESTED
@app.route("/mark-interested", methods=["POST"])
def mark_interested_route():
    # get data from AJAX request
    data = request.get_json()
    place_id = data.get("place_id")
    vendor_name = data.get("vendor_name")
    vendor_type_str = data.get("vendor_type") 

    # get session data
    user_id = session.get("user_id")
    event_id = session.get("event_id")

    # validation
    if not all([place_id, vendor_name, vendor_type_str, user_id, event_id]):
        return jsonify({
            "success": False, 
            "error": "Missing required data."
        }), 400

    try:
        # call CRUD function
        result = mark_as_interested(
            place_id=place_id, 
            vendor_name=vendor_name, 
            vendor_type_name=vendor_type_str, 
            user_id=user_id, 
            event_id=event_id,
            status="Interested"
        )

        # return AJAX success response
        if result and hasattr(result, 'vendor_id'):
            return jsonify({
                "success": True,
                "vendor_id": result.vendor_id,
                "status": "Interested"
            })
        # return error is exists
        else:
            return jsonify({
                "success": False, 
                "error": "This vendor is already in your list."
            }), 400

    # error handling
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# REMOVE INTERESTED
@app.route('/remove-vendor', methods=['POST'])
def remove_vendor():
    # get AJAX data
    data = request.get_json()
    place_id = data.get('place_id')
    event_id = session.get('event_id')

    # validation
    if not event_id or not place_id:
        return jsonify({"success": False, "message": "Missing info"}), 400

    # remove function
    success = remove_interested_vendor(event_id, place_id)
    
    return jsonify({"success": success})
        
# ................... VENDOR DETAILS .......................
@app.route("/vendor/<place_id>", methods=["GET", "POST"])
def vendor_details(place_id):
    # session data
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    event_id = session.get("event_id")

    if not event_id:
        return redirect(url_for("my_events"))
    
    # find vendor type
    vendor_type_name = request.args.get("vendor_type")

    # POST
    if request.method == "POST":
        # determine action
        action = request.form.get("action")

        # CRUD - create interaction
        if action == "create_interaction":
            status = request.form.get("status", "Interested")
            vendor_info = get_vendor_details(place_id)
            vendor_name = vendor_info.get("name") if vendor_info else None

            if vendor_name and vendor_type_name:
                mark_as_interested(
                    place_id=place_id,
                    vendor_name=vendor_name,
                    vendor_type_name=vendor_type_name,
                    user_id=user_id,
                    event_id=event_id,
                    status=status
                )

        # CRUD - update interaction 
        elif action == "update_interaction":
            status = request.form.get("status")
            price = request.form.get("price", "")
            notes = request.form.get("notes", "")

            update_vendor_interaction(
                user_id=user_id,
                event_id=event_id,
                place_id=place_id,
                status=status,
                price=price,
                notes=notes
            )
        
        # CRUD - toggle favourite
        elif action == "toggle_favourite":
            toggle_favourite(user_id=user_id, event_id=event_id, place_id=place_id)

        return redirect(url_for("vendor_details", place_id=place_id, vendor_type=vendor_type_name))

    # GET: get vendor details
    vendor_info = get_vendor_details(place_id)
    if not vendor_info:
        return "Vendor details not found", 404
    
    # google maps
    google_maps = (
        "https://www.google.com/maps/embed/v1/place"
        f"?key={env.get('GOOGLE_MAPS_API_KEY')}"
        f"&q=place_id:{place_id}"
    )

    # get vendor interactions
    interaction = VendorInteractions.query.filter_by(
        user_id=user_id,
        event_id=event_id,
        vendor_place_id=place_id
    ).first()

    return render_template(
        "vendorDetails.html",
        vendor=vendor_info,
        interaction=interaction,
        google_maps=google_maps
    )

# .................... BUDGET PLANNER .......................
@app.route("/budget", methods=["GET", "POST"])
def budgetPlanner():
    # session data
    if "user_id" not in session:
        return redirect(url_for("login"))

    if "event_id" not in session:
        return redirect(url_for("my_events"))

    user_id = session["user_id"]
    event_id = session["event_id"]

    event = Event.query.filter_by(event_id=event_id, user_id=user_id).first()

    # redirect if no event
    if event is None:
        session.pop("event_id", None)
        return redirect(url_for("my_events"))

    # determine active tab
    tab = request.args.get("tab", "plan")

    # COMPARE TAB
    if tab == "compare":
        vendor_type_id = request.args.get("vendor_type_id", type=int)
        sort_by = request.args.get("sort_by")
        event_vendor_types = get_vendor_types(event_id)
        quotes = get_quotes(user_id, event_id, vendor_type_id, sort_by)
        insights = compare_insights(event, quotes)

        # split into booked/not booked
        booked_quotes = [q for q in quotes if q.is_booked]
        other_quotes = [q for q in quotes if not q.is_booked]

        # separate priced/no price quotes
        priced_quotes = []
        no_price_quotes = []

        # append quotes
        for q in other_quotes:
            if q.price is None:
                no_price_quotes.append(q)
            else:
                priced_quotes.append(q)

        # combine priced + no price
        other_quotes = priced_quotes + no_price_quotes

        return render_template(
            "Budget/budget_compare.html",
            event=event,
            active_tab=tab,
            event_vendor_types=event_vendor_types,
            selected_vendor_type_id=vendor_type_id,
            sort_by=sort_by,
            booked_quotes=booked_quotes,
            other_quotes=other_quotes,
            insights=insights
        )
    # SPENDING TAB 
    elif tab == "spending":
        if request.method == "POST":
            # determine action
            action = request.form.get("action")

            # add spending
            if action == "add_spending":
                description = request.form.get("description")
                amount = request.form.get("amount")
                vendor_type_id = request.form.get("vendor_type_id") or None

                if description and amount:
                    add_spending_item(event_id, description, amount, vendor_type_id)
            # delete spending
            elif action == "delete_spending":
                spending_id = request.form.get("spending_id")
                if spending_id:
                    delete_spending_item(event_id, spending_id)
            return redirect(url_for("budgetPlanner", tab="spending"))

        # get spending items from db
        spending_items = (
            Spending.query
            .filter_by(event_id=event_id)
            .order_by(Spending.created_at.desc())
            .all()
        )

        return render_template(
            "Budget/budget_spending.html",
            event=event,
            active_tab=tab,
            spending_items=spending_items
        )

    # PLAN TAB
    else:
        event_vendor_types = get_vendor_types(event_id)
        vendor_budgets = get_vendor_budgets(event_id)

        # update planned budgets
        if request.method == "POST":
            budgets_dict = {}
            for vt in event_vendor_types:
                budgets_dict[vt.vendor_type_id] = request.form.get(f"budget_{vt.vendor_type_id}")
            save_budgets(event_id, budgets_dict)
            return redirect(url_for("budgetPlanner", tab="plan"))
        return render_template(
            "Budget/budget_plan.html",
            event=event,
            active_tab=tab,
            event_vendor_types=event_vendor_types,
            vendor_budgets=vendor_budgets
        )

# BOOK VENDOR/ADD TO MY SPENDING
@app.route("/vendor-booking", methods=["POST"])
def vendor_booking():
    # session data
    if "user_id" not in session:
        return redirect(url_for("login"))
    if "event_id" not in session:
        return redirect(url_for("my_events"))

    user_id = session["user_id"]
    event_id = session["event_id"]

    vendor_id = request.form.get("vendor_id", type=int)

    if not vendor_id:
        return redirect(request.referrer or url_for("eventDashboard"))

    # toggle booked function
    toggle_booked(user_id=user_id, event_id=event_id, vendor_id=vendor_id)
    
    return redirect(request.referrer or url_for("eventDashboard"))

# ......................... BUDGET INSIGHTS .......................
@app.route("/budget-insights", methods=["GET"])
def budget_insights():
    # session data
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    if "event_id" not in session:
        return jsonify({"error": "No event selected"}), 400

    # db query
    event = Event.query.filter_by(
        event_id=session["event_id"],
        user_id=session["user_id"]
    ).first_or_404()

    # insights calculations
    calculator = BudgetInsightsCalculator(event, session["user_id"])
    calculation_data = calculator.calculate()

    # summary cards
    formatter = BudgetInsightsSummary()
    structured_output = formatter.format(calculation_data)

    return jsonify(structured_output)

# ......................... BUDGET AI STRATEGY .......................
@app.route("/budget-ai-insights", methods=["GET"])
def budget_ai_insights():
    # session data
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    if "event_id" not in session:
        return jsonify({"error": "No event selected"}), 400

    # db query
    event = Event.query.filter_by(
        event_id=session["event_id"],
        user_id=session["user_id"]
    ).first_or_404()

    # insights calculations
    calculator = BudgetInsightsCalculator(event, session["user_id"])
    calculation_data = calculator.calculate()

    # summary cards
    formatter = BudgetInsightsSummary()
    structured_output = formatter.format(calculation_data)

    # saved vendor interactions
    quote_vendors = (
        VendorInteractions.query
        .options(joinedload(VendorInteractions.vendor_type))
        .filter_by(
            event_id=session["event_id"],
            user_id=session["user_id"]
        )
        .order_by(
            VendorInteractions.is_booked.desc(),
            VendorInteractions.is_favourite.desc(),
            VendorInteractions.created_at.desc()
        )
        .all()
    )

    # get 8 results from gplaces
    places_context = vendor_quote_data(
        quote_vendors,
        limit=8
    )

    # AI prompt

    ai_prompt = f"""
    Using BOTH the budget insights and the Google Places context,
    give the user budget advice.

    Focus on quotes (not booked) that are over budget, 
    tell the user why and recommend a cheaper alternative where they can save money.

    If its high risk, advise not to book and suggest another vendor. 
    If its medium risk, explain that the user can book it but may need to spend 
    less in other vendor type categories and give an example based on their current quotes.

    Talk about the pros of vendors based on the google places information.
    Explain how they can save money.

    Don't talk about booked vendors, unless they have 1 high risk booked vendor, explain 
    that they need to save money to adjust the budget and tell they how they can do this 
    based on other vendor type quotes.
    If there any no more quotes for that vendor type, look at other vendor catogries and 
    explain if they can save money in a different category.
    
    Prefer vendors with strong rating AND high review volume.
    
    Return exactly 3 numbered lines (1., 2., 3.), each on a new line.
    Do NOT invent vendors or prices.
    Use UK spelling and £ (GBP).
    Keep under 150 words.

    Budget insights JSON:
    {json.dumps(structured_output)}

    Quoted vendors (Google Places context):
    {json.dumps(places_context)}
    """
    # API response
    ai_response = client.responses.create(
        model="gpt-4o-mini",
        input=ai_prompt
    )

    # extract text
    strategic_text = ai_response.output_text.strip()

    # add to output
    structured_output["strategy"] = strategic_text

    return jsonify(structured_output)

if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)

