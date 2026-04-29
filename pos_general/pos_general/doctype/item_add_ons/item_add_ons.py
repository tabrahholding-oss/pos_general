# Copyright (c) 2024, Hussain and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.data import today
from erpnext.stock.get_item_details import get_conversion_factor, get_item_price

class ItemAddOns(Document):
    pass


@frappe.whitelist()
def get_price_list_rate(item_code,uom):
    args_for_get_price_list = {
        "price_list":"Standard Selling",
        "item_code":item_code,
        "uom":uom
    }
    price_rate = get_item_price(args_for_get_price_list,item_code)
    # print("price_rate",price_rate)
    if len(price_rate)>0:
        return price_rate[0][1]
    else:
        return 0

@frappe.whitelist()
def item_attribute_query(doctype, txt, searchfield, start, page_len, filters):
    item = filters.get("item")
    
    items = frappe.db.sql("""
        SELECT distinct it_attr.attribute
        FROM `tabItem Variant Attribute` it_attr
        JOIN `tabItem` it
        WHERE it_attr.parent = %s AND it.disabled = 0
    """, (item))
    return items

# @frappe.whitelist()
# def get_attr_values(item,attribute):
#     attr_vlu = frappe.db.sql("""
#         SELECT it_attr_value.attribute_value,it_attr_value.abbr
#         FROM `tabItem Attribute Value` it_attr_value
#         WHERE it_attr_value.parent = %s
#     """, (attribute))
#     print(attr_vlu)
#     return attr_vlu

@frappe.whitelist()
def get_attr_values(item, attribute):
    attr_vlu = frappe.db.sql("""
        SELECT it_attr_value.attribute_value, it_attr_value.abbr
        FROM `tabItem Attribute Value` it_attr_value
        WHERE it_attr_value.parent = %s
    """, (attribute))
    # Transform the result into a list of dictionaries
    return [{"attribute_value": row[0], "abbr": row[1]} for row in attr_vlu]
