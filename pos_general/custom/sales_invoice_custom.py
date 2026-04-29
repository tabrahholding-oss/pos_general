import frappe

def on_submit(self, m=None):
            
    if self.table_no:
        table = frappe.get_doc("Table Management", self.table_no)
        table.status = "Available"
        table.save()

def on_update(self,m=None):
    if self.table_no:
        table = frappe.get_doc("Table Management",self.table_no)
        table.status = "Reserved"
        table.save()

def on_cancel(self,m=None):
    if self.table_no:
        table = frappe.get_doc("Table Management",self.table_no)
        table.status = "Available"
        table.save()

def before_save_invoice(doc, method):
    resturent_type = doc.resturent_type
    price_list = frappe.db.get_value("Price List", {"order_type": resturent_type}, "name")
    
    if price_list:
        doc.selling_price_list = price_list
    else:
        doc.selling_price_list = frappe.get_cached_value("POS Profile", doc.pos_profile, "selling_price_list")