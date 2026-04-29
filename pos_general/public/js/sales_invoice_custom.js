frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
      if (frm.doc.docstatus === 1) {
        frm.add_custom_button(
          'Cancel with Linked Docs',
          async () => {
            frappe.confirm(
              `This will cancel all linked docs (Stock Entries, Payments, Auto BOM Consumption) and then cancel <b>${frm.doc.name}</b>. Continue?`,
              async () => {
                try {
                  frappe.show_progress('Cancelling...', 50, 100, 'Please wait');
                  const r = await frappe.call({
                    method: 'pos_general.api.cancel_chain.cascade_cancel_sales_invoice',
                    args: { si_name: frm.doc.name },
                    freeze: true,
                    freeze_message: 'Cancelling linked documents...'
                  });
                  const res = r.message || r;
                  const log = (res && res.log) ? res.log.join('<br>') : 'Done';
                  frappe.msgprint({ title: 'Cancel Report', message: log, indicator: res.ok ? 'green' : 'red' });
                  await frm.reload_doc();
                } catch (e) {
                  frappe.msgprint({ title: 'Cancel Failed', message: e.message || e, indicator: 'red' });
                } finally {
                  frappe.hide_progress();
                }
              }
            );
          }
        ).addClass('btn-danger');
      }
    }
  });