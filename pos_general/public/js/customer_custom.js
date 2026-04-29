frappe.ui.form.on('Customer', {

    refresh: function(frm) {
		frm.fields_dict['open_issues'].grid.wrapper.find('.grid-remove-rows').hide();
		frm.fields_dict['open_issues'].grid.wrapper.find('.grid-add-row, .grid-remove-rows').css('display', 'none');
		frm.get_field('open_issues').grid.cannot_add_rows = true

        frm.fields_dict['loyalty_points_list'].grid.wrapper.find('.grid-remove-rows').hide();
		frm.fields_dict['loyalty_points_list'].grid.wrapper.find('.grid-add-row, .grid-remove-rows').css('display', 'none');
		frm.get_field('loyalty_points_list').grid.cannot_add_rows = true

	},
	onload: function(frm) {
        if (!frm.is_new()) {
            // Fetch issues related to the customer where status is open
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Issue',
                    filters: {
                        customer: frm.doc.name,
                        status: 'Open'
                    },
                    fields: ['name', 'subject', 'issue_type', 'priority', 'status']
                },
                callback: function(response) {
                    if (response.message) {
                        // Clear the existing items in the child table
                        frm.clear_table('open_issues');
                        
                        // Add the fetched issues to the child table
                        response.message.forEach(function(issue) {
                            let row = frm.add_child('open_issues');
                            row.issue = issue.name;
                            row.subject = issue.subject;
                            row.issue_type = issue.issue_type;
                            row.priority = issue.priority;
                            row.status = issue.status;
                        });
                        
                        // Refresh the field to update the form
                        frm.refresh_field('open_issues');
                    }
                }
            });


            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Loyalty Point Entry',
                    filters: {
                        customer: frm.doc.name
                    },
                    fields: ['name', 'loyalty_program', 'loyalty_program_tier', 'loyalty_points', 'invoice']
                },
                callback: function(response) {
                    if (response.message) {
                        frm.clear_table('loyalty_points_list');
            
                        let total_points = 0;
                        let redeemed_points = 0;
            
                        let fetch_invoice_details = function(loyalty_point) {
                            // Fetch the invoice document to get the Shopify Order ID
                            frappe.call({
                                method: 'frappe.client.get',
                                args: {
                                    doctype: 'Sales Invoice',
                                    name: loyalty_point.invoice
                                },
                                callback: function(invoice_response) {
                                    if (invoice_response.message) {
                                        let invoice_doc = invoice_response.message;
                                        let shopify_order_id = invoice_doc.shopify_order_id || '';
            
                                        
                                        // Add the loyalty point entry to the table with Shopify Order ID
                                        let row = frm.add_child('loyalty_points_list');
                                        row.name1 = loyalty_point.name;
                                        row.loyalty_program = loyalty_point.loyalty_program;
                                        row.loyalty_program_tier = loyalty_point.loyalty_program_tier;
                                        row.loyalty_points = loyalty_point.loyalty_points;
                                        row.invoice = loyalty_point.invoice;

                                        if (!shopify_order_id) {
                                            row.invoice_source = "POS Order"
                                        }
                                        else{
                                            row.invoice_source = "Shopify Order"
                                        }
            
                                        if (row.loyalty_points > 0) {
                                            total_points += row.loyalty_points;
                                        } else {
                                            redeemed_points += Math.abs(row.loyalty_points);
                                        }
            
                                        frm.refresh_field('loyalty_points_list');
            
                                        let available_points = total_points - redeemed_points;
            
                                        // Set the total, redeemed, and available points in the form fields
                                        frm.set_value('total_points_earned', total_points);
                                        frm.set_value('total_points_redeem', redeemed_points);
                                        frm.set_value('total_available_points', available_points);
                                    }
                                }
                            });
                        };
            
                        response.message.forEach(fetch_invoice_details);
                    }
                }
            });
            
        }
	}
});
