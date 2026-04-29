
import frappe

@frappe.whitelist()
def get_items_pos(item_group):
    item_list = frappe.get_all(
        'Item',
        filters={"item_group":item_group,"has_variants":"0"},
        fields=['*'],
        
    )
    for item in item_list:
        item_price = frappe.get_all('Item Price',
                                   filters={"item_code":item.item_code},
                                   fields=['*'],)
        attachments = frappe.get_all('File',
                                    filters={"attached_to_doctype":"Item","attached_to_name":item.name},
                                    fields=['*'],)
        item['item_price'] = item_price
        item['Attachments'] = attachments
    return item_list
