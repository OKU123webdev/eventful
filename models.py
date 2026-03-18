from database import db

# DATABASE MODELS

class User(db.Model):
    __tablename__ = "user"
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    auth0_id = db.Column(db.String(255), nullable=False, unique=True)

    # relationships
    events = db.relationship("Event", back_populates="user")


class Event(db.Model):
    __tablename__ = "event"
    event_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    event_type_id = db.Column(db.Integer, db.ForeignKey("event_type.event_type_id"), nullable=False)
    event_name = db.Column(db.String(255))
    event_date = db.Column(db.Date)
    capacity = db.Column(db.Integer)
    overall_budget = db.Column(db.Numeric(10,2))
    location_id = db.Column(db.String(255))

    # relationships
    user = db.relationship("User", back_populates="events")
    checklist_items = db.relationship("EventChecklist", back_populates="event")
    event_type_rel = db.relationship("EventType", backref="events")

class EventType(db.Model):
    __tablename__ = "event_type"
    event_type_id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False)

class VendorType(db.Model):
    __tablename__ = "vendor_type"
    vendor_type_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vendor_type = db.Column(db.String(100), nullable=False)

    # relationships
    checklist_items = db.relationship("EventChecklist", back_populates="vendor_type")

class EventTypeVendors(db.Model):
    __tablename__ = "event_type_vendors"
    event_type_id = db.Column(db.Integer, db.ForeignKey("event_type.event_type_id"), primary_key=True)
    vendor_type_id = db.Column(db.Integer, db.ForeignKey("vendor_type.vendor_type_id"), primary_key=True)

class EventChecklist(db.Model):
    __tablename__ = "event_checklist"
    checklist_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.event_id"), nullable=False)
    vendor_type_id = db.Column(db.Integer, db.ForeignKey("vendor_type.vendor_type_id"), nullable=False)
    is_complete = db.Column(db.Boolean, default=False)

    # relationships
    event = db.relationship("Event", back_populates="checklist_items")
    vendor_type = db.relationship("VendorType", back_populates="checklist_items")

    # method
    @classmethod
    def show_checklist(cls, event_id):
        return cls.query.filter_by(event_id=event_id).all()
    
class VendorInteractions(db.Model):
    __tablename__ = "vendor_interactions"

    vendor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.event_id"), nullable=False)
    vendor_type_id = db.Column(db.Integer, db.ForeignKey("vendor_type.vendor_type_id"), nullable=False)
    vendor_place_id = db.Column(db.String(255), nullable=False)
    vendor_name = db.Column(db.String(255), nullable=False)
    vendor_status = db.Column(db.String(50), nullable=False, default="Interested")
    is_favourite = db.Column(db.Boolean, default=False)
    user_notes = db.Column(db.Text)
    price = db.Column(db.Numeric(10,2))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_booked = db.Column(db.Boolean, default=False)
    booked_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User")
    event = db.relationship("Event")
    vendor_type = db.relationship("VendorType")
    
class VendorBudget(db.Model):
    __tablename__ = "vendor_budget"
    budget_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.event_id"), nullable=False)
    vendor_type_id = db.Column(db.Integer, db.ForeignKey("vendor_type.vendor_type_id"), nullable=False)
    target_budget = db.Column(db.Numeric(10,2))

    vendor_type = db.relationship("VendorType")
    event = db.relationship("Event")

class Spending(db.Model):
    __tablename__ = "Spending"
    spending_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.event_id"), nullable=False)
    vendor_type_id = db.Column(db.Integer, db.ForeignKey("vendor_type.vendor_type_id"))
    vendor_interaction_id = db.Column(db.Integer, db.ForeignKey("vendor_interactions.vendor_id"))
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())