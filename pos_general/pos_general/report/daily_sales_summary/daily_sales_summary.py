from frappe import _
from datetime import datetime
from frappe.utils import cstr, cint, getdate, flt
import frappe


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters):
    data = []

    # Retrieve filter values
    start_date = filters.get('from_date')
    end_date = filters.get('to_date')
    branch = filters.get('pos_profile')
    cost_center = ''
    if branch:
        branch_doc = frappe.get_all(
            "Branch", filters={"pos_profile": branch}, fields=["cost_center"])
        cost_center = branch_doc[0].get(
            "cost_center", '') if branch_doc else ''

    # Validate date range
    if end_date < start_date:
        raise ValueError(
            "The 'End Date' cannot be earlier than the 'Start Date'.")

    # Query to get sales invoices from POS Closing Shift
    query_closing_shift = """
        SELECT DISTINCT sir.sales_invoice AS invoice
        FROM `tabPOS Closing Shift` sii
        JOIN `tabSales Invoice Reference` sir ON sii.name = sir.parent
        WHERE DATE(sii.period_start_date) >= %(start_date)s
        AND DATE(sii.period_start_date) <= %(end_date)s
        AND (%(branch)s IS NULL OR sii.pos_profile = %(branch)s)
    """
    closing_shift_invoice = frappe.db.sql(
        query_closing_shift, {'start_date': start_date, 'end_date': end_date, 'branch': branch}, as_dict=True
    )

    if not closing_shift_invoice:
        return data

    sales_invoices_list = [item['invoice'] for item in closing_shift_invoice]

    if not sales_invoices_list:
        return data

    # Sales Analysis query
    sales_analysis_query = """
        SELECT 
            ROUND(SUM(CASE WHEN si.total > 0 THEN si.total ELSE 0 END), 2) AS sale,
            ROUND(SUM(CASE WHEN si.total < 0 THEN si.total ELSE 0 END), 2) AS r_sale,
            SUM(si.total) AS g_sale,
            COALESCE(SUM(si.discount_amount), 0) AS discount,
            COALESCE(SUM(si.total_taxes_and_charges), 0) AS tax,
            (SUM(si.total) - COALESCE(SUM(si.discount_amount), 0) + COALESCE(SUM(si.total_taxes_and_charges), 0)) AS n_sale,
            si.name AS parent_name
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 AND si.name IN %(sales_invoices)s
    """
    sales_analysis = frappe.db.sql(sales_analysis_query, {
                                  'sales_invoices': tuple(sales_invoices_list)}, as_dict=True)
    # Sales Department query
    sales_department_query = """
        SELECT sii.item_group AS item, SUM(sii.amount) AS amount
        FROM `tabSales Invoice Item` sii
        WHERE sii.docstatus = 1 AND sii.parent IN %(sales_invoices)s
        GROUP BY sii.item_group
    """
    sales_department = frappe.db.sql(sales_department_query, {
                                    'sales_invoices': tuple(sales_invoices_list)}, as_dict=True)

    payment_type_query = """
                    SELECT 
                        sip.mode_of_payment AS type, 
                        (SUM(si.total) - COALESCE(SUM(si.discount_amount), 0) + COALESCE(SUM(si.total_taxes_and_charges), 0)) AS total
                    FROM 
                        `tabSales Invoice` si
                    JOIN 
                        `tabSales Invoice Payment` AS sip ON si.name = sip.parent
                    WHERE 
                        si.docstatus = 1 AND si.name IN %(sales_invoices)s
                    GROUP BY 
                        sip.mode_of_payment;
                    """

    payment_type = frappe.db.sql(payment_type_query, {
                                'sales_invoices': tuple(sales_invoices_list)}, as_dict=True)
    return_querry = """
    SELECT
        si.grand_total AS grand_total,
        si.return_against AS return_against
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
    AND si.is_return = 1 
    AND si.name IN %(sales_invoices)s
    """

    payment_return_query = frappe.db.sql(
        return_querry, {'sales_invoices': tuple(sales_invoices_list)}, as_dict=True)
    payment_row = []

    for payment in payment_type:
        payment_total = payment.get('total', 0)
        payment_type_name = payment.get('type')

        found_existing = False

        for return_invoice in payment_return_query:
            grand_total = return_invoice.get('grand_total', 0)
            return_against = return_invoice.get('return_against')

            doc = frappe.get_doc("Sales Invoice", return_against)

            for payment_doc in doc.payments:
                mode_of_payments = payment_doc.get("mode_of_payment")

                if mode_of_payments == payment_type_name:
                    entry_found = False
                    for entry in payment_row:
                        if entry['payment_type'] == payment_type_name:
                            entry['adjusted_total'] += grand_total
                            entry_found = True
                            break

                    if not entry_found:
                        payment_row.append({
                            "payment_type": payment_type_name,
                            "adjusted_total": grand_total + payment_total
                        })

                    found_existing = True
                    break
        if not found_existing:
            payment_row.append({
                "payment_type": payment_type_name,
                "adjusted_total": payment_total
            })
    # Purchase Analysis query
    purchase_analysis_query = """
        SELECT 
            pi.supplier_name AS name, SUM(pi.grand_total) AS grand_total, pi.posting_date AS posting
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1 AND pi.posting_date = %(date)s
        GROUP BY pi.supplier_name
    """
    purchase_analysis = frappe.db.sql(purchase_analysis_query, {
                                     'date': start_date}, as_dict=True)

    cost_center_condition = ""
    if cost_center:
        cost_center_condition = "AND jea.cost_center = %(cost_center)s"

    cash_flow_query = f"""
        SELECT jea.account, SUM(jea.debit) AS debit
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON jea.parent = je.name
        JOIN `tabAccount` a ON jea.account = a.name
        WHERE je.docstatus = 1 
        AND je.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND je.voucher_type = 'Cash Entry'
        {cost_center_condition}  -- Include cost center condition if provided
        GROUP BY jea.account
        HAVING SUM(jea.debit) > 0
    """

    # Execute the query
    cash_flow = frappe.db.sql(cash_flow_query, {
        'from_date': start_date,
        'to_date': end_date,
        'cost_center': cost_center if cost_center else None
    }, as_dict=True)

    # Constructing data for output
    data.append({"group": "<b>SALES ANALYSIS</b>", "des": "", "amount": ""})
    desc = ["Sales", "Returns", "<b>G.Sales</b>",
            "Discount", "Sales Tax", "<b>N.Sales</b>"]
    if sales_analysis:
        amount = [
            sales_analysis[0]['sale'],
            sales_analysis[0]['r_sale'],
            sales_analysis[0]['g_sale'],
            sales_analysis[0]['discount'],
            sales_analysis[0]['tax'],
            sales_analysis[0]['n_sale']
        ]
        for d, a in zip(desc, amount):
            data.append({"group": "", "des": d, "amount": a})

    data.append({"group": "<b>SALES BY PAYMENT TYPES</b>",
                "des": "", "amount": ""})
    for i in payment_row:
        data.append(
            # {"group": "", "des": i['payment_type'], "amount": i['adjusted_total']})
            {"group": "", "des": i['payment_type'], "amount": flt(i['adjusted_total'])+abs(flt(sales_analysis[0]['r_sale']))  })

    data.append({"group": "<b>SALES BY DEPARTMENTS</b>",
                "des": "", "amount": ""})
    total_department_sales = 0
    for d in sales_department:
        data.append({"group": "", "des": d['item'], "amount": d['amount']})
        total_department_sales += d['amount']
    data.append({"group": "", "des": "DEPARTMENT SALES : ",
                "amount": round(total_department_sales, 2)})

    data.append({"group": "<b>ADVANCE BOOKINGS</b>", "des": "", "amount": ""})

    data.append({"group": "<b>PURCHASE ANALYSIS</b>", "des": "", "amount": ""})
    total_purchase = 0
    for g in purchase_analysis:
        data.append(
            {"group": "", "des": g['name'], "amount": g['grand_total']})
        total_purchase += g['grand_total']
    data.append({"group": "", "des": "TOTAL PURCHASE: ",
                "amount": round(total_purchase, 2)})

    data.append({"group": "<b>CASH FLOW</b>", "des": "", "amount": ""})
    if sales_analysis:
        data.append({"group": "", "des": "Sales",
                    "amount": sales_analysis[0]['n_sale']})
    total_payment = 0
    for c in cash_flow:
        data.append({"group": "", "des": c['account'], "amount": c['debit']})
        total_payment += c['debit']

    if sales_analysis:
        n_sale = sales_analysis[0]['n_sale']
        # Deduct both total payment and total purchase from net sales for the cash balance
        cash_balance = n_sale - total_payment - total_purchase
        data.append({"group": "", "des": "<b>Total Payments</b>",
                    "amount": total_payment})
        data.append({"group": "", "des": "<b>Cash Balance</b>",
                    "amount": cash_balance})

    return data


def get_columns(filters):
    columns = [
        {"label": _("Group"), "fieldname": "group",
         "fieldtype": "Data", "width": 200, "align": "left"},
        {"label": _("DESCRIPTION"), "fieldname": "des",
         "fieldtype": "Data", "width": 500, "align": "left"},
        {"label": _("AMOUNT"), "fieldname": "amount",
         "fieldtype": "Currency", "width": 200, "align": "right"}
    ]
    return columns


@frappe.whitelist()
def get_user_branches():
    current_user = frappe.session.user
    if current_user == "Administrator":
        get_branches_query = """
            SELECT ppu.parent 
            FROM `tabPOS Profile User` AS ppu
            GROUP BY ppu.parent
        """
        get_branches = frappe.db.sql(get_branches_query, as_list=True)
    else:
        user_branches = frappe.get_all('POS Profile User', filters={
                                      'user': current_user}, fields=['parent'])
        get_branches = [[ub['parent']] for ub in user_branches]

    branches = [item for sublist in get_branches for item in sublist]
    return branches
