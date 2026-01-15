from database import db

class User(db.Model):
    __tablename__ = "user"
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    auth0_id = db.Column(db.String(255), nullable=False, unique=True)

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

class EventType(db.Model):
    __tablename__ = "event_type"
    event_type_id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False)

class VendorType(db.Model):
    __tablename__ = "vendor_type"
    vendor_type_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vendor_type = db.Column(db.String(100), nullable=False)

class EventTypeVendors(db.Model):
    __tablename__ = "event_type_vendors"
    event_type_id = db.Column(db.Integer, db.ForeignKey("event_type.event_type_id"), primary_key=True)
    vendor_type_id = db.Column(db.Integer, db.ForeignKey("vendor_type.vendor_type_id"), primary_key=True)

class EventChecklist(db.Model):
    __tablename__ = "event_checklist"
    checklist_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.event_id"), nullable=False)
    vendor_type_id = db.Column(db.Integer, db.ForeignKey("vendor_type.vendor_type_id"), nullable=False)
    is_booked = db.Column(db.Boolean, default=False)