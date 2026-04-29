// Copyright (c) 2024, Hussain and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily Sales Summary"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
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
            method: "pos_general.pos_general.report.daily_sales_summary.daily_sales_summary.get_user_branches",
            callback: function(response) {
                if (response.message) {
                    var allowed_branches = response.message;
					allowed_branches.unshift("");
                    var branch_filter = frappe.query_report.get_filter('pos_profile');
                    branch_filter.df.options = allowed_branches;
                    branch_filter.refresh();
                }
            }
        });
    }
};


