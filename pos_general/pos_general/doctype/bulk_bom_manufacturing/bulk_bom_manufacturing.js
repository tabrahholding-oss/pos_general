frappe.ui.form.on('Bulk BOM Manufacturing', {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && !frm.doc.stock_created) {
            frm.add_custom_button(__('Create Manufacturing Entries'), function () {
                frappe.confirm(
                    __('Are you sure you want to create Manufacturing Stock Entries? This cannot be done again from this document.'),
                    function () {
                        frappe.call({
                            method: 'pos_general.pos_general.doctype.bulk_bom_manufacturing.bulk_bom_manufacturing.create_manufacturing_entries',
                            args: {
                                docname: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Creating Manufacturing Entries...'),
                            callback: function (r) {
                                if (!r.exc) {
                                    frappe.msgprint(__('Manufacturing Entries Created Successfully'));
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            });
        }

        if (frm.doc.docstatus === 1 && frm.doc.stock_created) {
            frm.dashboard.add_comment(
                __('Manufacturing entries already created for this document.'),
                'green',
                true
            );
        }
    }
});

frappe.ui.form.on('Bulk BOM Manufacturing Item', {
    bom(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.bom) {
            frappe.db.get_value('BOM', row.bom, 'item')
                .then(r => {
                    frappe.model.set_value(cdt, cdn, 'item_code', r.message.item);
                });
        }
    }
});