// Copyright (c) 2024, Hussain and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Add-Ons', {
	refresh: function(frm) {
		
		frm.set_query("dependent_item", function () {
			return {
				filters: {
					variant_of: frm.doc.item,
				},
			};
		});
		frm.set_query("dependent_item_attribute", function() {
			if(frm.doc.item != ""){
				return {
					query: "pos_general.pos_general.doctype.item_add_ons.item_add_ons.item_attribute_query",
					filters: {
						"item": frm.doc.item
					}
				}
			}
			
		});
	},
	dependent_item_attribute:function(frm){
		if(frm.doc.dependent_item_attribute){
			frappe.call({
				method: 'pos_general.pos_general.doctype.item_add_ons.item_add_ons.get_attr_values',
				args:{
					item:frm.doc.item,
					attribute:frm.doc.dependent_item_attribute
				},
				callback: function(r) {
					if (r.message) {
						console.log("working")
						console.log(r.message)
						let options = r.message.map(attr => {
						    return { label: attr.attribute_value, value: attr.attribute_value };
						});
						frm.set_df_property('dependent_item_attribute_value', 'options', options);
					}
				}
			});
		}
		
	}
});

frappe.ui.form.on('Item Add Ons Child', {
	item:function(frm,cdt,cdn){
		var cdoc = locals[cdt][cdn]
		frappe.model.set_value(cdt, cdn, "deal_price", frm.doc.deal_price);
		if (cdoc.item){
			frappe.call({
				method: "pos_general.pos_general.doctype.item_add_ons.item_add_ons.get_price_list_rate",
				args: {
					item_code: cdoc.item,
					uom: cdoc.uom
				},
				callback: function (r) {
					var cdoc = locals[cdt][cdn]
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "rate", r.message)
					}
				}
			})
		}
	}
});