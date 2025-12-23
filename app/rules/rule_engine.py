# currently determinstic later will be updated to smart engine
from datetime import datetime
from typing import Dict, Any, List

RECEIPT_THRESHOLD_EUR = 25.0
MEAL_CAPS = {
    "BREAKFAST": 15.0,
    "LUNCH": 25.0,
    "DINNER": 40.0,
    "OTHER": 40.0
}
LODGING_NIGHT_CAP = 180.0
MILEAGE_RATE_EUR_PER_KM = 0.42

def parse_date(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()

def evaluate_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
    lines = claim["lines"]
    submission_date = parse_date(claim["submission_date"])

    total = 0.0
    line_results = []
    missing_info: List[str] = []

    for ln in lines:
        line_total = float(ln["amount"])
        total += line_total

        issues = []
        category = ln["category"]
        receipt = (ln.get("receipt") or {}).get("provided", False)

        expense_date = parse_date(ln["date"])
        days_late = (submission_date - expense_date).days

        # Deadline (from template policy): 30 days
        if days_late > 30:
            issues.append({
                "code": "SUBMISSION_LATE",
                "message": f"Submitted {days_late} days after expense date (policy limit: 30 days)."
            })

        # Receipt threshold
        if line_total >= RECEIPT_THRESHOLD_EUR and not receipt:
            issues.append({
                "code": "MISSING_RECEIPT",
                "message": f"Receipt required for single line >= {RECEIPT_THRESHOLD_EUR:.0f} EUR."
            })
            missing_info.append(f"Receipt (or Missing Receipt Declaration) for line {ln['line_id']}")

        # Category rules
        if category == "MEALS":
            meal_type = ln.get("meal_type") or "OTHER"
            cap = MEAL_CAPS.get(meal_type, MEAL_CAPS["OTHER"])
            if line_total > cap:
                issues.append({
                    "code": "MEAL_CAP_EXCEEDED",
                    "message": f"Meal amount {line_total:.2f} exceeds cap {cap:.2f} for {meal_type}."
                })

        if category == "LODGING":
            # For simplicity: treat amount as nightly; in real data include nights count.
            if line_total > LODGING_NIGHT_CAP:
                pre = (ln.get("preapproval") or {}).get("provided", False)
                if not pre:
                    issues.append({
                        "code": "LODGING_CAP_EXCEEDED_NO_PREAPPROVAL",
                        "message": f"Lodging exceeds nightly cap {LODGING_NIGHT_CAP:.2f} without pre-approval."
                    })

            if not receipt:
                issues.append({
                    "code": "MISSING_ITEMIZED_INVOICE",
                    "message": "Lodging requires an itemized hotel invoice."
                })
                missing_info.append(f"Itemized hotel invoice for line {ln['line_id']}")

        if category == "CLIENT_ENTERTAINMENT":
            attendees = ln.get("attendees") or []
            if len(attendees) == 0:
                issues.append({
                    "code": "MISSING_ATTENDEES",
                    "message": "Client entertainment requires attendee names and business purpose."
                })
                missing_info.append(f"Attendees list for line {ln['line_id']}")
            # Receipt always required for entertainment (policy template)
            if not receipt:
                issues.append({
                    "code": "MISSING_RECEIPT_ENTERTAINMENT",
                    "message": "Client entertainment requires itemized receipt regardless of amount."
                })
                missing_info.append(f"Itemized receipt for entertainment line {ln['line_id']}")

        if category == "MILEAGE":
            mileage = ln.get("mileage") or {}
            km = mileage.get("km", None)
            if km is None:
                issues.append({"code": "MISSING_MILEAGE_KM", "message": "Mileage requires km distance."})
                missing_info.append(f"Mileage km for line {ln['line_id']}")
            else:
                expected = float(km) * MILEAGE_RATE_EUR_PER_KM
                # Allow small rounding difference
                if abs(line_total - expected) > 0.5:
                    issues.append({
                        "code": "MILEAGE_AMOUNT_MISMATCH",
                        "message": f"Amount {line_total:.2f} does not match km*rate ({expected:.2f})."
                    })

        status = "COMPLIANT" if len(issues) == 0 else "NON_COMPLIANT"
        line_results.append({
            "line_id": ln["line_id"],
            "status": status,
            "issues": issues
        })

    approval_route = ["MANAGER"]
    if total > 1000:
        approval_route.append("FINANCE")

    # Basic decision from deterministic checks:
    if any(lr["status"] == "NON_COMPLIANT" for lr in line_results):
        decision = "NEEDS_MORE_INFO"
    else:
        decision = "APPROVE_RECOMMENDED"

    return {
        "decision": decision,
        "claim_total": total,
        "approval_route": approval_route,
        "line_results": line_results,
        "missing_info": sorted(set(missing_info))
    }
