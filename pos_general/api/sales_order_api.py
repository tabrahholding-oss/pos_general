import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_sales_order_details(customer, limit_start, limit_page_length, order_by='desc'):
    sales_order_meta = frappe.get_meta('Sales Order')
    fields = [field.fieldname for field in sales_order_meta.fields]
    
    sales_orders = frappe.get_all('Sales Order',
                                  filters={'customer': customer},
                                  fields=['name'],
                                  order_by='creation ' + order_by,
                                  limit_start=int(limit_start),
                                  limit_page_length=int(limit_page_length))

    sales_orders_data = []

    for so in sales_orders:
        sales_order = frappe.get_doc("Sales Order", so.name)
        sales_order_data = sales_order.as_dict()
        
        if 'items' in sales_order_data:
            sales_order_data['items'] = [item.as_dict() for item in sales_order.items]
        
        sales_orders_data.append(sales_order_data)

    return sales_orders_data

@frappe.whitelist(allow_guest=True)
def get_sales_order_with_item_specifics(sales_order_name):
   
    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    
    response = sales_order.as_dict() 

    response["items"] = [] 

    for item in sales_order.items:
        item_dict = item.as_dict()

        if not item.is_stock_item:
            product_bundle = frappe.get_all('Product Bundle', filters={'new_item_code': item.item_code}, fields=['name'])

            if product_bundle:
                bundle_name = product_bundle[0].name
                item_specifics = frappe.get_all('Item Specifics Child', filters={'parent': bundle_name}, fields=['item_specifics_name'])
                
                item_specifics_list = [child.item_specifics_name for child in item_specifics]

                item_dict['item_specifics'] = item_specifics_list

        response["items"].append(item_dict)

    return response





