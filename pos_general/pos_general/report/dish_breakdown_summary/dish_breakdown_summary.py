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
    branch = filters.get("name")

    # Retrieve distinct item groups
    item_groups = frappe.db.sql("""
    SELECT DISTINCT i.item_group
    FROM `tabSales Invoice` si
    INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
    INNER JOIN `tabItem` i ON sii.item_code = i.item_code
    WHERE si.posting_date >= %(from_date)s
      AND si.posting_date <= %(to_date)s
      AND si.status = %(status)s
      AND (%(branch)s IS NULL OR si.pos_profile = %(branch)s)
    ORDER BY i.item_group ASC
""", {
        'from_date': from_date,
        'to_date': to_date,
        'status': status,
        'branch': branch
    }, as_dict=True)

    for cat_type in item_groups:
        item_group = cat_type.get('item_group')

        # Initialize totals for each item group
        item_group_totals = {
            "item_code": "Category: %s" % item_group,
            "item_name": '',
            "qty": 0.0,
            "rate": 0.0,
            'amount_discount': 0.0,
            'tax': 0.0,
            "base_amount": 0.0,
        }
        data.append(item_group_totals)
        restaurant_totals = {
            "item_code": "",
            "item_name": item_group,
            "qty": 0.0,
            "rate": 0.0,
            'amount_discount': 0.0,
            'tax': 0.0,
            "base_amount": 0.0,
        }

        invoice_items = frappe.db.sql("""
            SELECT sii.item_code, sii.item_name, SUM(sii.qty) as qty, 
                sii.rate as rate, SUM(sii.base_amount) as base_amount
            FROM `tabSales Invoice` si
            INNER JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
            INNER JOIN `tabItem` i ON sii.item_code = i.item_code
            WHERE si.posting_date >= %(from_date)s
            AND si.posting_date <= %(to_date)s
            AND si.status = %(status)s
            AND i.item_group = %(item_group)s
            AND (%(branch)s IS NULL OR si.pos_profile = %(branch)s)
            GROUP BY sii.item_code
        """, {
            'from_date': from_date,
            'to_date': to_date,
            'status': status,
            'item_group': item_group,
            'branch': branch
        }, as_dict=True)

        # Populate totals for the current item group
        for item in invoice_items:
            data.append({
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "qty": item.get("qty"),
                "rate": item.get("rate"),
                'amount_discount': 0.0,
                'tax': 0.0,
                "base_amount": item.get("base_amount"),
            })
            base_amount = float(item.get("base_amount", 0))
            restaurant_totals["base_amount"] += base_amount

        formatted_total = "Net Value Total = {:,.2f}".format(
            restaurant_totals["base_amount"])

        data.append({
            "item_code": '',
            "item_name": '',
            "qty": '',
            "rate": '',
            'amount_discount': 0.0,
            'tax': 0.0,
            "base_amount": formatted_total,
        })

    return data


def get_columns(filters):
    columns = [
        {"label": _("Item Code"), "fieldname": "item_code",
         "fieldtype": "Link", "options": "Sales Invoice Item", "width": 200},
        {"label": _("Item Desc"), "fieldname": "item_name",
         "fieldtype": "Data", "width": 200},
        {"label": _("Item Qty"), "fieldname": "qty",
         "fieldtype": "Data", "width": 160},
        {"label": _("Item Price"), "fieldname": "rate",
         "fieldtype": "Data", "width": 160},
        {"label": _("Discount Amount"), "fieldname": "amount_discount",
         "fieldtype": "Data", "width": 160},
        {"label": _("Tax"), "fieldname": "tax",
         "fieldtype": "Data", "width": 160},
        {"label": _("Net Value"), "fieldname": "base_amount",
         "fieldtype": "Data", "width": 200},
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
