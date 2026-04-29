// Copyright (c) 2024, Hussain and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Inventory Variance Before Closing"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			// "fieldtype": "Datetime",
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			// "fieldtype": "Datetime",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			// "get_query": function() {
			// 	const company = frappe.query_report.get_filter_value('company');
			// 	return {
			// 		filters: { 'company': company }
			// 	}
			// }
		},
		{
			"fieldname":"item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			// "get_query": function() {
			// 	return {
			// 		query: "erpnext.controllers.queries.item_query"
			// 	}
			// }
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},

	]
};
