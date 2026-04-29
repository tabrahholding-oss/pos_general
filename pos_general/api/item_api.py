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
def get_item_with_variant_and_rate_multi_group():
    try:
        # Parse JSON data from request
        data = frappe.request.get_data().decode("utf-8")
        json_data = frappe.parse_json(data)
    except ValueError:
        frappe.response["http_status_code"] = 400
        return {"error": "Invalid JSON data"}

    item_groups = json_data.get("item_groups", [])
    if not item_groups:
        return {"error": "No item groups provided"}

    item_group_dict = {}

    for item_group in item_groups:
        item_details_without_variant = []
        item_detail = []
        print(item_group)
        try:
            # Fetch items with variants
            item_docs_list = frappe.get_all("Item", filters={"item_group": item_group, "has_variants": 1})
            # Fetch items without variants
            items_list_without_variant = frappe.get_all("Item", filters={"item_group": item_group, "has_variants": 0, "variant_of": "", "disabled": 0, "is_sales_item": 1})

            # Process items without variants
            for items in items_list_without_variant:
                item_data = frappe.get_doc("Item", items.name)
                item_price_list = frappe.get_all("Item Price", filters={"item_code": item_data.item_code}, fields=[
                    "item_code", "item_name", "price_list", "price_list_rate"
                ])

                for item_price in item_price_list:
                    price_list = frappe.get_all("Price List", filters={"selling": 1, "name": item_price.price_list}, fields=[
                        "name", "price_list_name", "selling", "order_type"
                    ])
                    item_price['order_type'] = price_list[0].order_type if price_list else None

                variant_dict_without_variant = {
                    "item_code": item_data.get("item_code"),
                    "item_name": item_data.get("item_name"),
                    "description": item_data.get("description"),
                    "rate": item_price_list,
                    "image": item_data.get("image"),
                    "kds_" : item_data.get("kds_"),
                    "order_type": item_data.get("order_type")
                }
                item_details_without_variant.append({"Item": variant_dict_without_variant})

            # Process items with variants
            for item in item_docs_list:
                item_template_data = frappe.get_doc("Item", item.name)
                template = {
                    "item_code": item_template_data.get("item_code"),
                    "item_name": item_template_data.get("item_name"),
                    "description": item_template_data.get("description"),
                    "image": item_template_data.get("image"),
                    "kds_" : item_data.get("kds_"),
                    "order_type": item_template_data.get("order_type"),
                    "variants": []
                }

                # Get all variants of the current item
                item_variants = frappe.get_all("Item", filters={"variant_of": item.name})
                for variant in item_variants:
                    variant_data = frappe.get_doc("Item", variant.name)
                    item_price_list = frappe.get_all("Item Price", filters={"item_code": variant_data.item_code}, fields=[
                        "item_code", "item_name", "price_list", "price_list_rate"
                    ])

                    for item_price in item_price_list:
                        price_list = frappe.get_all("Price List", filters={"selling": 1, "name": item_price.price_list}, fields=[
                            "name", "price_list_name", "selling", "order_type"
                        ])
                        item_price['order_type'] = price_list[0].order_type if price_list else None

                    variant_dict = {
                        "item_code": variant_data.get("item_code"),
                        "item_name": variant_data.get("item_name"),
                        "description": variant_data.get("description"),
                        "rate": item_price_list,
                        "kds_" : item_data.get("kds_"),
                        "image": variant_data.get("image")
                    }
                    template["variants"].append(variant_dict)

                item_detail.append({"template": template})

            # Store results for the current item group in the dictionary
            item_group_dict[item_group] = item_detail + item_details_without_variant

        except Exception as e:
            print(f"Error processing item group '{item_group}': {str(e)}")
            item_group_dict[item_group] = {"error": str(e)}

    # Print the dictionary to verify the structure (for debugging)
    for group_name, results in item_group_dict.items():
        print(f"Item Group: {group_name}")
        for item in results:
            print(item)

    return item_group_dict





@frappe.whitelist()
def get_item_with_variant_and_rate(item_group):
    item_details_without_variant = []
    item_detail = []
    item_docs_list = frappe.get_all("Item", filters={"item_group": item_group, "has_variants": 1})
    items_list_without_varient = frappe.get_all("Item", filters={"item_group": item_group, "has_variants": 0, "variant_of":"", "disabled": 0, "is_sales_item": 1})
    
    # Function to get attachments for an item
    def get_attachments(item_name):
        files = frappe.get_all("File", filters={"attached_to_doctype": "Item", "attached_to_name": item_name}, fields=["file_url", "file_name"])
        return [{"file_name": file.file_name, "file_url": file.file_url} for file in files]
    
    for items in items_list_without_varient:
        item_data = frappe.get_doc("Item", items.name)
        
        item_price_list = frappe.get_all("Item Price", filters={"item_code": item_data.item_code}, fields=[
            "item_code",
            "item_name",
            "price_list",
            "price_list_rate",
        ])
        for item_price in item_price_list:
            price_list = frappe.get_all("Price List", filters={"selling": 1, "name": item_price.price_list}, fields=[
            "name",
            "price_list_name",
            "selling",
            "order_type",
        ])
            if price_list:
                item_price['order_type'] = price_list[0].order_type  
            else:
                item_price['order_type'] = None  
        
        variant_dict_without_varient = {
                "item_code": item_data.get("item_code"),
                "item_name": item_data.get("item_name"),
                "description": item_data.get("description"),
                "rate": item_price_list,
                "image": item_data.get("image"),
                "order_type": item_data.get("order_type"),
                "attachments": get_attachments(item_data.name)  # Add attachments here
            }
        item_details_without_variant.append({"Item": variant_dict_without_varient})
    
    for item in item_docs_list:
        item_template_data = frappe.get_doc("Item", item.name)
        
        template = {
            "item_code": item_template_data.get("item_code"),
            "item_name": item_template_data.get("item_name"),
            "description": item_template_data.get("description"),
            "image": item_template_data.get("image"),
            "order_type": item_template_data.get("order_type"),
            "variants": [],
            "attachments": get_attachments(item_template_data.name)  # Add attachments here
        }

        item_variants = frappe.get_all("Item", filters={"variant_of": item.name})

        for variant in item_variants:
            variant_data = frappe.get_doc("Item", variant.name)
            item_price_list = frappe.get_all("Item Price", filters={"item_code": variant_data.item_code}, fields=[
            "item_code",
            "item_name",
            "price_list",
            "price_list_rate",
            ])
            for item_price in item_price_list:
                price_list = frappe.get_all("Price List", filters={"selling": 1, "name": item_price.price_list}, fields=[
                "name",
                "price_list_name",
                "selling",
                "order_type",
            ])
            if price_list:
                item_price['order_type'] = price_list[0].order_type  
            else:
                item_price['order_type'] = None  

            variant_dict = {
                "item_code": variant_data.get("item_code"),
                "item_name": variant_data.get("item_name"),
                "description": variant_data.get("description"),
                "rate": item_price_list,
                "image": variant_data.get("image"),
                "attachments": get_attachments(variant_data.name)  # Add attachments here
            }

            template["variants"].append(variant_dict)

        item_detail.append({"template": template})
       
    combined_results = item_detail + item_details_without_variant
    
    sorted_results = sorted(combined_results, key=lambda x: list(x.values())[0]['item_name'])

    return sorted_results



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
def get_variants_addons(item_code, order_type=None):
    
    Attributes = []
    variants = []
    item_add_on_doc = []

    def get_price_list(order_type):
        price_list_data = frappe.db.sql(
            """
            SELECT name
            FROM `tabPrice List`
            WHERE order_type = %s
            LIMIT 1
            """, (order_type), as_dict=True
        )
        if price_list_data:
            return price_list_data[0].name
        else:
            return None
        
    
    price_list = get_price_list(order_type) or "Standard Selling"
    try:
        # Fetch the main item document
        item_doc = frappe.get_doc("Item", item_code)
        attributes = get_item_attributes(item_doc.item_code)
        Attributes.append(attributes)
        if item_doc.has_variants == 1:
            try:
                # Fetch all item variants
                item_variants = frappe.get_all("Item", filters={"variant_of": item_doc.name})

                for variant_item in item_variants:
                    try:
                        # Fetch the variant document
                        variant_doc = frappe.get_doc("Item", variant_item.name)

                        # Prepare arguments to get the price list
                        args_for_get_price_list = {
                            "price_list": price_list,
                            "item_code": variant_doc.name,
                            "uom": variant_doc.stock_uom
                        }

                        # Fetch the price rate
                        price_rate = get_item_price(args_for_get_price_list, variant_doc.name)
                        variant_doc_dict = variant_doc.as_dict()
                        variant_doc_dict["rate"] = price_rate[0][1] if price_rate else 0

                        # Append the variant document to the list of variants
                        variants.append(variant_doc_dict)

                    except Exception as e:
                        print(f"Error fetching variant document or price: {e}")

            except Exception as e:
                print(f"Error fetching item variants: {e}")

    except Exception as e:
        print(f"Error fetching item document: {e}")

    # Fetch add-ons for the item with enhanced security and error handling
    try:
        # Fetch the list of item add-ons
        item_add_ons_list = frappe.get_list("Item Add-Ons", filters={"item": item_code}, fields=["*"], order_by="creation asc")

        for item_add_on in item_add_ons_list:
            try:
                # Fetch the document for each item add-on
                doc_add_on = frappe.get_doc("Item Add-Ons", item_add_on.name)
                add_on_details = doc_add_on.as_dict()

                # Process each add-on within the item add-on document
                for add_on in add_on_details.get('item_add_ons', []):
                    try:
                        add_on_item_doc = frappe.get_doc("Item", add_on['item'])

                        if add_on_item_doc.has_variants == 1:
                            add_on['variants'] = []
                            add_on_variants = frappe.get_all("Item", filters={"variant_of": add_on_item_doc.name})

                            for variant in add_on_variants:
                                try:
                                    variant_doc = frappe.get_doc("Item", variant.name)
                                    add_on['variants'].append(variant_doc.as_dict())
                                except Exception as e:
                                    print(f"Error fetching variant document: {e}")
                    except Exception as e:
                        print(f"Error fetching item document: {e}")

                item_add_on_doc.append(add_on_details)
            except Exception as e:
                print(f"Error fetching item add-on document: {e}")

    except Exception as e:
        print(f"Error fetching item add-ons list: {e}")

    # Prepare the final result
    result = []
    result.append({
        "Attributes":Attributes,
        "variants": variants,
        "add_ons": item_add_on_doc,
    })

    return result        


@frappe.whitelist()
def get_item_attributes(item_code):
    # Get all attributes for the given item
    attributes = frappe.db.get_all(
        "Item Variant Attribute",
        fields=["attribute","attribute_value",""],
        filters={"parenttype": "Item", "variant_of": item_code},
        order_by="idx asc",
    )
    organized_attributes = {}

    # Iterate through each attribute dictionary
    for attr in attributes:
        attribute_name = attr['attribute']
        attribute_value = attr['attribute_value']

        # Check if attribute name already exists in organized_attributes
        if attribute_name in organized_attributes:
            # Check if attribute_value already exists in values list
            if not any(v['attribute_value'] == attribute_value for v in organized_attributes[attribute_name]['values']):
                organized_attributes[attribute_name]['values'].append({'attribute_value': attribute_value, 'abbr': attribute_value})
        else:
            organized_attributes[attribute_name] = {
                'attribute': attribute_name,
                'values': [{'attribute_value': attribute_value, 'abbr': attribute_value}]
            }

    # Convert the dictionary to a list of dictionaries (desired format)
    desired_format = list(organized_attributes.values())

    # Print the result
    print(desired_format)
    return desired_format
