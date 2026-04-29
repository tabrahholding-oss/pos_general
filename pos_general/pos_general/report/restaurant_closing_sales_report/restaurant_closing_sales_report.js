// Copyright (c) 2024, Hussain and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Restaurant Closing Sales Report"] = {
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
			"fieldname":"name",
			"label": __("Branch"),
			"fieldtype": "Select",
			"options": [],
		},
        {
            "fieldname": "posa_pos_opening_shift",
            "label": __("POS Opening Shift"),
            "fieldtype": "Link",
            "options": "POS Opening Shift",
            "default": "",
            "reqd": 0
        }



    ],
    onload: function() {
        // Fetch allowed branches for the current user
        frappe.call({
            method: "pos_general.pos_general.report.restaurant_closing_sales_report.restaurant_closing_sales_report.get_user_branches",
            callback: function(response) {
                if (response.message) {
                    var allowed_branches = response.message;
                    var branch_filter = frappe.query_report.get_filter('name');
                    branch_filter.df.options = allowed_branches;
                    branch_filter.refresh();
                }
            }
        });
    }
};
