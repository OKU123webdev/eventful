# Convert insights to summary for AI
class BudgetInsightsSummary:

    # format price in £
    def money(self, amount):
        return f"£{float(amount):,.2f}"

    def format(self, calculation_data):
        # passed from route
        totals = calculation_data["totals"]
        selected = calculation_data["selected_results"]
        all_results = calculation_data.get("all_results", selected)

        # EVENT OVER BUDGET - summary
        if totals["is_event_over_budget"]:
            summary = (
                f"You are {self.money(totals['overspend_amount'])} "
                f"over your overall budget of "
                f"{self.money(totals['overall_budget'])}."
            )
        # EVENT UNDER BUDGET - summary
        else:
            summary = (
                f"You have {self.money(totals['remaining_overall'])} "
                f"remaining from your overall budget of "
                f"{self.money(totals['overall_budget'])}."
            )

        # SAVING OPPORTUNITIES
        saving_opportunities = []
        for r in all_results:
            if r.get("potential_saving_amount") and r.get("cheapest_vendor"):
                saving_opportunities.append({
                    "vendor_type_id": r["vendor_type_id"],
                    "vendor_type": r["vendor_type"],
                    "from_vendor": r["chosen_vendor"]["name"],
                    "to_vendor": r["cheapest_vendor"]["name"],
                    "save": float(r["potential_saving_amount"])
                })

        # sort by biggest saving opportunity
        saving_opportunities.sort(key=lambda x: x["save"], reverse=True)
        
        # BUILD SUMMARY  (for the 4 priority vendors)
        items = []
        for result in selected:
            vendor_name = result["chosen_vendor"]["name"]
            vendor_type = result["vendor_type"]
            risk = result["risk"]
            bullets = []
            title = "Within target"

            # if over target
            if result["percentage_over_target"]:
                title = "Over target"
                bullets.append(
                    f"This is {result['percentage_over_target']}% "
                    f"over your target budget for "
                    f"{vendor_type.lower()}."
                )

                # If booked and high risk
                if result["show_booking_warning"]:
                    bullets.append(
                        f"Because this is booked, you need to save "
                        f"{self.money(result['additional_savings_needed'])} "
                        f"elsewhere to stay aligned with your plan."
                    )

                # If not booked, recommend cheaper option
                elif result["potential_saving_amount"]:
                    bullets.append(
                        f"Cheaper option: "
                        f"{result['cheapest_vendor']['name']} "
                        f"(save {self.money(result['potential_saving_amount'])})."
                    )
                # no cheaper option
                else:
                    bullets.append("No cheaper quote saved in this category yet.")
                    if risk == "medium":
                        alt = next(
                            (s for s in saving_opportunities if s["vendor_type_id"] != result["vendor_type_id"]),
                            None
                        )
                        if alt:
                            bullets.append(
                                f"You can still stay on track overall by saving {self.money(alt['save'])} elsewhere. For example, switch {alt['vendor_type'].lower()} from {alt['from_vendor']} to {alt['to_vendor']}."
                            )

            # If under target
            elif result["percentage_under_target"]:
                bullets.append(
                    f"This is {result['percentage_under_target']}% "
                    f"under your target budget for "
                    f"{vendor_type.lower()}."
                )

            items.append({
                "vendor_name": vendor_name,
                "vendor_type": vendor_type,
                "risk": risk,
                "title": title,
                "bullets": bullets[:3]
            })

        return {
            "summary": summary,
            "items": items
        }