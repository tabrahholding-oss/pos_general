// Copyright (c) 2026, Hussain and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Clearing Reconciliation Entry", {
	refresh(frm) {
        ////
    },
    clearing_account: function (frm) {
        console.log("function run")
        maybe_fetch_balance(frm);
    },
    from_date: function (frm) {
        console.log("function run")
        maybe_fetch_balance(frm);
    },
    to_date: function (frm) {
        console.log("function run")
        maybe_fetch_balance(frm);
    },
});

  
// --- Child: recalc row + update parent total whenever something changes
frappe.ui.form.on('Payment Clearing Accounts', {
    amount(frm, cdt, cdn) {
        // If users edit amount directly
        update_total(frm);
    },
    items_add(frm, cdt, cdn) {
        update_total(frm);
    },
    items_remove(frm, cdt, cdn) {
        update_total(frm);
    }
});

function update_total(frm) {
    let total = 0;
    (frm.doc.payment_clearing_accounts || []).forEach(row => {
        total += flt(row.amount);
    });
    let diff = frm.gross_amount_as_per_pos - total
    frm.set_value('difference', Math.abs(diff));
    frm.set_value('net_amount', total);
}

// Short-hand float helper (uses frappe’s flt if present)
function flt(v) { return frappe?.utils?.flt ? frappe.utils.flt(v) : (parseFloat(v) || 0); }
    
function maybe_fetch_balance(frm) {
    const d = frm.doc;
    if (!d.clearing_account || !d.from_date || !d.to_date) return;
    
    frm.fields_dict.opening_balance?.set_value?.(null); // optional: clear while loading
    frappe.call({
        method: 'pos_general.pos_general.doctype.payment_clearing_reconciliation_entry.payment_clearing_reconciliation_entry.get_account_balances',
        args: {
        account: d.clearing_account,
        from_date: d.from_date,
        to_date: d.to_date,
        },
        freeze: false,
        callback: (r) => {
        console.log("function chl gya ")
        console.log(r);
        if (!r.message) return;
        const { opening, debit, credit, closing } = r.message;
        frm.set_value('gross_amount_as_per_pos', closing);
        frm.refresh_fields(['gross_amount_as_per_pos']);
        }
    });
}
