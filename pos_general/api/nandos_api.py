import frappe
from erpnext.stock.get_item_details import get_conversion_factor, get_item_price
@frappe.whitelist()
def get_item_details_with_variants_and_add_ons(item):
    item_with_detail = frappe._dict({"variants": [],"item_add_on_doc": [], "doctype": {}})
    item_doc = frappe.get_doc("Item", item)

    item_with_detail.doctype = item_doc.as_dict()
    currency = frappe.get_doc("Company",item_doc.item_defaults[0].company)
    item_with_detail.doctype["currency"] = currency.default_currency

    if item_doc.has_variants == 1:
        for attrib in item_doc.attributes:
            variant = frappe._dict({"Attribute": attrib, "Values": []})
            item_var = frappe.get_all("Item",filters={"variant_of":item_doc.name})
            for i in item_var:
                variants_doc = frappe.get_doc("Item",i.name)
                args_for_get_price_list = {
                "price_list": "Standard Selling",
                "item_code": variants_doc.name,
                "uom": variants_doc.stock_uom
                }
                price_rate = get_item_price(args_for_get_price_list, variants_doc.name)
                # print("price_rate : ", price_rate[0][1])

                variants_doc_dict = variants_doc.as_dict()
                variants_doc_dict["rate"] = price_rate[0][1] if price_rate else 0
                variant.Values.append(variants_doc_dict)
                
            item_with_detail.variants.append(variant)

    # Fetch the list of item add-ons for the given item, ordered by creation date in ascending order
    item_add_ons_list = frappe.get_list("Item Add-Ons", filters={"item": item}, fields=["*"], order_by="creation asc")

    # Initialize a list to hold the detailed add-on information
    item_with_detail.item_add_on_doc = []

    # Iterate through each item add-on in the list
    for item_add_on in item_add_ons_list:
        # Fetch the detailed document for the current item add-on
        doc_add_on = frappe.get_doc("Item Add-Ons", item_add_on.name)
        
        # Convert the document to a dictionary
        add_on_details = doc_add_on.as_dict()
        
        # Iterate through each item in the item add-ons list
        for add_on in add_on_details['item_add_ons']:
            # Fetch the item document for the current add-on
            item_doc = frappe.get_doc("Item", add_on['item'])
            
            # Check if the item has variants
            if item_doc.has_variants == 1:
                # Initialize the variants list within the specific add-on template dictionary
                add_on['variants'] = []

                # Fetch all variants of the current item
                variants = frappe.get_all("Item", filters={"variant_of": item_doc.name})
                
                # Iterate through each variant
                for variant in variants:
                    # Fetch the detailed document for the current variant
                    variant_doc = frappe.get_doc("Item", variant.name)
                    
                    # Append the variant details to the variants list in the specific add-on template dictionary
                    add_on['variants'].append(variant_doc.as_dict())

        # Append the detailed add-on information (including variants) to the item_with_detail object
        item_with_detail.item_add_on_doc.append(add_on_details)

    return item_with_detail



@frappe.whitelist()
def get_item_with_variant_and_rate(item_group):
    item_detail = []
    item_docs_list = frappe.get_all("Item", filters={"item_group": item_group, "has_variants": 1})

    for item in item_docs_list:
        item_template_data = frappe.get_doc("Item", item.name)

        template = {
            "item_code": item_template_data.get("item_code"),
            "item_name": item_template_data.get("item_name"),
            "description": item_template_data.get("description"),
            "image": item_template_data.get("image"),
            "variants": []
        }

        # Get all variants of the current item
        item_variants = frappe.get_all("Item", filters={"variant_of": item.name})

        for variant in item_variants:
            # Get the variant details
            variant_data = frappe.get_doc("Item", variant.name)

            # Get the price rate for the variant
            args_for_get_price_list = {
                "price_list": "Standard Selling",
                "item_code": variant_data.name,
                "uom": variant_data.stock_uom
            }
            price_rate = get_item_price(args_for_get_price_list, variant_data.name)

            # Create the variant dictionary with the desired fields
            variant_dict = {
                "item_code": variant_data.get("item_code"),
                "item_name": variant_data.get("item_name"),
                "description": variant_data.get("description"),
                "rate": price_rate[0][1] if price_rate else 0,
                "image": variant_data.get("image")
            }

            # Append the variant dictionary to the variants list in the template
            template["variants"].append(variant_dict)

        # Append the template dictionary to the item_detail
        item_detail.append({"template": template})

    return item_detail


@frappe.whitelist()
def get_deals():
    deal_dict = []
    deals_list = frappe.get_all("Item", filters={"item_group": "Deals"})
    
    if deals_list:
        for deal in deals_list:
            deal_doc = frappe.get_doc("Item", deal.name)
            
            args_for_get_price_list = {
                "price_list": "Standard Selling",
                "item_code": deal_doc.name,
                "uom": deal_doc.stock_uom,
            }
            price_rate = get_item_price(args_for_get_price_list, deal_doc.name)
            price = price_rate[0][1] if price_rate else 0

            currency = frappe.get_doc("Company",deal_doc.item_defaults[0].company)
            
            temp = {
                "deal_item": deal_doc,
                "deal_price": price,
                "default_currency": currency.default_currency,
                "bundle": []
            }
            
            bundle_doc = frappe.get_doc("Product Bundle", deal.name)
            for bundle_item in bundle_doc.items:
                item = frappe.get_doc("Item", bundle_item.item_code)
                item_dict = item.as_dict()
                if item_dict.get("has_variants") == 1:
                    variants_ls =[]
                    variants_list = frappe.get_all("Item", filters={"variant_of": item.name})
                    for var in variants_list:
                        v = frappe.get_doc("Item",var.name)
                        variants_ls.append(v)
                    item_dict["variants"] = variants_ls
                temp["bundle"].append(item_dict)
            deal_dict.append(temp)
            
    return deal_dict




# @frappe.whitelist()
# def create_sales_order():
#     try:
#         data = frappe.request.get_data().decode("utf-8")
#         json_data = frappe.parse_json(data)
#     except ValueError:
#         frappe.response["http_status_code"] = 400
#         return {"error": "Invalid JSON data"}

#     if not json_data:
#         frappe.response["http_status_code"] = 400
#         return {"error": "Missing required field: items"}
    
#     for items_list in json_data["items"]:
#         print("items list : ",items_list)
#         if len(items_list) == 1:
#             continue
#         existing_bundle_found = False
#         for item in items_list:

#             print("item : ",item)
#             item_code = item["item_code"]
#             # item_group = item["item_group"]
#             # qty = item["qty"]
#             # rate = item["rate"]
            
#             bundle_list = frappe.get_list("Product Bundle")
#             for bundle_name in bundle_list:

#                 print("bundle_name : ", bundle_name)

#                 bundle_doc = frappe.get_doc("Product Bundle", bundle_name)
#                 if len(bundle_doc.items) == len(items_list):
#                     all_items_matched = True
#                     for bundle_item in bundle_doc.items:
#                         if not any(bundle_item.item_code == item["item_code"] for item in items_list):
#                         # if not any(bundle_item.item_code == item["item_code"] and
#                         #            bundle_item.item_group == item["item_group"] and
#                         #            bundle_item.qty == item["qty"] and
#                         #            bundle_item.rate == item["rate"] for item in items_list):
#                             all_items_matched = False
#                             break
#                     if all_items_matched:
#                         existing_bundle_found = True
#                         break
            
#             if existing_bundle_found:
#                 print("found the bundle")
#                 break
        
#         if not existing_bundle_found:
#             # creating service item for creating bundle
#             first_item_code = items_list[0]["item_code"]
#             service_item_doc = frappe.new_doc("Item")
#             service_item_doc.item_code = first_item_code
#             service_item_doc.item_name = first_item_code
#             # service_item_doc.item_group = items_list[0]["item_group"]
#             service_item_doc.item_group = "Service Item"
#             service_item_doc.is_stock_item = 0
#             service_item_doc.save()

#             # Use the newly created service item as the new_item_code in the Product Bundle
#             new_bundle = frappe.new_doc("Product Bundle")
#             new_bundle.new_item_code = service_item_doc.name
#             for item_data in items_list:
#                 new_item = new_bundle.append("items", {})
#                 new_item.item_code = item_data["item_code"]
#                 new_item.description = item_data["item_code"]
#                 new_item.qty = 1
#             new_bundle.save()


@frappe.whitelist()
def create_sales_order():
    try:
        data = frappe.request.get_data().decode("utf-8")
        json_data = frappe.parse_json(data)
    except ValueError:
        frappe.response["http_status_code"] = 400
        return {"error": "Invalid JSON data"}

    if not json_data:
        frappe.response["http_status_code"] = 400
        return {"error": "Missing required field: items"}

    items_to_add = []
    for items_list in json_data["items"]:
        if len(items_list) == 1:
            item_data = items_list[0]
            item_code = item_data["item_code"]
            item_qty = item_data["qty"]
            rate = item_data["rate"]
            items_to_add.append({"item_code": item_code, "qty": item_qty,"rate":rate})
            continue
        
        existing_bundle_found = False
        for item in items_list:
            item_code = item["item_code"]
            bundle_list = frappe.get_list("Product Bundle")
            for bundle_name in bundle_list:
                bundle_doc = frappe.get_doc("Product Bundle", bundle_name)
                if len(bundle_doc.items) == len(items_list):
                    all_items_matched = True
                    for bundle_item in bundle_doc.items:
                        if not any(bundle_item.item_code == item["item_code"] for item in items_list):
                            all_items_matched = False
                            break
                    if all_items_matched:
                        existing_bundle_found = True
                        break
            
            if existing_bundle_found:
                # Add the bundle to items_to_add
                total_rate = sum(item_data["rate"] for item_data in items_list)
                items_to_add.append({"item_code": bundle_doc.name, "qty": items_list[0]["qty"], "rate": total_rate})
                break
        
        if not existing_bundle_found:
            # creating service item for creating bundle
            first_item_code = items_list[0]["item_code"]
            service_item_doc = frappe.new_doc("Item")
            service_item_doc.item_code = first_item_code
            service_item_doc.item_name = first_item_code
            service_item_doc.item_group = "Service Item"
            service_item_doc.is_stock_item = 0
            service_item_doc.save()

            # Use the newly created service item as the new_item_code in the Product Bundle
            new_bundle = frappe.new_doc("Product Bundle")
            new_bundle.new_item_code = service_item_doc.name
            for item_data in items_list:
                new_item = new_bundle.append("items", {})
                new_item.item_code = item_data["item_code"]
                new_item.description = item_data["item_code"]
                new_item.qty = 1
            new_bundle.save()

            # Add the newly created bundle to items_to_add
            total_rate = sum(item_data["rate"] for item_data in items_list)
            items_to_add.append({"item_code": new_bundle.name, "qty": items_list[0]["qty"], "rate": total_rate})

    # Create the sales order
    if json_data["sales_order"]:
        so = frappe.get_doc("Sales Order",json_data["sales_order"])
        if so.docstatus == 1: 
            return {"error": "Sales Order already submitted. Can't change submitted Sales Order"}
        else:
            so.set("items", [])
            for item_data in items_to_add:
                sales_order_item_row = so.append("items", {})
                sales_order_item_row.item_code = item_data["item_code"]
                sales_order_item_row.qty = item_data["qty"]
                sales_order_item_row.rate = item_data["rate"]
                sales_order_item_row.delivery_date = json_data.get("delivery_date", "")
            so.save()
            # frappe.db.set_value("Sales Order", json_data["sales_order"], "items", items_to_add)
    else:
        try:
            sales_order = frappe.new_doc("Sales Order")
            sales_order.customer = json_data.get("customer","")
            sales_order.table_no = json_data.get("table_no", "")
            sales_order.delivery_date = json_data.get("delivery_date", "")
            sales_order.cost_center = json_data.get("cost_center", "")
            for item_data in items_to_add:
                sales_order_item_row = sales_order.append("items", {})
                sales_order_item_row.item_code = item_data["item_code"]
                sales_order_item_row.qty = item_data["qty"]
                sales_order_item_row.rate = item_data["rate"]
                sales_order_item_row.delivery_date = json_data.get("delivery_date", "")
            sales_order.save()
        except:
            return {"error": "invalid JSON data"}
        

@frappe.whitelist()
def create_bundle_from_item(json_data):
    try:
        # Parse the incoming JSON data
        data = frappe.parse_json(json_data)
        
        # Extract the list of items
        bundles_data = data.get("items", [])
        
        if not bundles_data:
            frappe.response["http_status_code"] = 400
            return {"error": "Missing required field: items"}
        
        created_bundles = []
        
        for bundle_data in bundles_data:
            with_meal = bundle_data.get("with_meal", False)
            meal_price = bundle_data.get("meal_price", 0)
            items_list = bundle_data.get("items", [])
            item_specifics = bundle_data.get("item_specifics", [])
            
            if not items_list:
                frappe.response["http_status_code"] = 400
                return {"error": "Missing required field: items in one of the bundles"}
            
            items_to_add = []
            existing_bundle_found = False
            
            # Check for existing bundles that match the items list and item specifics
            bundle_list = frappe.get_list("Product Bundle")
            
            for bundle_name in bundle_list:
                bundle_doc = frappe.get_doc("Product Bundle", bundle_name)
                
                if len(bundle_doc.items) == len(items_list):
                    all_items_matched = True
                    
                    for bundle_item in bundle_doc.items:
                        if not any(bundle_item.item_code == item_data["item_code"] for item_data in items_list):
                            all_items_matched = False
                            break
                    
                    if all_items_matched:
                        # Check if item specifics match exactly
                        bundle_specifics = bundle_doc.get("item_specifics") or []
                        if len(bundle_specifics) == len(item_specifics):
                            all_specifics_matched = True
                            
                            for i in range(len(bundle_specifics)):
                                if bundle_specifics[i].name != item_specifics[i]["name"]:
                                    all_specifics_matched = False
                                    break
                            
                            if all_specifics_matched:
                                existing_bundle_found = True
                                break
            
            if existing_bundle_found:
                # Add the existing bundle to items_to_add
                total_rate = sum(item_data["rate"] for item_data in items_list)
                items_to_add.append({"item_code": bundle_doc.name, "qty": items_list[0]["qty"], "rate": total_rate})
            else:
                # Determine max cooking_time and if any item is marked as is_kds
                max_cooking_time = 0
                any_item_is_kds = False
                
                for item_data in items_list:
                    item_doc = frappe.get_doc("Item", item_data["item_code"])
                    if item_doc.is_kds_item:
                        any_item_is_kds = True
                        if item_doc.cooking_time > max_cooking_time:
                            max_cooking_time = item_doc.cooking_time
                
                # Create a new service item for the bundle
                first_item_code = items_list[0]["item_code"]
                
                if not first_item_code:
                    frappe.response["http_status_code"] = 400
                    return {"error": "Missing item_code in one of the bundles"}
                
                service_item_doc = frappe.new_doc("Item")
                service_item_doc.item_code = first_item_code
                service_item_doc.item_name = first_item_code
                service_item_doc.item_group = "Service Item"
                service_item_doc.is_stock_item = 0
                
                # Set cooking_time and is_kds for the service item
                service_item_doc.cooking_time = max_cooking_time
                service_item_doc.is_kds_item = any_item_is_kds
                
                service_item_doc.save()
                frappe.db.commit()  # Optional: commit changes to the database

                # Create a new product bundle using the service item
                new_bundle = frappe.new_doc("Product Bundle")
                new_bundle.new_item_code = service_item_doc.name
                
                for item_data in items_list:
                    new_item = new_bundle.append("items", {})
                    new_item.item_code = item_data["item_code"]
                    new_item.description = item_data["item_code"]
                    new_item.qty = item_data["qty"]
                
                # Add item specifics to the new product bundle if available
                for specific in item_specifics:
                    new_specific = new_bundle.append("item_specifics", {})
                    new_specific.item_specifics_name = specific["name"]
                new_bundle.meal_price = meal_price
                new_bundle.with_meal = with_meal
                new_bundle.save()
                frappe.db.commit()

                # Add the newly created bundle to items_to_add
                total_rate = sum(item_data["rate"] for item_data in items_list)
                items_to_add.append({"item_code": new_bundle.name, "qty": items_list[0]["qty"], "rate": total_rate})
            
            created_bundles.append(items_to_add)
        
        # Output the list of created bundles
        print("created_bundles:", created_bundles)
        return created_bundles

    except ValueError:
        # Return a 400 error if JSON data is invalid
        frappe.response["http_status_code"] = 400
        return {"error": "Invalid JSON data"}


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