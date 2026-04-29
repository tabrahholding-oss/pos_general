# Copyright (c) 2024, Hussain and contributors
# For license information, please see license.txt
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_data(filters):
    data = []
    
    if not filters or not filters.get('from_date') or not filters.get('to_date'):
        return data

    from_date = filters.get('from_date')
    to_date = filters.get('to_date')
    status = filters.get('status', 'Paid')
    branch = filters.get('name')  # Branch filter
    posa_pos_opening_shift = filters.get("posa_pos_opening_shift")

    restaurant_types_query = """
        SELECT DISTINCT resturent_type
        FROM `tabSales Invoice` as si 
        WHERE si.posting_date >= %(from_date)s
          AND si.posting_date <= %(to_date)s
          AND si.status = %(status)s
    """
    
    # Include branch filter if provided
    if branch:
        restaurant_types_query += " AND si.pos_profile = %(branch)s"
    
    # Include posa_pos_opening_shift filter if provided
    if posa_pos_opening_shift:
        restaurant_types_query += " AND si.posa_pos_opening_shift = %(posa_pos_opening_shift)s"

    restaurant_types_query += " ORDER BY resturent_type ASC"
    
    # Execute the query
    restaurant_types = frappe.db.sql(restaurant_types_query, {
        'from_date': from_date,
        'to_date': to_date,
        'status': status,
        'branch': branch,
        'posa_pos_opening_shift': posa_pos_opening_shift,
    }, as_dict=True)
    
    for restaurant_type in restaurant_types:
        rest_type = restaurant_type.get('resturent_type')
        
        restaurant_totals = {
            "gross_sales": 0.0,
            "discount_amount": 0.0,
            "sub_total": 0.0,
            "tax_cash": 0.0,
            "tax_credit": 0.0,
            "cash_sale": 0.0,
            "credit_sale": 0.0,
            "grand_total": 0.0,
            "cash_without_tax": 0.0,
            "credit_without_tax": 0.0,
            "sales_without_tax" : 0.0
        }
        
        # Conditional query for sales invoices
        sales_invoices_query = """
            SELECT 
                si.name, 
                si.resturent_type, 
                si.posting_date, 
                si.total, 
                si.grand_total, 
                si.discount_amount, 
                si.total_taxes_and_charges 
            FROM 
                `tabSales Invoice` AS si
            WHERE 
                si.posting_date >= %(from_date)s
                AND si.posting_date <= %(to_date)s
                AND si.status = %(status)s
                AND si.resturent_type = %(rest_type)s
        """
        
        # Include branch filter if provided
        if branch:
            sales_invoices_query += " AND si.pos_profile = %(branch)s"
        
        # Include posa_pos_opening_shift filter if provided
        if posa_pos_opening_shift:
            sales_invoices_query += " AND si.posa_pos_opening_shift = %(posa_pos_opening_shift)s"
        
        sales_invoices_query += " ORDER BY resturent_type ASC"
        
        # Execute the query
        sales_invoices = frappe.db.sql(sales_invoices_query, {
            'from_date': from_date,
            'to_date': to_date,
            'status': status,
            'rest_type': rest_type,
            'branch': branch,
            'posa_pos_opening_shift': posa_pos_opening_shift,
        }, as_dict=True)

        for invoice in sales_invoices:
            repost_doc = frappe.get_doc("Sales Invoice", invoice.name)
            tax_amount_by_cash = 0.0
            tax_amount_by_credit = 0.0
            pay_amount_by_cash = 0.0
            pay_amount_by_credit = 0.0
            cash_without_tax = 0.0
            credit_without_tax = 0.0
            sales_without_tax = 0.0
            
            # Loop through the payments to calculate cash and credit tax
            for pay in repost_doc.payments:
                if pay.get("type") == "Cash":
                    pay_amount_by_cash += pay.get("amount", 0)
                    cash_without_tax += invoice.total # Corrected calculation
                    tax_amount_by_cash += invoice.total_taxes_and_charges  # Tax on cash sales
                elif pay.get("type") == "Bank":
                    pay_amount_by_credit += pay.get("amount", 0)
                    credit_without_tax += invoice.total  # Corrected calculation
                    tax_amount_by_credit += invoice.total_taxes_and_charges
            
            total = float(invoice.get("total", 0))
            discount_amount = float(invoice.get("discount_amount", 0))
            grand_total = float(invoice.get("grand_total", 0))
            
            # Add invoice amounts to restaurant totals
            restaurant_totals["gross_sales"] += grand_total
            restaurant_totals["discount_amount"] += discount_amount
            restaurant_totals["sub_total"] += total
            restaurant_totals["tax_cash"] += tax_amount_by_cash  
            restaurant_totals["tax_credit"] += tax_amount_by_credit  
            restaurant_totals["cash_sale"] += pay_amount_by_cash
            restaurant_totals["credit_sale"] += pay_amount_by_credit
            restaurant_totals["cash_without_tax"] += cash_without_tax
            restaurant_totals["credit_without_tax"] += credit_without_tax
            # update grand Total  = cash sale + credit sale 
            restaurant_totals["grand_total"] = (restaurant_totals["cash_sale"] + restaurant_totals["credit_sale"])
            restaurant_totals["sales_without_tax"] = (restaurant_totals["cash_without_tax"] + restaurant_totals["credit_without_tax"]
    )
        
        # Append only the group summary to data
        data.append({
            "date": rest_type,
            "total": round(restaurant_totals["gross_sales"], 2),
            "discount_amount": round(restaurant_totals["discount_amount"], 2),
            "sub_total": round(restaurant_totals["sub_total"], 2),
            "tax_cash": round(restaurant_totals["tax_cash"], 2),
            "tax_credit": round(restaurant_totals["tax_credit"], 2),
            "cash_without_tax": round(restaurant_totals["cash_without_tax"], 2),
            "credit_without_tax": round(restaurant_totals["credit_without_tax"], 2),
            "cash_sale": round(restaurant_totals["cash_sale"], 2),
            "credit_sale": round(restaurant_totals["credit_sale"], 2),
            "grand_total": round(restaurant_totals["grand_total"], 2),
            "sales_without_tax": round(restaurant_totals["sales_without_tax"], 2),
        })
    
    return data


def get_columns(filters):
    columns = [
        {"label": _("Restaurant"), "fieldname": "date", "fieldtype": "Data", "width": 200},
        {"label": _("Gross Sales"), "fieldname": "total", "fieldtype": "Data", "width": 200},  
        {"label": _("Discount"), "fieldname": "discount_amount", "fieldtype": "Data", "width": 200},
        {"label": _("Sub Total"), "fieldname": "sub_total", "fieldtype": "Data", "width": 200},
        {"label": _("Tax (Cash)"), "fieldname": "tax_cash", "fieldtype": "Data", "width": 200},
        {"label": _("Tax (Credit)"), "fieldname": "tax_credit", "fieldtype": "Data", "width": 200},
        {"label": _("Cash sales without tax"), "fieldname": "cash_without_tax", "fieldtype": "Data", "width": 200},
        {"label": _("Credit sales without tax"), "fieldname": "credit_without_tax", "fieldtype": "Data", "width": 200},
        {"label": _("sales without tax"), "fieldname": "sales_without_tax", "fieldtype": "Data", "width": 200},
        {"label": _("Cash Sales"), "fieldname": "cash_sale", "fieldtype": "Data", "width": 200},
        {"label": _("Credit Sales"), "fieldname": "credit_sale", "fieldtype": "Data", "width": 200},
        {"label": _("Total Sales"), "fieldname": "grand_total", "fieldtype": "Data", "width": 200},
    ]
    return columns





@frappe.whitelist()
def get_user_branches():
    current_user = frappe.session.user
    if current_user == "Administrator":
        get_branches_query = """
            SELECT ppu.parent 
            FROM `tabPOS Profile User` AS ppu
            GROUP BY ppu.parent
        """
        get_branches = frappe.db.sql(get_branches_query, as_list=True)
    else:
        user_branches = frappe.get_all('POS Profile User', filters={'user': current_user}, fields=['parent'])
        get_branches = [[ub['parent']] for ub in user_branches]

    branches = [item for sublist in get_branches for item in sublist]
    return branches





      # saleTablequery =  """
        #     SELECT  sp.type , si.total_taxes_and_charges, 
        #     from `tabSales Invoice Payment`  sp
        #     inner join  `tabSales Invoice` as si 
        #     on si.name = sp.parent
        #     """
        # sales_invoice_table = frappe.db.sql(saleTablequery,{
        #     'from_date': from_date,
        #     'to_date': to_date,
        #     'status': status,
        #     'rest_type': rest_type,
        #     'branch': branch,
        #     'posa_pos_opening_shift': posa_pos_opening_shift,
        # },as_dict=True)
        # def get_data(filters):
    # data = []
    
    # if not filters or not filters.get('from_date') or not filters.get('to_date'):
    #     return data

    # from_date = filters.get('from_date')
    # to_date = filters.get('to_date')
    # status = filters.get('status', 'Paid')
    # branch = filters.get('name')  # Branch filter
    # posa_pos_opening_shift = filters.get("posa_pos_opening_shift")  # POSA Opening Shift filter

    # # Conditional query for restaurant types
    # restaurant_types_query = """
    #     SELECT DISTINCT resturent_type
    #     FROM `tabSales Invoice` as si 
    #     WHERE si.posting_date >= %(from_date)s
    #       AND si.posting_date <= %(to_date)s
    #       AND si.status = %(status)s
    # """
    
    # # Include branch filter if provided
    # if branch:
    #     restaurant_types_query += " AND si.pos_profile = %(branch)s"
    
    # # Include posa_pos_opening_shift filter if provided
    # if posa_pos_opening_shift:
    #     restaurant_types_query += " AND si.posa_pos_opening_shift = %(posa_pos_opening_shift)s"

    # restaurant_types_query += " ORDER BY resturent_type ASC"
    
    # # Execute the query
    # restaurant_types = frappe.db.sql(restaurant_types_query, {
    #     'from_date': from_date,
    #     'to_date': to_date,
    #     'status': status,
    #     'branch': branch,
    #     'posa_pos_opening_shift': posa_pos_opening_shift,
    # }, as_dict=True)
    
    # for restaurant_type in restaurant_types:
    #     rest_type = restaurant_type.get('resturent_type')
        
    #     restaurant_totals = {
    #         "gross_sales": 0.0,  # Now reflecting grand_total
    #         "discount_amount": 0.0,
    #         "sub_total": 0.0,  # Now reflecting total directly
    #         "tax_cash": 0.0,
    #         "tax_credit": 0.0,
    #         "cash_sale": 0.0,
    #         "credit_sale": 0.0,
    #         "grand_total": 0.0,
    #     }
        
    #     # Conditional query for sales invoices
    #     sales_invoices_query = """
    #         SELECT 
    #             si.name, 
    #             si.resturent_type, 
    #             si.posting_date, 
    #             si.total, 
    #             si.grand_total, 
    #             si.discount_amount, 
    #             sp.type, 
    #             si.total_taxes_and_charges
    #         FROM 
    #             `tabSales Invoice` AS si
    #         INNER JOIN 
    #             `tabSales Invoice Payment` AS sp ON si.name = sp.parent 
    #         WHERE 
    #             si.posting_date >= %(from_date)s
    #             AND si.posting_date <= %(to_date)s
    #             AND si.status = %(status)s
    #             AND si.resturent_type = %(rest_type)s
    #     """
        
    #     # Include branch filter if provided
    #     if branch:
    #         sales_invoices_query += " AND si.pos_profile = %(branch)s"
        
    #     # Include posa_pos_opening_shift filter if provided
    #     if posa_pos_opening_shift:
    #         sales_invoices_query += " AND si.posa_pos_opening_shift = %(posa_pos_opening_shift)s"
        
    #     sales_invoices_query += " ORDER BY resturent_type ASC"
        
    #     # Execute the query
    #     sales_invoices = frappe.db.sql(sales_invoices_query, {
    #         'from_date': from_date,
    #         'to_date': to_date,
    #         'status': status,
    #         'rest_type': rest_type,
    #         'branch': branch,
    #         'posa_pos_opening_shift': posa_pos_opening_shift,
    #     }, as_dict=True)


        
    #     for invoice in sales_invoices:
    #         repost_doc = frappe.get_doc("Sales Invoice", invoice.name)
    #         tax_amount_by_cash = 0.0
    #         tax_amount_by_tax = 0.0
    #         pay_amount_by_cash = 0.0
    #         pay_amount_by_tax = 0.0
            
    #         for tax in repost_doc.taxes:
    #             if tax.get("rate") == 5:
    #                 tax_amount_by_cash += tax.get("base_tax_amount", 0)
    #             elif tax.get("rate") == 16:
    #                 tax_amount_by_tax += tax.get("base_tax_amount", 0)
            
    #         for pay in repost_doc.payments:
    #             if pay.get("type") == "Cash":
    #                 pay_amount_by_cash += pay.get("amount", 0)
    #             elif pay.get("type") == "Bank":
    #                 pay_amount_by_tax += pay.get("amount", 0)
            
    #         total = float(invoice.get("total", 0))  # Sub Total now comes from total
    #         discount_amount = float(invoice.get("discount_amount", 0))
    #         grand_total = float(invoice.get("grand_total", 0))  # Gross sales from grand_total
            
            
    #         # Add invoice amounts to restaurant totals
    #         restaurant_totals["gross_sales"] += grand_total  # Gross Sales is now grand_total
    #         restaurant_totals["discount_amount"] += discount_amount
    #         restaurant_totals["sub_total"] += total  # Sub Total is directly total
    #         restaurant_totals["tax_cash"] += tax_amount_by_cash
    #         restaurant_totals["tax_credit"] += tax_amount_by_tax
    #         restaurant_totals["cash_sale"] += pay_amount_by_cash
    #         restaurant_totals["credit_sale"] += pay_amount_by_tax
    #         restaurant_totals["grand_total"] += grand_total  # Total sales is grand_total
        
    #     formatted_gross_sales = "Gross Sales Total = {:,.2f}".format(restaurant_totals["gross_sales"])
    #     formatted_discount_amount = "Discount Total = {:,.2f}".format(restaurant_totals["discount_amount"])
    #     formatted_sub_total = "Sub Total = {:,.2f}".format(restaurant_totals["sub_total"])
    #     formatted_tax_cash = "Tax (Cash) Total = {:,.2f}".format(restaurant_totals["tax_cash"])
    #     formatted_tax_credit = "Tax (Credit) Total = {:,.2f}".format(restaurant_totals["tax_credit"])
    #     formatted_cash_sale = "Cash Sales Total = {:,.2f}".format(restaurant_totals["cash_sale"])
    #     formatted_credit_sale = "Credit Sales Total = {:,.2f}".format(restaurant_totals["credit_sale"])
    #     formatted_grand_total = "Total Sales = {:,.2f}".format(restaurant_totals["grand_total"])

    #     # Append only the group summary to data
    #     data.append({
    #         "date": "Restaurant: %s" % rest_type,
    #         "total": formatted_gross_sales,  # Now reflecting gross_sales
    #         "discount_amount": formatted_discount_amount,
    #         "sub_total": formatted_sub_total,  # Sub total is now from total
    #         "tax_cash": formatted_tax_cash,
    #         "tax_credit": formatted_tax_credit,
    #         "cash_sale": formatted_cash_sale,
    #         "credit_sale": formatted_credit_sale,
    #         "grand_total": formatted_grand_total,
    #     })
    
    # return data