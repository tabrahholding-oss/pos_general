import frappe

def validate(self, m=None):
    self.order_time = max((i.cooking_time for i in self.items if i.is_kds_item), default=0)
    
    if self.table_no:
        table = frappe.get_doc("Table Management", self.table_no)
        if self.cancelled_from_app:
            table.status = "Available"
        else:
            table.status = "Reserved"
        table.save()