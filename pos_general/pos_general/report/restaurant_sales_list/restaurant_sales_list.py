import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_data(filters):
    data = []

    if not filters or not filters.get('from_date') or not filters.get('to_date'):
        return data

    from_date = filters.get('from_date')
    to_date = filters.get('to_date')
    status = filters.get('status', 'Paid')
    branch = filters.get("pos_profile")
    # Initialize grand total
    grand_total_sum = 0.0

    invoice_items = frappe.db.sql("""
    SELECT 
        si.customer, 
        si.name, 
        u.full_name AS owner_full_name, 
        si.posting_date, 
        si.posting_time, 
        sip.mode_of_payment, 
        si.grand_total,
        i.item_group AS order_type
    FROM 
        `tabSales Invoice` si
    LEFT JOIN 
        `tabSales Invoice Payment` sip ON si.name = sip.parent
    INNER JOIN 
        (SELECT parent, item_code, MIN(idx) AS min_idx FROM `tabSales Invoice Item` GROUP BY parent) sii_min 
        ON si.name = sii_min.parent
    INNER JOIN 
        `tabItem` i ON sii_min.item_code = i.item_code
    LEFT JOIN 
        `tabUser` u ON si.owner = u.name
    WHERE 
        si.posting_date >= %(from_date)s
        AND si.posting_date <= %(to_date)s
        AND si.status = %(status)s
        AND (%(branch)s IS NULL OR si.pos_profile = %(branch)s)
""", {
        'from_date': from_date,
        'to_date': to_date,
        'status': status,
        'branch': branch
    }, as_dict=True)

    # Populate data and calculate grand total
    for item in invoice_items:
        data.append({
            "customer": item.get("customer"),
            "order_type": item.get("order_type"),  # First item's order type
            "name": item.get("name"),
            "owner": item.get("owner_full_name"),
            "posting_date": item.get("posting_date"),
            'posting_time': item.get("posting_time"),
            'mode_of_payment': item.get("mode_of_payment"),
            "grand_total": item.get("grand_total"),
        })
        grand_total_sum += float(item.get("grand_total", 0))

    # Append grand total row
    data.append({
        "customer": '',
        "order_type": '',
        "name": '',
        "owner": '',
        'posting_date': '',
        'posting_time': '',
        "mode_of_payment": 'Grand Total',
        "grand_total": "{:,.2f}".format(grand_total_sum)
    })

    return data


def get_columns(filters):
    columns = [
        {"label": _("Customer Name"), "fieldname": "customer",
         "fieldtype": "Link", "options": "Customer", "width": 200},
        {"label": _("Order Type"), "fieldname": "order_type",
         "fieldtype": "Data", "width": 200},
        {"label": _("Order No"), "fieldname": "name",
         "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
        {"label": _("Order Taker"), "fieldname": "owner",
         "fieldtype": "Data", "width": 160},
        {"label": _("Order Date"), "fieldname": "posting_date",
         "fieldtype": "Date", "width": 160},
        {"label": _("Order Time"), "fieldname": "posting_time",
         "fieldtype": "DateTime", "width": 160},
        {"label": _("Payment Mode"), "fieldname": "mode_of_payment",
         "fieldtype": "Data", "width": 200},
        {"label": _("Grand Total"), "fieldname": "grand_total",
         "fieldtype": "Currency", "width": 200},
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
