import frappe
from frappe.utils import flt


CASH_MOP = "Cash"
CARD_MOPS = {"Credit Card"}
COMPLIMENTARY_MOP = "Complimentory"
CREDIT_MOP = "Credit"
TIP_FIELD = "tip"
COMPLIMENTARY_ITEM_FIELD = "custom_is_complimentary_item"  # new field name


def execute(filters=None):
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    pos_profile = filters.get("pos_profile")
    pos_shift = filters.get("pos_shift")

    if not company or not from_date or not to_date:
        frappe.throw("Please select Company, From Date, and To Date")

    # Build filters dynamically
    si_filters = {
        "docstatus": 1,
        "company": company,
    }

    if pos_profile:
        si_filters["pos_profile"] = pos_profile

    # ✅ If opening_shift selected: ignore date range
    if pos_shift:
        # IMPORTANT: change this fieldname to your actual SI field that stores shift link
        si_filters["posa_pos_opening_shift"] = pos_shift
    else:
        # ✅ Otherwise require date range
        if not from_date or not to_date:
            frappe.throw("Please select From Date and To Date (or select Opening Shift)")
        si_filters["posting_date"] = ["between", [from_date, to_date]]

    invoices = frappe.get_all(
        "Sales Invoice",
        filters=si_filters,
        fields=[
            "name",
            "posting_date",
            "company",
            "resturent_type",
            "base_total",
            "base_discount_amount",
            "base_net_total",
            "grand_total",
            "change_amount",
            "tip",
            "outstanding_amount",
        ],
        order_by="posting_date asc, name asc",
    )

    if not invoices:
        return get_columns(), []

    # preload all payments
    names = [i.name for i in invoices]
    payments = frappe.get_all(
        "Sales Invoice Payment",
        filters={"parent": ("in", names)},
        fields=["parent", "mode_of_payment", "amount"],
    )

    # group payments by invoice
    pay_by_inv = {}
    for p in payments:
        pay_by_inv.setdefault(p.parent, []).append(p)

    dine_in_sales = 0.0
    takeaway_sales = 0.0
    discount_total = 0.0
    cash_tips = 0.0
    card_tips = 0.0
    payment_totals = {}
    complimentary_total = 0.0
    credit_sales_total = 0.0

    def add_pay(mop, amount):
        if not mop:
            return
        payment_totals[mop] = payment_totals.get(mop, 0.0) + flt(amount)

    for inv in invoices:
        inv_pays = pay_by_inv.get(inv.name, [])
        mop_set = {p.mode_of_payment for p in inv_pays}
        inv_tip = flt(inv.tip)

        # # --- Tip allocation ---
        # cash_tip_this_inv = 0.0
        # card_tip_this_inv = 0.0
        # if inv_tip:
        #     if len(mop_set) == 1:
        #         only_mop = list(mop_set)[0]
        #         if only_mop in CARD_MOPS:
        #             card_tip_this_inv = inv_tip
        #         else:
        #             cash_tip_this_inv = inv_tip
        #     else:
        #         cash_tip_this_inv = inv_tip

        # cash_paid = sum(flt(p.amount) for p in inv_pays if p.mode_of_payment == CASH_MOP)
        # card_paid = sum(flt(p.amount) for p in inv_pays if p.mode_of_payment in CARD_MOPS)

        # --- Tip allocation (UPDATED Credit Card logic) ---
        cash_tip_this_inv = 0.0
        card_tip_this_inv = 0.0

        cash_paid = sum(flt(p.amount) for p in inv_pays if p.mode_of_payment == CASH_MOP)
        card_paid = sum(flt(p.amount) for p in inv_pays if p.mode_of_payment in CARD_MOPS)

        billed_amount = flt(inv.base_net_total)
        inv_tip = flt(inv.tip)

        # --- Handle all three scenarios ---
        # 1. Credit card paid more than billed (tip not entered)
        # 2. Tip entered but card paid equals billed (tip not added to paid)
        # 3. Both correct
        if card_paid > (billed_amount + inv_tip):
            # Tip not entered properly — calculate difference
            card_tip_this_inv = card_paid - billed_amount

        # elif inv_tip > 0 and card_paid <= billed_amount:
        #     # Tip entered but not added in paid
        #     card_tip_this_inv = inv_tip
        #     print("nahi ana bawa 2")
        elif inv_tip > 0 and abs((card_paid - billed_amount) - inv_tip) <= 1:
            # Both entered correctly
            card_tip_this_inv = inv_tip

        # Assign cash tip if it’s a cash-only invoice
        if len({p.mode_of_payment for p in inv_pays}) == 1:
            only_mop = inv_pays[0].mode_of_payment
            if only_mop == CASH_MOP and inv_tip:
                cash_tip_this_inv = inv_tip

        else:
            # Mixed MOPs — assign to cash if not card
            if not card_tip_this_inv and inv_tip:
                cash_tip_this_inv = inv_tip


        # --- Effective payments ---
        effective_cash = max(0.0, flt(cash_paid) - flt(inv.change_amount))
        effective_card = flt(card_paid)

        effective_other = 0.0
        for p in inv_pays:
            if p.mode_of_payment not in CARD_MOPS and p.mode_of_payment != CASH_MOP and p.mode_of_payment != COMPLIMENTARY_MOP:
                effective_other += flt(p.amount)

        effective_non_comp_paid = effective_cash + effective_card + effective_other

        # --- Complimentary (old + new) and Credit Handling ---

        # --- Complimentary via Payment MOP (with partial payments considered) ---
        complimentary_from_mop = 0.0
        billed_amount = flt(inv.base_net_total)
        total_paid = sum(flt(p.amount) for p in inv_pays)

        if COMPLIMENTARY_MOP in mop_set:
            # Amounts paid through Complimentary MOP should be fully considered complimentary
            comp_paid = sum(flt(p.amount) for p in inv_pays if p.mode_of_payment == COMPLIMENTARY_MOP)

            # Remaining unpaid (if any) also becomes complimentary
            unpaid_portion = max(0.0, billed_amount - total_paid)

            complimentary_from_mop = comp_paid + unpaid_portion

        # Complimentary via Items (new logic)
        comp_items = frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": inv.name, COMPLIMENTARY_ITEM_FIELD: 1},
            fields=["amount", "item_code", "qty", "uom", "parent"],
        )
        if "___price_cache" not in locals():
            price_cache = {}
        company_currency = frappe.get_cached_value("Company", company, "default_currency")
        price_list_name = inv.get("selling_price_list")

        def get_pl_rate_base(item_code, uom):
            """Fetch price_list_rate from Item Price for this price list and convert to base currency."""
            key = (price_list_name, item_code, uom)
            if key in price_cache:
                return price_cache[key]

            filters = {
                "item_code": item_code,
                "selling": 1
            }
            # Try with matching UOM first, then fallback without UOM
            try_orders = [
                (dict(filters, uom=uom), "valid_from desc"),
                (filters, "valid_from desc"),
            ]

            price_list_rate = None
            rate_currency = None

            for f, order in try_orders:
                ip = frappe.get_all(
                    "Item Price",
                    filters=f,
                    fields=["price_list_rate", "currency"],
                    order_by=order,
                    limit=1,
                )
                if ip:
                    price_list_rate = flt(ip[0].price_list_rate)
                    rate_currency = ip[0].currency
                    break

            # As a last resort, use Item's standard_rate (optional)
            if price_list_rate is None:
                std = frappe.get_all(
                    "Item",
                    filters={"name": item_code},
                    fields=["standard_rate"],
                    limit=1,
                )
                price_list_rate = flt((std and std[0].standard_rate) or 0.0)
                rate_currency = company_currency  # standard_rate is in base/company currency

            # Convert to base currency if needed
            if rate_currency and rate_currency != company_currency:
                ex = flt(get_exchange_rate(rate_currency, company_currency, inv.posting_date))
            else:
                ex = 1.0

            base_rate = price_list_rate * ex
            price_cache[key] = base_rate
            return base_rate

        complimentary_from_items = 0.0
        for it in comp_items:
            unit_base = get_pl_rate_base(it.item_code, it.uom)
            complimentary_from_items += unit_base * flt(it.qty)

        complimentary_for_this_invoice = complimentary_from_mop + complimentary_from_items


        # --- Credit Logic ---
        credit_for_this_invoice = 0.0
        total_paid = sum(flt(p.amount) for p in inv_pays)
        billed_amount = flt(inv.base_net_total)
        unpaid_amount = max(0.0, billed_amount - total_paid)

        # 1️⃣ Case A: No payments or partial unpaid → treat unpaid as credit
        if (not inv_pays) or (unpaid_amount > 0.0001 and COMPLIMENTARY_MOP not in mop_set):
            credit_for_this_invoice += unpaid_amount

        # 2️⃣ Case B: Old logic – any payments made through “Credit” MOP
        credit_paid = sum(flt(p.amount) for p in inv_pays if p.mode_of_payment.lower() in {"credit", "credit sales", "on account"})
        if credit_paid:
            credit_for_this_invoice += credit_paid

        # Add to totals
        if credit_for_this_invoice > 0.0001:
            credit_sales_total += credit_for_this_invoice

        # Add up global totals
        if complimentary_for_this_invoice > 0.0001:
            complimentary_total += complimentary_for_this_invoice

        # --- Dine In / Take Away ---
        # Complimentary reduces sales, Credit still part of net sales
        net_sales_for_invoice = max(0.0, flt(inv.base_total))

        if inv.resturent_type == "Dine In":
            dine_in_sales += net_sales_for_invoice
        elif inv.resturent_type == "Take Away":
            takeaway_sales += net_sales_for_invoice

        discount_total += flt(inv.base_discount_amount)

        # --- Payment totals (cash, card, other) ---
        cash_amount_final = max(0.0, cash_paid - flt(inv.change_amount)) + cash_tip_this_inv
        if abs(cash_amount_final) > 0.0001:
            add_pay(CASH_MOP, cash_amount_final)

        # Avoid double counting: if card_paid already includes the tip (card_paid > billed),
        # use card_paid as-is. Only add tip to card when it wasn't included in paid.
        if card_tip_this_inv > 0 and card_paid <= billed_amount:
            # Scenario 2: tip entered but not paid → include it to reflect actual intake
            card_amount_final = card_paid
        else:
            # Scenarios 1 & 3: tip already in card_paid OR no tip → don't add again
            card_amount_final = card_paid

        if abs(card_amount_final) > 0.0001:
            add_pay("Card", card_amount_final)

        other_mops = [p for p in inv_pays if p.mode_of_payment not in CARD_MOPS and p.mode_of_payment != CASH_MOP]
        for p in other_mops:
            add_pay(p.mode_of_payment, flt(p.amount))

    gross_sales = dine_in_sales + takeaway_sales
    net_sales = gross_sales - discount_total
    total_tips = cash_tips + card_tips

    # recompute tips split
    for inv in invoices:
        inv_pays = pay_by_inv.get(inv.name, [])
        mop_set = {p.mode_of_payment for p in inv_pays}
        inv_tip = flt(inv.tip)
        if not inv_tip:
            continue
        if len(mop_set) == 1 and next(iter(mop_set)) in CARD_MOPS:
            card_tips += inv_tip
        else:
            cash_tips += inv_tip

    total_tips = cash_tips + card_tips
    total_all = net_sales + total_tips

    rows = []
    rows.append({"section": "Sales Breakdown"})
    rows.append({"category": "Dine-in Sales", "amount": dine_in_sales})
    rows.append({"category": "Takeaway Sales", "amount": takeaway_sales})
    rows.append({"category": "Gross Sales", "amount": gross_sales})
    rows.append({"category": "Discounts Given", "amount": -discount_total})
    rows.append({"category": "Net Sales", "amount": net_sales})

    rows.append({"section": "Tips Summary"})
    rows.append({"category": "Cash Tips", "amount": cash_tips})
    rows.append({"category": "Card Tips", "amount": card_tips})
    rows.append({"category": "Total Tips", "amount": total_tips})
    rows.append({"category": "TOTAL", "amount": total_all})

    rows.append({"section": "Payment Breakdown (Including Tips)"})
    total_payments_row = 0.0
    for mop, amt in sorted(payment_totals.items()):
        if mop not in [COMPLIMENTARY_MOP, CREDIT_MOP]:
            rows.append({"category": mop, "amount": amt})
            total_payments_row += flt(amt)

    if credit_sales_total:
        rows.append({"category": "Credit Sales", "amount": credit_sales_total})
        total_payments_row += credit_sales_total

    rows.append({"category": "TOTAL", "amount": total_payments_row})

    rows.append({"section": "Direct Expense Summary"})
    if complimentary_total:
        rows.append({"category": "Complimentary Sales", "amount": complimentary_total})

    return get_columns(), rows


def get_columns():
    return [
        {"label": "Section", "fieldname": "section", "fieldtype": "Data", "width": 240},
        {"label": "Category", "fieldname": "category", "fieldtype": "Data", "width": 260},
        {"label": "Amount (QAR)", "fieldname": "amount", "fieldtype": "Currency", "width": 140},
    ]