# # customer_api.py

import frappe

# @frappe.whitelist(allow_guest=True)
# def get_customer_details(customer_name=None, mobile_no=None):
    
   
#     filters = []
    
#     if customer_name:
#         filters.append(["customer_name", "like", f"%{customer_name}%"])
#     if mobile_no:
#         filters.append(["mobile_no", "like", f"%{mobile_no}%"])
    
#     if not filters:
#         return []

#     query = """
#     SELECT *
#     FROM `tabCustomer`
#     WHERE {}
#     """.format(" OR ".join([f"{filter[0]} LIKE %s" for filter in filters]))

#     parameters = [filter[2] for filter in filters]

#     customers = frappe.db.sql(query, tuple(parameters), as_dict=True)

#     return customers

@frappe.whitelist()
def get_customer_details(customer_group=None, searchText=None):
    # Construct the SQL query to fetch all columns
    result = frappe.db.sql("""
        SELECT * 
        FROM `tabCustomer` 
        WHERE 
            (member_id = %s OR member = %s OR customer_name = %s) 
            AND (customer_group = %s OR %s IS NULL)
            AND is_member = '1' 
            AND disabled = '0'
    """, (searchText, searchText, searchText, customer_group, customer_group), as_dict=True)

    return result
