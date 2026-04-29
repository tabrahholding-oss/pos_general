// frappe.provide("erpnext.stock");

frappe.ui.form.on("Stock Take", {
	refresh: function (frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Stock Reconciliation'),
                function () {
                    frappe.model.open_mapped_doc({
                        method: "pos_general.pos_general.doctype.stock_take.stock_take.make_stock_reconciliation",
                        frm: frm
                    });
                }, __("Create"), "btn-primary");            
        }

		if(frm.doc.docstatus==0) {
			if(!frm.doc.posting_date) {
				frm.set_value('posting_date', frappe.datetime.nowdate());
			}
			if(!frm.doc.posting_time) {
				frm.set_value('posting_time', frappe.datetime.now_time());
			}
			set_posting_date_and_time_read_only(frm);
		}
	
	},
	onload: function (frm) {
        frm.set_query('branch', function () {
            if (!frm.doc.company) {
                frappe.msgprint(__("Please select Company first"));
                return;
            }
            return {
                filters: {
                    "company": frm.doc.company,                    
                }
            };
        });

	    frm.set_query("item_code", "items", function() {
			return {
				query: "pos_general.pos_general.doctype.stock_take.stock_take.warehouse_items",
				filters:{
					// "is_stock_item": 1,
					"warehouse": frm.doc.warehouse,
					"posting_date": frm.doc.posting_date,
					"posting_time": frm.doc.posting_time,
					"company": frm.doc.company
				}
			}
		} );


		frm.set_query("warehouse", "warehouses", function() {
			return {
				query: "pos_general.pos_general.doctype.stock_take.stock_take.filter_branch_warehouses",
				filters:{
					"branch": frm.doc.branch
				}
			}
		} );


		frm.set_query("item_groups", function () {
			if (!(frm.doc.warehouse || frm.doc.branch)) {
                frappe.msgprint(__("Please select Branch or Warehouse first"));
                return;
            }

			let warehouses = [];
			if (frm.doc.warehouse){
				warehouses.push(frm.doc.warehouse);
			}
			else {
				frm.doc.warehouses.forEach((warehouse) => {
					warehouses.push(warehouse.warehouse);
				})
			}

            return {
				query: "pos_general.pos_general.doctype.stock_take.stock_take.warehouse_item_groups",
                filters: {
                    "warehouses": warehouses,
					"posting_date": frm.doc.posting_date,
					"posting_time": frm.doc.posting_time,
					"company": frm.doc.company
                }
            };
        });

		// frm.set_df_property("warehouses", "read_only", 1);
	},
	branch: function(frm) {
		if(frm.doc.branch){
			frm.set_value("item_groups", null);
			frappe.call({
				method: "pos_general.pos_general.doctype.stock_take.stock_take.get_branch_warehouses",
				args: {
					branch: frm.doc.branch
				},
				callback: function(r) {
					if (r.exc || !r.message || !r.message.length) return;
		
					frm.clear_table("warehouses");
		
					r.message.forEach((row) => {
						let item = frm.add_child("warehouses");
						$.extend(item, row);
		
						item.warehouse = item.warehouse_name;
												
					});
					frm.refresh_field("warehouses");
					// frm.set_df_property("warehouses", "read_only", 1);

					frm.events.populate_branch_warehouse_items(frm);
					
				}
			});
		}

	
},

item_groups: function(frm) {
	if (frm.doc.item_groups){		
		frm.clear_table("items");		
		frm.refresh_field("items");			
		if(frm.doc.warehouse){
			frm.events.populate_items(frm, frm.doc.warehouse);
		}
		if(frm.doc.branch){
			frm.events.populate_branch_warehouse_items(frm);
		}
	}
	
},

location: function(frm) {
	if(frm.doc.location == "Warehouse"){
		frm.set_query("warehouse", function(frm, cdt, cdn) {			
				return {					
					filters: { }
				}	
			});
	}	

	if(frm.doc.location == "Branch") {
		frm.set_value("branch", null);
	}

	frm.set_value("warehouse", null);
	frm.set_value("item_groups", null);
},

warehouse: function(frm) {
	if(frm.doc.warehouse){	
		
		frm.clear_table("items");
		frm.set_value("item_groups", null);
		frm.refresh_field("items");
		frm.events.populate_items(frm, frm.doc.warehouse);
	}

},
populate_branch_warehouse_items: function(frm){

	frm.clear_table("items");
	frm.refresh_field("items");
	frm.doc.warehouses.forEach((warehouse) => {
		frm.events.populate_items(frm, warehouse.warehouse);
	});

},
populate_items: function(frm, warehouse){

	let item_groups = [];
	if (frm.doc.item_groups){
		frm.doc.item_groups.forEach(row => {
			item_groups.push(row.item_group)
		});
	}
	
	let count_type = [];
	if (frm.doc.count_type){
		count_type.push(frm.doc.count_type)
	}
		
	

	frappe.call({
		method: "pos_general.pos_general.doctype.stock_take.stock_take.get_items",
		args: {
			warehouse: warehouse,
			posting_date: frm.doc.posting_date,
			posting_time: frm.doc.posting_time,
			company: frm.doc.company,
			item_groups: item_groups,
			count_type: count_type,
		},
		callback: function(r) {
			if (r.exc || !r.message || !r.message.length) return;				

			r.message.forEach((row) => {
				let item = frm.add_child("items");
				$.extend(item, row);
				item.current_stock = item.qty || 0;
				item.physical_stock = item.qty || 0;
			});
			frm.refresh_field("items");
		}
	});
},

set_posting_time: function(frm) {
	set_posting_date_and_time_read_only(frm);
},

posting_date: function(frm) {
	frm.trigger("set_qty_for_all_items");
},

posting_time: function(frm) {
	frm.trigger("set_qty_for_all_items");
},

set_qty_for_all_items: function(frm) {
	frm.doc.items.forEach(row => {
		frm.events.set_item_qty(frm, row.doctype, row.name);
	});
},

set_item_qty: function(frm, cdt, cdn) {
	var d = frappe.model.get_doc(cdt, cdn);

	if(d.item_code && frm.doc.warehouse) {
		frappe.call({
			method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for",
			args: {
				item_code: d.item_code,
				warehouse: frm.doc.warehouse,
				posting_date: frm.doc.posting_date,
				posting_time: frm.doc.posting_time,				
			},
			callback: function(r) {				
				frappe.model.set_value(cdt, cdn, "current_stock", r.message.qty);
			}
		});
	}
},

})



frappe.ui.form.on("Stock Take Item", {
	"physical_stock": function(frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		var diff = item.physical_stock - item.current_stock;
		frappe.model.set_value(cdt, cdn, "stock_difference", diff);		
		// frm.refresh_field("stock_difference", cdn);
	},

	item_code: function(frm, cdt, cdn) {	
		frm.events.set_item_qty(frm, cdt, cdn);
	}
});


frappe.ui.form.on("Branch Warehouse", {
	warehouse: function(frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		frm.events.populate_branch_warehouse_items(frm);
	},

	warehouses_remove: function (frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		frm.events.populate_branch_warehouse_items(frm);
	}
});

function set_posting_date_and_time_read_only(frm) {

	if (frm.doc.set_posting_time) {
		frm.set_df_property('posting_date', 'read_only', 0);
		frm.set_df_property('posting_time', 'read_only', 0);
	} else {
		frm.set_df_property('posting_date', 'read_only', 1);
		frm.set_df_property('posting_time', 'read_only', 1);
	}
}