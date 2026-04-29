# Copyright (c) 2022, Hussain and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr, cint, getdate,flt
def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data
def get_data(filters):



    data = []
    conditions = get_conditions(filters)
    if filters.get("item_group"):
        get_item_group = frappe.db.sql(""" select * from `tabItem Group` where parent_item_group='RAW MATERIAL' and  name='"""+filters.get("item_group")+"""' """.format(conditions=conditions),filters,as_dict=1,)
    else:
        get_item_group = frappe.db.sql(""" select * from `tabItem Group` where parent_item_group='RAW MATERIAL' """.format(conditions=conditions),filters,as_dict=1,)
    
    # warehouse = ""
    # if filters.get("warehouse"):
        # warehouse = " and sle.warehouse = %(warehouse)s"

    for gr in get_item_group:
        rowgroup = []
        rowgroup = [f'<strong>{gr.name}</strong>','','','','','','','','','','','','','','','','','','']
        data.append(rowgroup)
        if filters.get("warehouse"):
            check_bol = frappe.db.sql(
                f""" 
                    SELECT 
                    it.name AS item_code,
                    it.item_group AS item_group,
                    it.item_name AS item_name,
                    it.last_purchase_rate,
                    it.stock_uom,
                    ledger.warehouse AS warehouse,
                    ledger.opening_qty AS opening_qty,
                    ledger.received_qty AS received_qty,
                    ledger.dispatch_qty AS dispatch_qty,
                    (ledger.opening_qty + ledger.received_qty - abs(ledger.dispatch_qty)) as closing_qty
                FROM 
                    `tabItem` AS it
                JOIN (
                    SELECT 
                        sle.item_code,
                        sle.warehouse,
                        SUM(CASE WHEN sle.posting_date < '"""+filters.get("from_date")+"""' THEN sle.actual_qty ELSE 0 END) AS opening_qty,
                        SUM(CASE WHEN sle.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""' AND sle.actual_qty > 0 THEN sle.actual_qty ELSE 0 END) AS received_qty,
                        SUM(CASE WHEN sle.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""' AND sle.actual_qty < 0 THEN sle.actual_qty ELSE 0 END) AS dispatch_qty
                    FROM 
                        `tabStock Ledger Entry` AS sle
                    WHERE 
                        is_cancelled=0 and sle.warehouse='"""+filters.get("warehouse")+"""'
                    GROUP BY 
                        sle.item_code, sle.warehouse
                ) AS ledger ON ledger.item_code = it.name
                WHERE 
                    it.name is not null and it.item_group='"""+gr.name+"""'
                    {conditions}
                    """.format(conditions=conditions),
                    filters,
                    as_dict=1,
                )
        else:
            check_bol = frappe.db.sql(
            f""" 
                SELECT 
                it.name AS item_code,
                it.item_group AS item_group,
                it.item_name AS item_name,
                it.last_purchase_rate,
                it.stock_uom,
                ledger.warehouse AS warehouse,
                ledger.opening_qty AS opening_qty,
                ledger.received_qty AS received_qty,
                ledger.dispatch_qty AS dispatch_qty,
                (ledger.opening_qty + ledger.received_qty - abs(ledger.dispatch_qty)) as closing_qty
            FROM 
                `tabItem` AS it
            JOIN (
                SELECT 
                    sle.item_code,
                    sle.warehouse,
                    SUM(CASE WHEN sle.posting_date < '"""+filters.get("from_date")+"""' THEN sle.actual_qty ELSE 0 END) AS opening_qty,
                    SUM(CASE WHEN sle.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""' AND sle.actual_qty > 0 THEN sle.actual_qty ELSE 0 END) AS received_qty,
                    SUM(CASE WHEN sle.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""' AND sle.actual_qty < 0 THEN sle.actual_qty ELSE 0 END) AS dispatch_qty
                FROM 
                    `tabStock Ledger Entry` AS sle
                WHERE 
                    is_cancelled=0 
                GROUP BY 
                    sle.item_code, sle.warehouse
            ) AS ledger ON ledger.item_code = it.name
            WHERE 
                it.name is not null and it.item_group='"""+gr.name+"""'
                {conditions}
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )
        tot_theoretical_usage_cost=0
        tot_variance=0
        for bol in check_bol:
            #purchase qty
            get_purchase_qty = frappe.db.sql(""" 
                select sum(qty) as purchase_qty from `tabPurchase Receipt Item` b
                inner join  `tabPurchase Receipt` a on a.name=b.parent
                where b.item_code='"""+bol.item_code+"""' and a.docstatus =1 and a.set_warehouse='"""+bol.warehouse+"""'
                and a.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""'
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )
            if get_purchase_qty:
                purchase_qty=get_purchase_qty[0].purchase_qty
            else:
                purchase_qty=0
                

            #        Transfer In
            get_transfer_in_qty = frappe.db.sql(""" 
                select sum(qty) as transfer_in_qty from `tabStock Entry Detail` b
                inner join  `tabStock Entry` a on a.name=b.parent
                where b.item_code='"""+bol.item_code+"""' and a.stock_entry_type='Material Transfer' and a.docstatus =1 and b.t_warehouse='"""+bol.warehouse+"""'
                and a.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""'
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )
            if get_transfer_in_qty:
                transfer_in_qty=get_transfer_in_qty[0].transfer_in_qty
            else:
                transfer_in_qty=0
                
            #        Transfer Out
            get_transfer_out_qty = frappe.db.sql(""" 
                select sum(qty) as transfer_out_qty from `tabStock Entry Detail` b
                inner join  `tabStock Entry` a on a.name=b.parent
                where b.item_code='"""+bol.item_code+"""' and a.stock_entry_type='Material Transfer' and a.docstatus =1 and b.s_warehouse='"""+bol.warehouse+"""'
                and a.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""'
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )
            if get_transfer_out_qty:
                transfer_out_qty=get_transfer_out_qty[0].transfer_out_qty
            else:
                transfer_out_qty=0
                
            #        Return
            get_purchase_return_qty = frappe.db.sql(""" 
                select sum(qty) as purchase_return_qty from `tabPurchase Receipt Item` b
                inner join  `tabPurchase Receipt` a on a.name=b.parent
                where b.item_code='"""+bol.item_code+"""' and a.docstatus =1 and a.is_return=0 and a.set_warehouse='"""+bol.warehouse+"""'
                and a.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""'
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )
            if get_purchase_return_qty:
                purchase_return_qty=get_purchase_return_qty[0].purchase_return_qty
            else:
                purchase_return_qty=0
                
            #        Transfer Out
            get_adjustment_qty = frappe.db.sql(""" 
                select sum(qty) as adjustment_qty from `tabStock Entry Detail` b
                inner join  `tabStock Entry` a on a.name=b.parent
                where b.item_code='"""+bol.item_code+"""' and a.stock_entry_type='Material Issue' and a.docstatus =1 and b.s_warehouse='"""+bol.warehouse+"""'
                and a.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""'
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )
            if get_adjustment_qty:
                adjustment_qty=get_adjustment_qty[0].adjustment_qty
            else:
                adjustment_qty=0

            # Enterd Closing Stock from Stock Take Doc
            get_physical_stock = frappe.db.sql(""" 
                select sum(physical_stock) as physical_stock from `tabStock Take Item` b
                inner join  `tabStock Take` a on a.name=b.parent
                where b.item_code='"""+bol.item_code+"""' and a.docstatus =1 and b.warehouse='"""+bol.warehouse+"""'
                and a.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""'
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )
            if get_physical_stock:
                physical_stock=get_physical_stock[0].physical_stock
            else:
                physical_stock=0

            # theoretical_usage
            get_theoretical_usage = frappe.db.sql(""" 
                select sum(qty) as theoretical_usage_qty,sum(amount) as theoretical_usage_amount from `tabStock Entry Detail` b
                inner join  `tabStock Entry` a on a.name=b.parent
                where b.item_code='"""+bol.item_code+"""' and a.stock_entry_type='Manufacture' and a.docstatus =1 and b.s_warehouse='"""+bol.warehouse+"""'
                and a.posting_date BETWEEN '"""+filters.get("from_date")+"""' AND '"""+filters.get("to_date")+"""'
                """.format(conditions=conditions),
                filters,
                as_dict=1,
            )

            
            if get_theoretical_usage:
                theoretical_usage_qty=get_theoretical_usage[0].theoretical_usage_qty
                theoretical_usage_amount=get_theoretical_usage[0].theoretical_usage_amount
                tot_theoretical_usage_cost += flt(theoretical_usage_amount)
            else:
                theoretical_usage_qty=0
                theoretical_usage_amount=0
                tot_theoretical_usage_cost += flt(theoretical_usage_amount)
            
            
            actual_usage=flt(bol.opening_qty)+flt(transfer_in_qty)-flt(transfer_out_qty)-flt(purchase_return_qty)-flt(physical_stock)
            variance=flt(bol.closing_qty)-flt(physical_stock)
            variance_cost=flt(flt(bol.closing_qty)-flt(physical_stock)) * flt(bol.last_purchase_rate)
            tot_variance += flt(variance_cost)
            # if physical_stock==0:
            row1 = []
            row1 = ['',bol.item_code,bol.item_name,bol.warehouse,bol.last_purchase_rate,bol.stock_uom,bol.opening_qty,purchase_qty,transfer_in_qty,transfer_out_qty,purchase_return_qty,adjustment_qty,theoretical_usage_qty,theoretical_usage_amount,actual_usage,bol.closing_qty,physical_stock,variance,variance_cost]
            data.append(row1)

        rowtotal = []
        rowtotal = ['<b>Total</b>','','','','','','','','','','','','',f'<strong>{tot_theoretical_usage_cost}</strong>','','','','',f'<strong>{tot_variance}</strong>']
        data.append(rowtotal)

        rowempty = []
        rowempty = ['','','','','','','','','','','','','','','','','','','']
        data.append(rowempty)
    return data

def get_conditions(filters):
    conditions = ""
    if filters.get("item_code"):
        conditions += " AND it.name = %(item_code)s"
    if filters.get("item_group"):
        conditions += " AND it.item_group = %(item_group)s"
    return conditions

def get_columns(filters):
    columns = [
        {
            "label": _("Item Group"),
            "options": "Item Group",
            "fieldname": "item_group",
            "fieldtype": "Link",
            "width": 130,
        },
        {
            "label": _("Item Code"),
            "options": "Item",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "width": 130,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 130,
        },
         {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "hidden": "1",
            "options": "Warehouse",
            "width": 130,
        },
        {
            "label": _("IUCost"),
            "fieldname": "last_purchase_rate",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("IUnit"),
            "fieldname": "stock_uom",
            "options": "UOM",
            "fieldtype": "Link",
            "width": 130,
        },
        {
            "label": _("Opening Qty"),
            "fieldname": "opening_qty",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Purchase Qty"),
            "fieldname": "purchase_qty",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Transfer In"),
            "fieldname": "transfer_in",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Transfer Out"),
            "fieldname": "transfer_out",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Return"),
            "fieldname": "purchase_return_qty",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Adjustment Qty"),
            "fieldname": "adjustment_qty",
            "fieldtype": "Float",
            "hidden": "1",
            "width": 130,
        },
        {
            "label": _("Theoretical Usage"),
            "fieldname": "theoretical_usage",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Theoretical Usage Cost"),
            "fieldname": "theoretical_usage_cost",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Actual Usage"),
            "fieldname": "actual_usage",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Expected Closing Stock"),
            "fieldname": "closing_qty",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Entered Closing Stock"),
            "fieldname": "entered_closing_stock",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Veriance"),
            "fieldname": "veriance",
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "label": _("Veriance Cost"),
            "fieldname": "veriance_cost",
            "fieldtype": "Float",
            "width": 130,
        },

        
    ]
    return columns