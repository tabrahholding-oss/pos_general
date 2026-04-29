// Copyright (c) 2024, Hussain and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Restaurant Sales List"] = {
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
			"fieldname":"pos_profile",
			"label": __("Branch"),
			"fieldtype": "Select",
			"options": [],
		}
    ],
    onload: function() {
        // Fetch allowed branches for the current user
        frappe.call({
            method: "pos_general.pos_general.report.restaurant_sales_list.restaurant_sales_list.get_user_branches",
            callback: function(response) {
                if (response.message) {
                    var allowed_branches = response.message;
                    var branch_filter = frappe.query_report.get_filter('pos_profile');
                    branch_filter.df.options = allowed_branches;
                    branch_filter.refresh();
                }
            }
        });
    }
};
