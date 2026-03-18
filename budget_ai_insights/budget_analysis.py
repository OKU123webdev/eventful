from sqlalchemy import func
from sqlalchemy.orm import joinedload
from database import db
from models import Spending, VendorBudget, VendorInteractions

# Calculate insights for AI analysis
class BudgetInsightsCalculator:

    def __init__(self, event, user_id):
        self.event = event
        self.user_id = user_id

    def calculate(self):
        # OVERALL BUDGET/SPENDING DATA
        overall_budget = float(self.event.overall_budget or 0)

        # spending total
        total_spent = (
            db.session.query(
                func.coalesce(func.sum(Spending.amount), 0)
            )
            .filter(Spending.event_id == self.event.event_id)
            .scalar()
        )

        total_spent = float(total_spent or 0)

        # remaining
        remaining_overall = overall_budget - total_spent
        is_event_over_budget = remaining_overall < 0
        overspend_amount = abs(remaining_overall) if is_event_over_budget else 0.0

        # PLANNING DATA - get specific vendor budgets
        planned_budgets = VendorBudget.query.filter_by(
            event_id=self.event.event_id
        ).all()

        target_by_type = { 
            budget.vendor_type_id: float(budget.target_budget) # dict {id: price}
            if budget.target_budget else None
            for budget in planned_budgets
        }

        # COMPARE DATA - get vendor quotes
        vendor_quotes = (
            VendorInteractions.query
            .options(joinedload(VendorInteractions.vendor_type))
            .filter_by(
                user_id=self.user_id,
                event_id=self.event.event_id
            )
            .all()
        )

        # loop through quotes and group by vendor type
        vendor_groups = {}
        for quote in vendor_quotes:

            vendor_type_id = quote.vendor_type_id

            vendor_type_name = (
                quote.vendor_type.vendor_type
                if quote.vendor_type else "Unknown"
            )

            # add quote info
            if vendor_type_id not in vendor_groups:
                vendor_groups[vendor_type_id] = {
                    "vendor_type_id": vendor_type_id,
                    "vendor_type": vendor_type_name,
                    "target_budget": target_by_type.get(vendor_type_id),
                    "quotes_with_prices": [],
                    "booked_vendor": None
                }

            # add quoted price
            if quote.price is not None:
                vendor_groups[vendor_type_id]["quotes_with_prices"].append({
                    "name": quote.vendor_name,
                    "price": float(quote.price)
                })

            # group booked quotes
            if quote.is_booked and quote.price is not None:
                vendor_groups[vendor_type_id]["booked_vendor"] = {
                    "name": quote.vendor_name,
                    "price": float(quote.price)
                }


        # ANALYSE DATA (for each vendor type)
        vendor_analysis_results = []

        for group in vendor_groups.values():

            target_budget = group["target_budget"]
            
            # sort quotes with prices
            quotes_sorted = sorted(
                group["quotes_with_prices"],
                key=lambda x: x["price"] # func to return price
            )

            # booked quotes
            booked_vendor = group["booked_vendor"]

            # choose 1 quote per vendor type
            if booked_vendor:
                chosen_vendor = booked_vendor
                selection_reason = "booked"
            elif quotes_sorted:
                chosen_vendor = quotes_sorted[-1]  # highest quote
                selection_reason = "highest_quote"
            else:
                continue  # Skip if none

            # find cheapest quote
            cheapest_vendor = quotes_sorted[0] if quotes_sorted else None

            # DIFFERENCE FROM TARGET
            difference_from_target = None
            percentage_over_target = None
            percentage_under_target = None

            if target_budget and target_budget > 0:

                difference_from_target = (
                    chosen_vendor["price"] - target_budget
                )

                if difference_from_target > 0: # % over
                    percentage_over_target = round(
                        (difference_from_target / target_budget) * 100
                    )

                elif difference_from_target < 0: # % under
                    percentage_under_target = round(
                        (abs(difference_from_target) / target_budget) * 100
                    )


            # RISK LEVEL
            risk = "low"

            if is_event_over_budget:
                risk = "high"

            elif percentage_over_target and percentage_over_target > 10:
                risk = "high"

            elif percentage_over_target and percentage_over_target > 0:
                risk = "medium"


            # if risk = high + booked
            show_booking_warning = (
                selection_reason == "booked"
                and risk == "high"
            )

            # SAVINGS REQUIRED TO MEET TARGET
            additional_savings_needed = (
                difference_from_target
                if show_booking_warning and difference_from_target
                else 0.0
            )

            # calulate potential saving
            potential_saving_amount = None

            if (
                cheapest_vendor
                and cheapest_vendor["name"] != chosen_vendor["name"]
            ):
                potential_saving_amount = ( # advise cheaper vendor
                    chosen_vendor["price"]
                    - cheapest_vendor["price"]
                )


            # STORE ANALYSIS RESULTS
            vendor_analysis_results.append({
                "vendor_type_id": group["vendor_type_id"],
                "vendor_type": group["vendor_type"],
                "chosen_vendor": chosen_vendor,
                "selection_reason": selection_reason,
                "risk": risk,
                "difference_from_target": difference_from_target,
                "percentage_over_target": percentage_over_target,
                "percentage_under_target": percentage_under_target,
                "show_booking_warning": show_booking_warning,
                "additional_savings_needed": additional_savings_needed,
                "cheapest_vendor": cheapest_vendor,
                "potential_saving_amount": potential_saving_amount
            })


        # Prioritise 4 quotes (high/med)
        high_risk = [
            v for v in vendor_analysis_results
            if v["risk"] == "high"
        ]

        medium_risk = [
            v for v in vendor_analysis_results
            if v["risk"] == "medium"
        ]

        # sort highest to lowest
        high_risk.sort(
            key=lambda x: x["difference_from_target"] or 0,
            reverse=True 
        )

        medium_risk.sort(
            key=lambda x: x["difference_from_target"] or 0,
            reverse=True
        )

        # RESULTS TO GIVE AI (max 4)
        selected_results = []

        for v in high_risk:
            if len(selected_results) >= 4:
                break
            selected_results.append(v)

        for v in medium_risk:
            if len(selected_results) >= 4:
                break
            selected_results.append(v)


        # Return calculation data
        return {
            "totals": {
                "overall_budget": overall_budget,
                "remaining_overall": remaining_overall,
                "is_event_over_budget": is_event_over_budget,
                "overspend_amount": overspend_amount
            },
            "selected_results": selected_results,
            "all_results": vendor_analysis_results
        }