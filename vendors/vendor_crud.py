from database import db
from models import VendorInteractions, VendorType, Spending
from datetime import datetime

# Create - MARK AS INTRESTED
def mark_as_interested(place_id, vendor_name, vendor_type_name, user_id, event_id, status):

    # check vendor type exists
    vendorType = VendorType.query.filter_by(vendor_type=vendor_type_name).first()
    
    if not vendorType:
        return None 
    
    # check interaction exsists
    existing = VendorInteractions.query.filter_by(
        user_id=user_id,
        event_id=event_id,
        vendor_place_id=place_id
    ).first()

    if existing:
        return existing
    
    # create new interaction
    new_interaction = VendorInteractions(
        user_id=user_id,
        event_id=event_id,
        vendor_place_id=place_id,
        vendor_name=vendor_name,
        vendor_type_id=vendorType.vendor_type_id,
        vendor_status=status or "Interested"
    )
    # add to db
    db.session.add(new_interaction)
    db.session.commit()
    return new_interaction 

# READ - get vendors
def get_selected_vendors(user_id, event_id, vendor_type=None, sort_by=None):
    
    # db query
    query = VendorInteractions.query.filter_by(user_id=user_id, event_id=event_id)

    # filter by vendor type
    if vendor_type:
        vt = VendorType.query.filter_by(vendor_type=vendor_type).first()
        if vt:
            query = query.filter(VendorInteractions.vendor_type_id == vt.vendor_type_id)

    # sorting
    if sort_by == "date_desc":
        query = query.order_by(VendorInteractions.created_at.desc())
    elif sort_by == "date_asc":
        query = query.order_by(VendorInteractions.created_at.asc())
    elif sort_by == "price_desc":
        query = query.order_by(VendorInteractions.price.desc())
    elif sort_by == "price_asc":
        query = query.order_by(VendorInteractions.price.asc())

    return query.all()


# UPDATE: vendor interactions
def update_vendor_interaction(user_id, event_id, place_id, status=None, price=None, notes=None):
    # find interaction
    interaction = VendorInteractions.query.filter_by(
        user_id=user_id,
        event_id=event_id,
        vendor_place_id=place_id
    ).first()

    if not interaction:
        return None

    # update price
    if price is not None and price != "":
        interaction.price = float(price)
    elif price == "":
        interaction.price = None

    # update notes
    if notes is not None:
        interaction.user_notes = notes

    # update status
    if status:
        interaction.vendor_status = status

        # BOOKED
        if status == "Booked":
            interaction.is_booked = True

            # if not booked, add timestap
            if interaction.booked_at is None:
                interaction.booked_at = datetime.utcnow()

            # SPENDING
            # check exsits in spending table
            if interaction.price is not None: 
                linked_spending = Spending.query.filter_by(
                    event_id=event_id,
                    vendor_interaction_id=interaction.vendor_id
                ).first()

                # create new spending
                if not linked_spending:
                    db.session.add(Spending(
                        event_id=event_id,
                        vendor_type_id=interaction.vendor_type_id,
                        vendor_interaction_id=interaction.vendor_id,
                        description=interaction.vendor_name,
                        amount=interaction.price
                    ))
                # update existing spending
                else:
                    linked_spending.description = interaction.vendor_name
                    linked_spending.amount = interaction.price
                    linked_spending.vendor_type_id = interaction.vendor_type_id

        else:
            # toggle UNBOOK
            interaction.is_booked = False
            interaction.booked_at = None

            # remove linked spending 
            linked_spending = Spending.query.filter_by(
                event_id=event_id,
                vendor_interaction_id=interaction.vendor_id
            ).first()
            if linked_spending:
                db.session.delete(linked_spending)

    db.session.commit()
    return interaction



# UPDATE: toggle favourite
def toggle_favourite(user_id, event_id, place_id):
    # db query
    interaction = VendorInteractions.query.filter_by(
        user_id=user_id,
        event_id=event_id,
        vendor_place_id=place_id
    ).first()

    if not interaction:
        return None
    
    # update boolean
    interaction.is_favourite = not bool(interaction.is_favourite)

    # save to db
    db.session.commit()
    return interaction

# UPDATE: toggle booked
def toggle_booked(user_id, event_id, vendor_id):
    # db query
    interaction = VendorInteractions.query.filter_by(
        vendor_id=vendor_id,
        user_id=user_id,
        event_id=event_id
    ).first()

    if not interaction:
        return None

    # find linked spending
    linked_spending = Spending.query.filter_by(
        event_id=event_id,
        vendor_interaction_id=interaction.vendor_id
    ).first()

    if interaction.is_booked:
        # UNBOOK
        interaction.is_booked = False
        interaction.booked_at = None

        # update status
        if interaction.vendor_status == "Booked":
            interaction.vendor_status = "Interested"

        # remove price from spending
        if linked_spending:
            db.session.delete(linked_spending)

    else:
        # BOOK
        interaction.is_booked = True
        interaction.booked_at = datetime.utcnow()
        interaction.vendor_status = "Booked"

        # if no quoted price
        if interaction.price is None:
            db.session.commit()
            return interaction

        # if quoted price, add to spending
        if not linked_spending:
            new_spending = Spending(
                event_id=event_id,
                vendor_type_id=interaction.vendor_type_id,
                vendor_interaction_id=interaction.vendor_id,
                description=interaction.vendor_name,
                amount=interaction.price
            )
            db.session.add(new_spending)
        else:
            # update existing spending row
            linked_spending.description = interaction.vendor_name
            linked_spending.amount = interaction.price
            linked_spending.vendor_type_id = interaction.vendor_type_id

    db.session.commit()
    return interaction



# DELETE - remove from interaction table
def remove_interested_vendor(event_id, place_id):
    try:
        # db query
        interaction = VendorInteractions.query.filter_by(
            event_id=event_id, 
            vendor_place_id=place_id
        ).first()
        
        if interaction:
            # remove from db
            db.session.delete(interaction)
            db.session.commit()
            return True
        return False
    
    # error handling
    except Exception as e:
        print(f"Error removing interaction: {e}")
        db.session.rollback()
        return False
    
