import frappe
from typing import List, Dict, Any
from datetime import datetime


def parse_datetime(datetime_str):
    # Try different formats to parse the datetime string
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"Time data '{datetime_str}' does not match any expected format")

@frappe.whitelist(allow_guest= True)
def get_sales_order_by_branch(start_datetime, end_datetime,_order_by,branch=None, kds_station=None):
    from datetime import datetime, timedelta
    end_datetime = datetime.now()
    start_datetime = end_datetime - timedelta(days=1)
    start_date_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S')

    filters={'docstatus': 0,'cancelled_from_app': 0,'creation': ['between', (start_date_str, end_date_str)]}
    if branch:
        filters['branch'] = branch

    sales_orders = frappe.get_all('Sales Order',
                                 filters= filters,
                                  fields=['name'],
                                  order_by='creation '+_order_by)

    sales_orders_data = []

    for so in sales_orders:
        sales_order = frappe.get_doc("Sales Order", so.name)
        sales_order_data = sales_order.as_dict()
        sales_order_data["items"] = [] 

        for item in sales_order.items:
            item_dict = item.as_dict()

            if not item.is_stock_item:
                product_bundle = frappe.get_all('Product Bundle', filters={'new_item_code': item.item_code}, fields=['name'])

                if product_bundle:
                    bundle_name = product_bundle[0].name
                    item_specifics = frappe.get_all('Item Specifics Child', filters={'parent': bundle_name}, fields=['item_specifics_name'])
                    
                    item_specifics_list = [child.item_specifics_name for child in item_specifics]

                    item_dict['item_specifics'] = item_specifics_list

            sales_order_data["items"].append(item_dict)
        sales_orders_data.append(sales_order_data)

    return sales_orders_data  

@frappe.whitelist()
def get_sales_order(start_datetime, end_datetime,_order_by):
    if isinstance(start_datetime, str):
        start_datetime = parse_datetime(start_datetime)
    if isinstance(end_datetime, str):
        end_datetime = parse_datetime(end_datetime)
    
    start_date_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S')

    sales_orders = frappe.get_all('Sales Order',
                                  filters={'docstatus': 0,'cancelled_from_app': 0,'creation': ['between', (start_date_str, end_date_str)]},
                                  fields=['name'],
                                  order_by='creation '+_order_by)

    sales_orders_data = []

    for so in sales_orders:
        sales_order = frappe.get_doc("Sales Order", so.name)
        sales_order_data = sales_order.as_dict()
        sales_orders_data.append(sales_order_data)

    return sales_orders_data   

@frappe.whitelist()
def get_pos_profile_and_branch(user_id, is_multiple_pos_profiles):
    # Debugging output to check the type and value of is_multiple_pos_profiles
    print(f"Received is_multiple_pos_profiles: {is_multiple_pos_profiles} (type: {type(is_multiple_pos_profiles)})")

    # Step 1: Get the POS Profile for the user
    user_pos_profile = frappe.get_all(
        'POS Profile User',
        filters={'user': user_id},
        fields=['parent']
    )

    if not user_pos_profile:
        return {"error": "No POS Profile found for the user."}

    pos_profile_name = user_pos_profile[0].parent

    # Fetch the full POS Profile document
    pos_profile_doc = frappe.get_doc('POS Profile', pos_profile_name)

    # Step 2: Find the corresponding branch based on the POS Profile
    branch = None  # Initialize branch variable

    if is_multiple_pos_profiles == "1":
        # Multiple profiles, check in Branch POS Profiles
        branch_data = frappe.get_all(
            'Branch POS Profiles',
            filters={'pos_profile': pos_profile_name},
            fields=['parent'],
            limit=1  # Get only one branch
        )
        if branch_data:
            branch_name = branch_data[0].parent
            # Fetch the full Branch document
            branch_doc = frappe.get_doc('Branch', branch_name)
        else:
            branch_doc = None
    elif is_multiple_pos_profiles == "0":
        print("Single profile detected.")
        # Single profile, direct link
        branch_data = frappe.get_all(
            'Branch',
            filters={'pos_profile': pos_profile_name},
            fields=['name'],
            limit=1  # Get only one branch
        )
        if branch_data:
            branch_name = branch_data[0].name
            # Fetch the full Branch document
            branch_doc = frappe.get_doc('Branch', branch_name)
        else:
            branch_doc = None
    else:
        return {"error": "Invalid value for is_multiple_pos_profiles."}

    # Return the full pos_profile_doc and branch_doc
    return {
        'pos_profile': pos_profile_doc,
        'branch': branch_doc if branch_doc else "No branch found"
    }

