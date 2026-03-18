from database import db
from models import VendorInteractions, VendorBudget, VendorType, EventChecklist, Spending
from sqlalchemy.orm import joinedload

# COMPARE - get vendor type names from event
def get_vendor_types(event_id):
    return (
        db.session.query(VendorType)
        .join(EventChecklist, VendorType.vendor_type_id == EventChecklist.vendor_type_id)
        .filter(EventChecklist.event_id == event_id)
        .order_by(VendorType.vendor_type.asc())
        .all()
    )

# COMPARE - get quote price for each vendor
def get_quotes(user_id, event_id, vendor_type_id=None, sort_by=None):
    query = (
        VendorInteractions.query
        .options(joinedload(VendorInteractions.vendor_type))
        .filter_by(user_id=user_id, event_id=event_id)
    )

    if vendor_type_id is not None:
        query = query.filter(VendorInteractions.vendor_type_id == vendor_type_id)

    # sort filter
    if sort_by == "price_low":
        query = query.order_by(VendorInteractions.price.is_(None), VendorInteractions.price.asc())
    elif sort_by == "price_high":
        query = query.order_by(VendorInteractions.price.is_(None), VendorInteractions.price.desc())
    else:
        query = query.order_by(VendorInteractions.created_at.desc())

    return query.all()

# PLAN - get users budgets
def get_vendor_budgets(event_id):
    budgets = VendorBudget.query.filter_by(event_id=event_id).all()
    # return dictonary vendor_type_id: budget
    return {b.vendor_type_id: b for b in budgets}

# PLAN - save budgets
def save_budgets(event_id, budgets_dict):
    for vendor_type_id, value in budgets_dict.items():
        # check value not empty string
        if value is None or str(value).strip() == "":
            target = None
        else:
            target = float(value) # convert to float

        # get existing planned budget
        existing = VendorBudget.query.filter_by(
            event_id=event_id,
            vendor_type_id=vendor_type_id
        ).first()

        # replace existing or add new
        if existing:
            existing.target_budget = target
        else:
            db.session.add(VendorBudget(
                event_id=event_id,
                vendor_type_id=vendor_type_id,
                target_budget=target
            ))
    db.session.commit()

# MY SPENDING - add spending
def add_spending_item(event_id, description, amount, vendor_type_id=None):
    new_item = Spending(
        event_id=event_id,
        description=description,
        amount=float(amount),
        vendor_type_id=vendor_type_id
    )
    db.session.add(new_item)
    db.session.commit()

# MY SPENDING - delete spending
def delete_spending_item(event_id, spending_id):
    # find by id
    item = Spending.query.filter_by(
        spending_id=spending_id,
        event_id=event_id
    ).first()

    # delete
    if item:
        db.session.delete(item)
        db.session.commit()