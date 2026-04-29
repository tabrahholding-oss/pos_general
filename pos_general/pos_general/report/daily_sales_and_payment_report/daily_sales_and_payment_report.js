// Copyright (c) 2025, Hussain and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Sales and Payment Report"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		  },
		  {
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
			on_change: function () {
				// clear pos_shift when date changes (optional but recommended)
				frappe.query_report.set_filter_value("pos_shift", "");
			  }
		  },
		  {
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end()
		  },
		  {
			fieldname: "pos_profile",
			label: __("POS Profile"),
			fieldtype: "Link",
			options: "POS Profile",
			reqd: 1,
		  },
		  {
			fieldname: "pos_shift",
			label: __("POS Shift"),
			fieldtype: "Link",
			options: "POS Opening Shift",
			get_query: function () {
				const d = frappe.query_report.get_filter_value("from_date");
				const pos_profile = frappe.query_report.get_filter_value("pos_profile");
				if (!d) return {};
		
				const start = `${d} 00:00:00`;
				const end   = `${d} 23:59:59`;
		
				return {
				  filters: {
					// replace 'opening_datetime' with your actual datetime field in Opening Shift
					period_start_date: ["between", [start, end]],
					docstatus: 1,
					pos_profile:pos_profile,
				  }
				};
			}
		  }
	]
};

/* eslint-disable */
