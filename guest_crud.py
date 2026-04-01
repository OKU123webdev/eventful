from database import db
from models import Guest
from sqlalchemy import or_

# CREATE - add guest
def add_guest(event_id, firstname, lastname, email=None, rsvp_status="Pending"):
    new_guest = Guest(
        event_id=event_id,
        firstname=firstname,
        lastname=lastname,
        email=email,
        rsvp_status=rsvp_status or "Pending"
    )

    db.session.add(new_guest)
    db.session.commit()
    return new_guest


# READ - get guests for one event
def get_guests(event_id):
    return Guest.query.filter_by(event_id=event_id).order_by(Guest.lastname.asc(), Guest.firstname.asc()).all()


# UPDATE - update RSVP status
def update_guest_rsvp(guest_id, event_id, rsvp_status):
    guest = Guest.query.filter_by(
        guest_id=guest_id,
        event_id=event_id
    ).first()

    if not guest:
        return None

    guest.rsvp_status = rsvp_status
    db.session.commit()
    return guest


# DELETE - remove guest
def remove_guest(guest_id, event_id):
    guest = Guest.query.filter_by(
        guest_id=guest_id,
        event_id=event_id
    ).first()

    if not guest:
        return False

    db.session.delete(guest)
    db.session.commit()
    return True

# READ - get guests for one event
def get_guests(event_id, search=None, status_filter=None):
    query = Guest.query.filter_by(event_id=event_id)

    # search first or last name
    if search:
        query = query.filter(
            or_(
                Guest.firstname.ilike(f"%{search}%"),
                Guest.lastname.ilike(f"%{search}%")
            )
        )

    # filter by RSVP status
    if status_filter:
        query = query.filter(Guest.rsvp_status == status_filter)

    return query.order_by(Guest.lastname.asc(), Guest.firstname.asc()).all()