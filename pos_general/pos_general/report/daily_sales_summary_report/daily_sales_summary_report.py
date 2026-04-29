from frappe import _
from datetime import datetime
from frappe.utils import cstr, cint, getdate
import frappe  # Ensure frappe is correctly imported

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_data(filters):
    data = []

    # Ensure 'from_date' and 'to_date' filters are provided
    if not filters or not filters.get('from_date') or not filters.get('to_date'):
        return data

    from_date = filters.get('from_date')
    to_date = filters.get('to_date')
    pos_profile = filters.get('pos_profile')
    order_type = filters.get('order_type')
    mode_of_payment = filters.get('mode_of_payment')

    # Base SQL query
    sql_query = """
        SELECT 
            si.name AS invoice_name,
            si.resturent_type AS resturent_type,
            si.posting_date AS posting_date,
            si.total AS total,
            si.discount_amount AS discount_amount,
            si.base_total_taxes_and_charges AS base_total_taxes_and_charges,
            si.grand_total AS grand_total,
            mop.mode_of_payment AS mode_of_payment
        FROM 
            `tabSales Invoice` AS si
        LEFT JOIN 
            `tabSales Invoice Payment` AS mop ON si.name = mop.parent
        WHERE 
            si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
    """

    params = [from_date, to_date]

    if pos_profile:
        sql_query += " AND si.pos_profile = %s"
        params.append(pos_profile)
    if order_type:
        sql_query += " AND si.resturent_type = %s"
        params.append(order_type)
    if mode_of_payment:
        sql_query += " AND mop.mode_of_payment = %s"
        params.append(mode_of_payment)

    sql_query += " ORDER BY si.posting_date ASC"

    # Execute the SQL query
    sales_invoices = frappe.db.sql(sql_query, tuple(params), as_dict=True)

    # Initialize total variables
    total_gross = 0.0
    total_discount = 0.0
    total_tax = 0.0
    total_grand = 0.0

    # Prepare data for the report
    for invoice in sales_invoices:
        gross_total = float(invoice.get("total", 0))
        discount = float(invoice.get("discount_amount", 0))
        tax = float(invoice.get("base_total_taxes_and_charges", 0))
        grand_total = float(invoice.get("grand_total", 0))

        total_gross += gross_total
        total_discount += discount
        total_tax += tax
        total_grand += grand_total

        data.append({
            "resturent_type": invoice.get("resturent_type"),
            "posting_date": invoice.get("posting_date"),
            "total": gross_total,
            "discount_amount": discount,
            "base_total_taxes_and_charges": tax,
            "grand_total": grand_total,
        })

    # Append total row
    if sales_invoices:
        data.append({
            "resturent_type": "<b>Total</b>",
            "posting_date": "",
            "total": total_gross,
            "discount_amount": total_discount,
            "base_total_taxes_and_charges": total_tax,
            "grand_total": total_grand,
        })

    return data

def get_columns(filters):
    columns = [
        {"label": _("Restaurant Type"), "fieldname": "resturent_type", "fieldtype": "Link", "options": "Order Type", "width": 200},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 180},
        {"label": _("Gross Total"), "fieldname": "total", "fieldtype": "Float", "width": 200},
        {"label": _("Tax"), "fieldname": "base_total_taxes_and_charges", "fieldtype": "Float", "width": 200},
        {"label": _("Discount"), "fieldname": "discount_amount", "fieldtype": "Float", "width": 200},
        {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Float", "width": 200},
    ]
    return columns
