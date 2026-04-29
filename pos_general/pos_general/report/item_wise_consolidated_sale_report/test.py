# Copyright (c) 2022, Hussain and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta, date
from frappe.utils import cstr, cint, getdate
import calendar
from datetime import datetime, timedelta

def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data



def get_data(filters):
    
    data = []
    conditions = get_conditions(filters)
    query = """
        SELECT sales_invoice as invoice
        FROM
            `tabPOS Closing Shift` sii
        JOIN
            `tabSales Invoice Reference` sir
        
        WHERE 
            DATE(sii.period_start_date) = %(start_date)s    
            AND sir.parent = sii.name

       
    """
    closing_shift = frappe.db.sql(query,{
        'start_date':filters.get('from_date')
    },as_dict=True)


    # for cs in closing_shift:
    #     # data=[]
    #     print('Working')
    #     sales_invoice_reference = frappe.get_all("Sales Invoice Reference",fields=["sales_invoice"],filters = [["parent", "=", cs.name]])
    #     print(cs)
    #     print(len(sales_invoice_reference))
    #     d = []

    #     for sir in sales_invoice_reference:
    #         d.append(sir.sales_invoice)
        
        
    sales_invoices_str = ', '.join(["'%s'" % item for item in closing_shift])
    query = """
    SELECT  
        sii.item_code,sii.item_name,sii.uom,
        ROUND(SUM(CASE WHEN sii.qty > 0 THEN sii.qty ELSE 0 END),2) AS qty,
        ROUND(SUM(CASE WHEN sii.qty < 0 THEN sii.qty ELSE 0 END),2) AS r_qty, ROUND(SUM(CASE WHEN sii.qty > 0 THEN sii.qty ELSE 0 END) +
        SUM(CASE WHEN sii.qty < 0 THEN sii.qty ELSE 0 END),2) AS n_qty,
        ROUND((pr.price_list_rate),2) as price_list_rate,
        ROUND((SUM(CASE WHEN sii.qty > 0 THEN sii.qty ELSE 0 END) + SUM(CASE WHEN sii.qty < 0 THEN sii.qty ELSE 0 END))*pr.price_list_rate,2) as amount
    FROM
        `tabSales Invoice Item` sii
    JOIN
        `tabSales Invoice` si ON sii.parent = si.name
    INNER JOIN
        `tabItem Price` pr ON sii.item_code = pr.item_code
    WHERE sii.parent IN ({})   
    GROUP BY
        sii.item_code,sii.item_name,sii.uom
    ORDER BY
        sii.item_code;  
    """.format(sales_invoices_str)
    shift = frappe.db.sql(query,as_dict=True)
    for s in shift:
        data.append(s)
    # Convert list of dictionaries to set of tuples to remove duplicates
    unique_data = {tuple(item.items()) for item in data}

    # Convert set of tuples back to list of dictionaries
    unique_data = [dict(item) for item in unique_data]
    # print(unique_data)
     
    return unique_data
def get_conditions(filters):
    conditions = "1=1"
    return conditions

def get_columns(filters):
    columns = [
        
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": _("ITEM DESCRIPTION"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 120},
        {"label": _("QTY"), "fieldname": "qty", "fieldtype": "Data", "width": 120},
        {"label": _("R.QTY"), "fieldname": "r_qty", "fieldtype": "Data", "width": 120},
        {"label": _("N.QTY"), "fieldname": "n_qty", "fieldtype": "Data", "width": 120},
        {"label": _("RATE"), "fieldname": "price_list_rate", "fieldtype": "Data", "width": 120},
        {"label": _("AMOUNT"), "fieldname": "amount", "fieldtype": "Data", "width": 120}
        



     

    ]
    return columns

    #  query = """
    #     SELECT
    #         sii.item_code,sii.item_name,sii.uom, 
    #         ROUND(SUM(CASE WHEN sii.qty > 0 THEN sii.qty ELSE 0 END),2) AS qty,
    #         ROUND(SUM(CASE WHEN sii.qty < 0 THEN sii.qty ELSE 0 END),2) AS r_qty, ROUND(SUM(CASE WHEN sii.qty > 0 THEN sii.qty ELSE 0 END) +
    #         SUM(CASE WHEN sii.qty < 0 THEN sii.qty ELSE 0 END),2) AS n_qty,
    #         ROUND((pr.price_list_rate),2) as price_list_rate,
    #         ROUND((SUM(CASE WHEN sii.qty > 0 THEN sii.qty ELSE 0 END) + SUM(CASE WHEN sii.qty < 0 THEN sii.qty ELSE 0 END))*pr.price_list_rate,2) as amount
    #     FROM








    #         `tabSales Invoice Item` sii
    #     JOIN
    #         `tabSales Invoice` si ON sii.parent = si.name

    #     INNER JOIN
    #         `tabItem Price` pr ON sii.item_code = pr.item_code


    #     WHERE
    #         si.docstatus = 1
    #         AND si.posting_date BETWEEN %(start_date)s AND %(end_date)s
    #         AND si.posting_time BETWEEN %(start_time)s AND %(end_time)s
        # GROUP BY
        #     sii.item_code,sii.item_name,sii.uom
        # ORDER BY
        #     sii.item_code;
    # """
    
    # data = frappe.db.sql(query, {
    #     'start_date': filters.get("from_date"),
    #     'end_date': filters.get("to_date"),
    #     'start_time': filters.get("from_time"),
    #     'end_time': filters.get("to_time")
    # }, as_dict=True)
    # print(data)






 

     # get_item_query = frappe.get_all("Item", fields=["item_code","item_name","stock_uom"])    
    # for it in get_item_query:
    #     sales_invoice_list = frappe.get_all("Sales Invoice",filters=[["posting_date", ">=",filters.get('from_date')],["posting_date", "<=",filters.get('to_date')],["posting_time", ">=",filters.get('from_time')],["posting_time", "<=",filters.get('to_time')]],fields=["name"])  
    #     if sales_invoice_list:  
    #         for inv in sales_invoice_list:
    #             inv_doc = frappe.get_doc("Sales Invoice",inv.name)
    #             tqty=0
    #             rtqty=0
    #             for child in inv_doc.items:
    #                 if child.item_code == it.item_code:
                        
    #                     if child.qty > 0:
    #                         tqty=tqty+child.qty
    #             row=[]
    #             if not it.item_code in row:
    #                 row=[it.item_code,it.item_name,it.stock_uom,tqty]
                
    #             data.append(row)
                        



            
    

    # Loop through each item retrieved from the database
    # for it in get_item_query:
    #      # For each item, get all sales invoice items related to it
    #     get_so2_query = frappe.get_all("Sales Invoice Item", filters=[ ["item_code", "=",it.item_code],["docstatus", "=",1],["creation", ">=",filters.get('from_date')],["creation", "<=",filters.get('to_date')] ], fields=["*"] )
    #     get_so3_query = frappe.get_all("Item Price", filters={"item_code":it.item_code}, fields=["*"])
    #     rate=0
    #     if get_so3_query:
    #         rate=get_so3_query[0].price_list_rate
    #     tqty=0
    #     rtqty=0
    #     for so2 in get_so2_query:
    #         if so2.qty > 0:
    #             tqty=tqty+so2.qty
    #         else:
    #             rtqty=rtqty+so2.qty
  
    #     row2 = []
    #     row2 = [it.item_code,it.item_n
    # ame,it.stock_uom,f"{tqty:,.2f}",f"{rtqty:,.2f}",f"{tqty+rtqty:,.2f}",f"{rate:,.2f}",rate*(tqty+rtqty)]
    #     data.append(row2) 