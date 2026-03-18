from sqlalchemy import func
from database import db
from models import VendorBudget, Spending

# COMPARE QUOTES TO PLANNED BUDGETS
def compare_insights(event, quotes):
    overall_budget = float(event.overall_budget or 0)

    # current spending
    total_spent = (
        db.session.query(func.coalesce(func.sum(Spending.amount), 0)) # if null use 0
        .filter(Spending.event_id == event.event_id)
        .scalar()
    )

    # total spent
    total_spent = float(total_spent or 0)

    # remaining
    remaining_overall = overall_budget - total_spent

    # target budgets
    budgets = VendorBudget.query.filter_by(event_id=event.event_id).all()

    target_by_type = {
        b.vendor_type_id: float(b.target_budget) if b.target_budget is not None else None
        for b in budgets
    }

    insights = {}

    # loop quotes and compare to budgets
    for q in quotes:
        price = float(q.price) if q.price is not None else None
        target = target_by_type.get(q.vendor_type_id)

        # default feedback
        row_class = "quote-neutral"
        tooltip = ""

        # quote not added
        if price is None:
            row_class = "quote-neutral" 
            tooltip = "No quote price added yet."
        else:
            diff_to_overall = price - remaining_overall
            # NO TARGET SET, compare to overall
            if target is None or target == 0:
                # under overall budget
                if price <= remaining_overall:
                    row_class = "quote-neutral"
                    tooltip = (
                    f"No planned budget set for this vendor type. "
                    f"This quote is affordable within your remaining overall budget (£{remaining_overall:,.2f})."
                    )
                # over overall budget
                else:
                    row_class = "quote-over"
                    tooltip = (
                        f"No planned budget set for this vendor type. "
                        f"This quote exceeds your remaining overall budget by £{diff_to_overall:,.2f}."
                    )
            else:
                # COMPARE TO VENDOR TARGET
                diff_to_target = price - target
                
                # check > overall
                if diff_to_overall > 0:
                    row_class = "quote-over"
                    tooltip = (
                        f"Quote £{price:,.2f} exceeds your remaining overall budget "
                        f"(£{remaining_overall:,.2f}) by £{diff_to_overall:,.2f}."
                    )
                # < overall
                else:
                    over_target_percent = (price - target)/target

                    # less than target
                    if over_target_percent <= 0:
                        row_class = "quote-ok"
                        tooltip = (
                            f"Within planned budget (£{target:,.2f})."
                        )
                    # less than 10%
                    elif over_target_percent <= 0.10:
                        row_class = "quote-warn"
                        tooltip = (
                            f"{over_target_percent*100:.0f}% over planned budget "
                            f"(£{diff_to_target:,.2f} over £{target:,.2f})."
                        )
                    # over 10%
                    else:
                        row_class = "quote-over"
                        tooltip = (
                            f"{over_target_percent*100:.0f}% over planned budget "
                            f"(£{diff_to_target:,.2f} over £{target:,.2f})."
                        )
        # add to insights dict
        insights[q.vendor_id] = {
            "row_class": row_class,
            "tooltip": tooltip
        }

    return insights