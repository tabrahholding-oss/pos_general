frappe.ui.form.on('POS Payment Method', {
	tax_and_charges: function(frm,cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.tax_and_charges) {
            frappe.db.get_doc('Sales Taxes and Charges Template', row.tax_and_charges)
                .then(doc => {
                    if (doc && doc.taxes && doc.taxes.length > 0) {
                        // Assuming you want the rate from the first matching tax
                        let rate = doc.taxes[0].rate;  // Adjust this logic as needed
                        frappe.model.set_value(cdt, cdn, 'tax_rate', rate);
                    }
                });
            }
	}
});
