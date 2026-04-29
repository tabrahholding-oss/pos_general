frappe.query_reports["Daily Sales Summary Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "pos_profile",
            "label": __("POS Profile"),
            "fieldtype": "Link",
            "options": "POS Profile",
            "reqd": 0
        },
        {
            "fieldname": "order_type",
            "label": __("Order Type"),
            "fieldtype": "Link",
            "options": "Order Type",
            "reqd": 0
        },
        {
            "fieldname": "mode_of_payment",
            "label": __("Mode of Payment"),
            "fieldtype": "Link",
            "options": "Mode of Payment",
            "reqd": 0
        }
    ]
};
