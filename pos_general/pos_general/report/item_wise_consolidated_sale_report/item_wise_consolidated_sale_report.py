import frappe
from frappe import _
from datetime import datetime
from frappe.utils import cstr, cint, getdate

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_data(filters):
    data = []
    start_date = filters.get('from_date')
    end_date = filters.get('to_date')
    branch = filters.get('pos_profile')

    #Validate date range
    if end_date < start_date:
        raise ValueError("The 'End Date' cannot be earlier than the 'Start Date'.")
    # Ensure 'from_date' filter is provided
    if not filters or not filters.get('from_date'):
        return data

    # Query to fetch sales invoices related to POS Closing Shift
    query_closing_shift = """
        SELECT DISTINCT sir.sales_invoice AS invoice
        FROM `tabPOS Closing Shift` pcs
        JOIN `tabSales Invoice Reference` sir ON pcs.name = sir.parent
        WHERE pcs.period_start_date >= %(start_date)s
        And DATE(pcs.period_start_date)<= %(end_date)s
        AND pcs.pos_profile = %(branch)s
    """

    # Fetching sales invoices for the given date
    closing_shift_invoices = frappe.db.sql(query_closing_shift, {'start_date': filters.get('from_date'),'end_date':filters.get('to_date'),'branch': filters.get('pos_profile')}, as_dict=True)

    if closing_shift_invoices:
        # Extracting list of invoices from the result
        invoices_list = [item['invoice'] for item in closing_shift_invoices]
        
        # If no invoices are found, return empty data
        if not invoices_list:
            return data

        # Creating a comma-separated string of invoices for the next query
        invoices_str = ', '.join(["'%s'" % inv for inv in invoices_list])

        # Query to fetch sales invoice items data
        query_sales_invoice_items = f"""
            SELECT  
                sii.item_code, sii.item_name, sii.uom,
                ROUND(SUM(CASE WHEN sii.qty > 0 THEN sii.qty ELSE 0 END), 2) AS qty,
                ROUND(SUM(CASE WHEN sii.qty < 0 THEN sii.qty ELSE 0 END), 2) AS r_qty, 
                ROUND(SUM(sii.qty), 2) AS n_qty,
                ROUND(SUM(sii.qty * sii.rate), 2) as amount,  -- Ensure multiplication reflects correct logic
                sii.rate as price_list_rate,
                si.name as parent
            FROM
                `tabSales Invoice Item` sii
            JOIN
                `tabSales Invoice` si ON sii.parent = si.name
            WHERE sii.parent IN ({invoices_str})   
            GROUP BY
                sii.item_code, sii.item_name, sii.uom, sii.rate
            ORDER BY
                sii.item_code;
        """

        # Fetching sales invoice items data
        sales_invoice_items = frappe.db.sql(query_sales_invoice_items, as_dict=True)
        
        # Calculating total amount
        total_amount = sum(item['amount'] for item in sales_invoice_items)

        # Appending fetched data to the 'data' list
        for item in sales_invoice_items:
            data.append(item)

        # Adding a row for total amount
        total_row = {"item_code": "", "item_name": "<b>Total</b>", "qty": "", "r_qty": "", "n_qty": "",
                     "price_list_rate": "", "amount": round(total_amount, 2)}
        data.append(total_row)

    return data

def get_columns(filters):
    columns = [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 120},
        {"label": _("QTY"), "fieldname": "qty", "fieldtype": "Float", "width": 120},
        {"label": _("R.QTY"), "fieldname": "r_qty", "fieldtype": "Float", "width": 120},
        {"label": _("N.QTY"), "fieldname": "n_qty", "fieldtype": "Float", "width": 120},
        {"label": _("Rate"), "fieldname": "price_list_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120}
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
        user_branches = frappe.get_all('POS Profile User', filters={'user': current_user}, fields=['parent'])
        get_branches = [[ub['parent']] for ub in user_branches]

    branches = [item for sublist in get_branches for item in sublist]
    return branches