import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, nowtime, cint


class BulkBOMManufacturing(Document):
    def validate(self):
        self.set_defaults()
        self.validate_main_fields()
        self.validate_bom_rows()

    def set_defaults(self):
        if not self.posting_date:
            self.posting_date = nowdate()

    def validate_main_fields(self):
        if not self.company:
            frappe.throw(_("Company is required."))

        if not self.source_warehouse:
            frappe.throw(_("Source Warehouse is required."))

        if not self.target_warehouse:
            frappe.throw(_("Target Warehouse is required."))

        validate_transaction_warehouse(self.source_warehouse, "Source Warehouse", self.company)
        validate_transaction_warehouse(self.target_warehouse, "Target Warehouse", self.company)

    def validate_bom_rows(self):
        if not self.bom_items:
            frappe.throw(_("Please add at least one BOM row."))

        for row in self.bom_items:
            if not row.bom:
                frappe.throw(_("BOM is required in row {0}.").format(row.idx))

            if flt(row.qty_to_manufacture) <= 0:
                frappe.throw(
                    _("Qty to Manufacture must be greater than zero in row {0}.").format(row.idx)
                )

            bom = frappe.get_doc("BOM", row.bom)

            if bom.docstatus != 1:
                frappe.throw(_("BOM {0} must be submitted.").format(row.bom))

            if not cint(bom.is_active):
                frappe.throw(_("BOM {0} is not active.").format(row.bom))

            if bom.company and bom.company != self.company:
                frappe.throw(
                    _("BOM {0} belongs to company {1}, but this document company is {2}.")
                    .format(row.bom, bom.company, self.company)
                )

            row.item_code = bom.item

            source_warehouse = row.source_warehouse or self.source_warehouse
            target_warehouse = row.target_warehouse or self.target_warehouse

            validate_transaction_warehouse(
                source_warehouse,
                "Source Warehouse in row {0}".format(row.idx),
                self.company
            )

            validate_transaction_warehouse(
                target_warehouse,
                "Target Warehouse in row {0}".format(row.idx),
                self.company
            )


def validate_transaction_warehouse(warehouse, label, company=None):
    if not warehouse:
        return

    wh = frappe.db.get_value(
        "Warehouse",
        warehouse,
        ["name", "is_group", "company"],
        as_dict=True
    )

    if not wh:
        frappe.throw(_("{0} {1} does not exist.").format(label, warehouse))

    if cint(wh.is_group):
        frappe.throw(
            _("{0} {1} is a Group Warehouse. Please select a non-group warehouse.")
            .format(label, warehouse)
        )

    if company and wh.company and wh.company != company:
        frappe.throw(
            _("{0} {1} belongs to company {2}, not {3}.")
            .format(label, warehouse, wh.company, company)
        )


@frappe.whitelist()
def create_manufacturing_entries(docname):
    doc = frappe.get_doc("Bulk BOM Manufacturing", docname)
    doc.check_permission("write")

    if doc.docstatus != 1:
        frappe.throw(_("Please submit the document before creating Stock Entries."))

    if cint(doc.stock_created):
        frappe.throw(_("Stock Entries are already created from this document."))

    validate_required_custom_fields(doc)

    pending_rows = []

    for row in doc.bom_items:
        if cint(row.created) or row.stock_entry:
            continue

        pending_rows.append(row)

    if not pending_rows:
        frappe.throw(_("No pending BOM rows found."))

    created_entries = []

    for row in pending_rows:
        bom = frappe.get_doc("BOM", row.bom)

        stock_entry = make_manufacture_stock_entry_from_bom(doc, row, bom)

        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

        source_warehouse = row.source_warehouse or doc.source_warehouse
        target_warehouse = row.target_warehouse or doc.target_warehouse

        # 1. Update the original BOM row.
        frappe.db.set_value(
            row.doctype,
            row.name,
            {
                "item": bom.item,
                "created": 1,
                "stock_entry": stock_entry.name
            },
            update_modified=False
        )

        # 2. Add row into Created Stock Entries child table.
        add_created_stock_entry_log(
            doc=doc,
            row=row,
            bom=bom,
            stock_entry=stock_entry,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse
        )

        created_entries.append(stock_entry.name)

    # 3. Mark parent as completed.
    frappe.db.set_value(
        doc.doctype,
        doc.name,
        "stock_created",
        1,
        update_modified=False
    )

    frappe.msgprint(
        _("Manufacturing Stock Entries created: {0}")
        .format(", ".join(created_entries))
    )

    return created_entries


def validate_required_custom_fields(doc):
    parent_meta = frappe.get_meta(doc.doctype)

    required_parent_fields = [
        "bom_items",
        "stock_entries",
        "stock_created"
    ]

    for fieldname in required_parent_fields:
        if not parent_meta.get_field(fieldname):
            frappe.throw(
                _("Missing field {0} in DocType {1}.")
                .format(fieldname, doc.doctype)
            )

    bom_items_field = parent_meta.get_field("bom_items")
    bom_item_doctype = bom_items_field.options
    bom_item_meta = frappe.get_meta(bom_item_doctype)

    required_bom_item_fields = [
        "bom",
        "item",
        "qty_to_manufacture",
        "created",
        "stock_entry"
    ]

    for fieldname in required_bom_item_fields:
        if not bom_item_meta.get_field(fieldname):
            frappe.throw(
                _("Missing field {0} in child DocType {1}.")
                .format(fieldname, bom_item_doctype)
            )

    log_field = parent_meta.get_field("stock_entries")
    log_doctype = log_field.options
    log_meta = frappe.get_meta(log_doctype)

    required_log_fields = [
        "bom",
        "item",
        "qty",
        "stock_entry",
        "status"
    ]

    for fieldname in required_log_fields:
        if not log_meta.get_field(fieldname):
            frappe.throw(
                _("Missing field {0} in child DocType {1}.")
                .format(fieldname, log_doctype)
            )


def make_manufacture_stock_entry_from_bom(doc, row, bom):
    source_warehouse = row.source_warehouse or doc.source_warehouse
    target_warehouse = row.target_warehouse or doc.target_warehouse
    qty = flt(row.qty_to_manufacture)

    validate_transaction_warehouse(source_warehouse, "Source Warehouse in row {0}".format(row.idx), doc.company)
    validate_transaction_warehouse(target_warehouse, "Target Warehouse in row {0}".format(row.idx), doc.company)

    if bom.docstatus != 1:
        frappe.throw(_("BOM {0} must be submitted.").format(row.bom))

    if not cint(bom.is_active):
        frappe.throw(_("BOM {0} is not active.").format(row.bom))

    if qty <= 0:
        frappe.throw(_("Qty to Manufacture must be greater than zero in row {0}.").format(row.idx))

    stock_entry = frappe.new_doc("Stock Entry")

    stock_entry.purpose = "Manufacture"
    stock_entry.stock_entry_type = "Manufacture"

    if hasattr(stock_entry, "set_stock_entry_type"):
        stock_entry.set_stock_entry_type()

    stock_entry.company = doc.company
    stock_entry.set_posting_time = 1
    stock_entry.posting_date = doc.posting_date or nowdate()

    # This is the BOM link.
    stock_entry.from_bom = 1
    stock_entry.bom_no = row.bom
    stock_entry.fg_completed_qty = qty

    # Raw materials from here.
    stock_entry.from_warehouse = source_warehouse

    # Finished good goes here.
    stock_entry.to_warehouse = target_warehouse

    # if stock_entry.meta.get_field("use_multi_level_bom"):
    #     stock_entry.use_multi_level_bom = 1

    if stock_entry.meta.get_field("remarks"):
        stock_entry.remarks = _(
            "Created from Bulk BOM Manufacturing {0}, row {1}, BOM {2}."
        ).format(doc.name, row.idx, row.bom)

    stock_entry.get_items()

    # Do not manually append finished good.
    # Only force selected warehouses into ERPNext-generated rows.
    for item in stock_entry.items:
        if item.s_warehouse:
            item.s_warehouse = source_warehouse

        if item.t_warehouse:
            item.t_warehouse = target_warehouse

    if hasattr(stock_entry, "mark_finished_and_secondary_items"):
        stock_entry.mark_finished_and_secondary_items()

    finished_goods = [
        item for item in stock_entry.items
        if cint(item.is_finished_item)
    ]

    if not finished_goods:
        frappe.throw(
            _("BOM {0} did not generate a Finished Good row. Please check BOM {0}.")
            .format(row.bom)
        )

    if len(finished_goods) > 1:
        frappe.throw(
            _("BOM {0} generated more than one Finished Good row.")
            .format(row.bom)
        )

    return stock_entry


def add_created_stock_entry_log(doc, row, bom, stock_entry, source_warehouse, target_warehouse):
    parentfield = "stock_entries"

    table_field = frappe.get_meta(doc.doctype).get_field(parentfield)

    if not table_field:
        frappe.throw(
            _("Parent DocType {0} does not have child table field {1}.")
            .format(doc.doctype, parentfield)
        )

    child_doctype = table_field.options

    next_idx = frappe.db.count(
        child_doctype,
        {
            "parent": doc.name,
            "parenttype": doc.doctype,
            "parentfield": parentfield
        }
    ) + 1

    log_data = {
        "doctype": child_doctype,
        "parent": doc.name,
        "parenttype": doc.doctype,
        "parentfield": parentfield,
        "idx": next_idx,
        "bom": row.bom,
        "item": bom.item,
        "qty": flt(row.qty_to_manufacture),
        "stock_entry": stock_entry.name,
        "status": "Submitted"
    }

    log_meta = frappe.get_meta(child_doctype)

    if log_meta.get_field("source_warehouse"):
        log_data["source_warehouse"] = source_warehouse

    if log_meta.get_field("target_warehouse"):
        log_data["target_warehouse"] = target_warehouse

    log = frappe.get_doc(log_data)
    log.insert(ignore_permissions=True)