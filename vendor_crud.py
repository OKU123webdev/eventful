from database import db
from models import VendorInteractions, VendorType
from vendor_search import get_vendor_details
from flask import session

# Create - MARK AS INTRESTED
def mark_as_interested(place_id, vendor_name, vendor_type_name, user_id, event_id):

    vendorType = VendorType.query.filter_by(vendor_type=vendor_type_name).first()
    
    if not vendorType:
        return None 
    
    existing = VendorInteractions.query.filter_by(
        user_id=user_id,
        event_id=event_id,
        vendor_place_id=place_id
    ).first()

    if not existing:
        new_interaction = VendorInteractions(
            user_id=user_id,
            event_id=event_id,
            vendor_place_id=place_id,
            vendor_name=vendor_name,
            vendor_type_id=vendorType.vendor_type_id,
            vendor_status="Interested"
        )
        db.session.add(new_interaction)
        db.session.commit()
        return new_interaction 
    return None



def get_selected_vendors(user_id, event_id, sort_by=None):
    query = VendorInteractions.query.filter_by(user_id=user_id, event_id=event_id)
    if sort_by == "date_desc":
        query = query.order_by(VendorInteractions.created_at.desc())
    elif sort_by == "date_asc":
        query = query.order_by(VendorInteractions.created_at.asc())
    elif sort_by == "price_desc":
        query = query.order_by(VendorInteractions.quote_price.desc())
    elif sort_by == "price_asc":
        query = query.order_by(VendorInteractions.quote_price.asc())

    return query.all()


# Update 
# TOGGLE FAVOURITE
def toggle_favourite(vendor_id, favourite=True):
    vendor = VendorInteractions.query.get(vendor_id)
    if vendor:
        vendor.is_favorite = favourite
        db.session.commit() #ask ab out this?
        return True
    return False

# UPDATE STATUS
def update_vendor_status(vendor_id, status):
    vendor = VendorInteractions.query.get(vendor_id)
    if vendor:
        vendor.vendor_status = status
        db.session.commit()
        return True
    return False

def update_notes(vendor_id, notes):
    vendor = VendorInteractions.query.get(vendor_id)
    if vendor:
        vendor.notes = notes
        db.session.commit()
        return True
    return False

def update_quote(vendor_id, price):
    vendor = VendorInteractions.query.get(vendor_id)
    if vendor:
        try:
            vendor.quote_price = float(price)
            db.session.commit()
            return True
        except ValueError:
            return {"error": "Invalid price format"}, 400
    return False

# Delete - REMOVE VENDOR FROM SELECTED TABLE
def remove_interested_vendor(event_id, place_id):
    try:
        # Match using your actual column name: vendor_place_id
        interaction = VendorInteractions.query.filter_by(
            event_id=event_id, 
            vendor_place_id=place_id
        ).first()
        
        if interaction:
            db.session.delete(interaction)
            db.session.commit()
            return True
        return False
    except Exception as e:
        print(f"Error removing interaction: {e}")
        db.session.rollback()
        return False