# Copyright (c) 2023, Tylextech and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_stock_balance_for
from erpnext.stock.utils import get_stock_balance


class StockTake(Document):
    pass


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def warehouse_items(doctype, txt, searchfield, start, page_len, filters):
    warehouse, company = filters.get("warehouse"), filters.get("company")
    posting_date, posting_time = filters.get("posting_date"), filters.get("posting_time")

    items = get_items(warehouse, posting_date, posting_time, company)
    if items:
        items = [[item['item_code'], item['item_name'] + ', ' + item['item_group']] for item in items]
    return items


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def warehouse_item_groups(doctype, txt, searchfield, start, page_len, filters):
    warehouses, company = filters.get("warehouses"), filters.get("company")
    posting_date, posting_time = filters.get("posting_date"), filters.get("posting_time")

    items = []
    for warehouse in warehouses:
        warehouse_items = get_items(warehouse, posting_date, posting_time, company)
        items.extend(warehouse_items)
    item_groups = []
    for item in items:
        if not [item['item_group'], item['item_group']] in item_groups:
            item_groups.append([item['item_group'], item['item_group']])
    return item_groups


@frappe.whitelist()
def get_branch_warehouses(branch):
    warehouses = []
    branch = frappe.get_doc("Branch", branch)

    warehouses = [{"warehouse_name": d.warehouse} for d in branch.warehouses]
    if branch.rejected_warehouse:
        warehouses.append({"warehouse_name": branch.rejected_warehouse})
    return warehouses


@frappe.whitelist()
def filter_branch_warehouses(doctype, txt, searchfield, start, page_len, filters):
    branch = filters.get("branch")	
    warehouses = get_branch_warehouses(branch)
    warehouses = [[warehouse_dict["warehouse_name"], warehouse_dict["warehouse_name"]] for warehouse_dict in warehouses]
    return warehouses


@frappe.whitelist()
def get_items(
    warehouse, posting_date, posting_time, company, item_code=None, ignore_empty_stock=False, item_groups=None, count_type=None
):
    ignore_empty_stock = cint(ignore_empty_stock)
    items = [frappe._dict({"item_code": item_code, "warehouse": warehouse})]

    if not item_code:
        items = get_items_for_stock_reco(warehouse, company)

    res = []
    itemwise_batch_data = get_itemwise_batch(warehouse, posting_date, company, item_code)

    for d in items:
        if d.item_code in itemwise_batch_data:
            valuation_rate = get_stock_balance(
                d.item_code, d.warehouse, posting_date, posting_time, with_valuation_rate=True
            )[1]

            for row in itemwise_batch_data.get(d.item_code):
                if ignore_empty_stock and not row.qty:
                    continue

                args = get_item_data(row, row.qty, valuation_rate)
                res.append(args)
        else:
            stock_bal = get_stock_balance(
                d.item_code,
                d.warehouse,
                posting_date,
                posting_time,
                with_valuation_rate=True,
                with_serial_no=cint(d.has_serial_no),
            )
            qty, valuation_rate, serial_no = (
                stock_bal[0],
                stock_bal[1],
                stock_bal[2] if cint(d.has_serial_no) else "",
            )

            if ignore_empty_stock and not stock_bal[0]:
                continue

            args = get_item_data(d, qty, valuation_rate, serial_no)

            res.append(args)

    item_groups = json.loads(item_groups) if item_groups else None
    if item_groups:
        res = filter(lambda item: item["item_group"] in item_groups, res)
    print(res)
    count_type = json.loads(count_type) if count_type else None
    if count_type:
        res = filter(lambda item: item["count_type"] in count_type, res)

    res = sorted(res, key = lambda item: item["item_group"])
    return res


def get_items_for_stock_reco(warehouse, company):
    lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
    items = frappe.db.sql(
        f"""
        select
            i.count_type,i.name as item_code, i.item_name, i.item_group, bin.warehouse as warehouse, i.has_serial_no, i.has_batch_no
        from
            `tabBin` bin, `tabItem` i
        where
            i.name = bin.item_code
            and IFNULL(i.disabled, 0) = 0
            and i.is_stock_item = 1
            and i.has_variants = 0
            and exists(
                select name from `tabWarehouse` where lft >= {lft} and rgt <= {rgt} and name = bin.warehouse
            )
    """,
        as_dict=1,
    )

    items += frappe.db.sql(
        """
        select
            i.count_type,i.name as item_code, i.item_name, i.item_group, id.default_warehouse as warehouse, i.has_serial_no, i.has_batch_no
        from
            `tabItem` i, `tabItem Default` id
        where
            i.name = id.parent
            and exists(
                select name from `tabWarehouse` where lft >= %s and rgt <= %s and name=id.default_warehouse
            )
            and i.is_stock_item = 1
            and i.has_variants = 0
            and IFNULL(i.disabled, 0) = 0
            and id.company = %s
        group by i.name
    """,
        (lft, rgt, company),
        as_dict=1,
    )

    # remove duplicates
    # check if item-warehouse key extracted from each entry exists in set iw_keys
    # and update iw_keys
    iw_keys = set()
    items = [
        item
        for item in items
        if [
            (item.item_code, item.warehouse) not in iw_keys,
            iw_keys.add((item.item_code, item.warehouse)),
        ][0]
    ]

    return items



def get_itemwise_batch(warehouse, posting_date, company, item_code=None):
    from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import execute

    itemwise_batch_data = {}

    filters = frappe._dict(
        {"warehouse": warehouse, "from_date": posting_date, "to_date": posting_date, "company": company}
    )

    if item_code:
        filters.item_code = item_code

    columns, data = execute(filters)

    for row in data:
        itemwise_batch_data.setdefault(row[0], []).append(
            frappe._dict(
                {
                    "item_code": row[0],
                    "item_group": row[2],
                    "warehouse": warehouse,
                    "qty": row[9],
                    "item_name": row[1],
                    "batch_no": row[5],
                }
            )
        )

    return itemwise_batch_data



def get_item_data(row, qty, valuation_rate, serial_no=None):
    return {
        "item_code": row.item_code,
        "warehouse": row.warehouse,
        "qty": qty,
        "item_name": row.item_name,
        "item_group": row.item_group,
        "valuation_rate": valuation_rate,
        "current_qty": qty,
        "current_valuation_rate": valuation_rate,
        "current_serial_no": serial_no,
        "serial_no": serial_no,
        "batch_no": row.get("batch_no"),
        "count_type": row.count_type
    }



@frappe.whitelist()
def make_stock_reconciliation(source_name: str, target_doc=None):
    def set_missing_values(source, target, source_parent):
        target.purpose = "Stock Reconciliation"
        target.set_warehouse = source.warehouse

    def update_item(source, target, source_parent):
        stock_balance = get_stock_balance_for(source.item_code, source.warehouse, source_parent.posting_date, source_parent.posting_time)
        print(f"stock_balance: {stock_balance}")
        target.valuation_rate = stock_balance["rate"]
        target.current_valuation_rate = stock_balance["rate"]
        target.current_serial_no = stock_balance["serial_nos"]
        target.serial_nos = stock_balance["serial_nos"]
        target.amount = target.qty * target.valuation_rate
        target.current_amount = stock_balance["rate"] * source.current_stock
        target.amount_difference = target.amount - target.current_amount

    return get_mapped_doc("Stock Take", source_name, {
        "Stock Take": {
            "doctype": "Stock Reconciliation",
            "validation": {"docstatus": ["=", 1]},
            "field_map": {
                "stock_take": "name",
            },
            "field_no_map": [
                "items"
            ],
            "postprocess": set_missing_values,
        },
        "Stock Take Item": {
            "doctype": "Stock Reconciliation Item",
            "field_map": {
                "item_name": "item_name",
                "physical_stock": "qty",
                "current_stock": "current_qty",
                "stock_difference": "quantity_difference",
            },
            "postprocess": update_item,
        }
    }, target_doc)