import frappe
from typing import List, Tuple, Set

# Lower-level docs first
CANCEL_PRIORITY = [
    "Stock Entry",
    "Delivery Note",
    "Payment Entry",
    "Journal Entry",
    "Kitchen Order Ticket",
    "Automated BOM Manufacturing",
]

def _is_child_table(doctype: str) -> bool:
    return bool(frappe.get_cached_value("DocType", doctype, "istable"))

def _dynamic_link_parents(dt: str, name: str) -> List[Tuple[str, str]]:
    return [
        (r.parenttype, r.parent)
        for r in frappe.get_all(
            "Dynamic Link",
            filters={"link_doctype": dt, "link_name": name},
            fields=["parenttype", "parent"],
        )
    ]

def _docs_from_link_fields(dt: str, name: str) -> List[Tuple[str, str]]:
    """Generic: DocFields with fieldtype=Link options=<dt>, including via child tables."""
    found = set()
    dfields = frappe.get_all(
        "DocField",
        filters={"fieldtype": "Link", "options": dt},
        fields=["parent", "fieldname"],
    )
    for df in dfields:
        parent_dt, fn = df.parent, df.fieldname
        if _is_child_table(parent_dt):
            rows = frappe.get_all(parent_dt, filters={fn: name}, fields=["parent"])
            if rows:
                for holder in frappe.get_all(
                    "DocField",
                    filters={"fieldtype": "Table", "options": parent_dt},
                    fields=["parent"],
                ):
                    for r in rows:
                        if frappe.db.exists(holder.parent, r.parent):
                            found.add((holder.parent, r.parent))
        else:
            for docname in frappe.get_all(parent_dt, filters={fn: name}, pluck="name"):
                found.add((parent_dt, docname))
    return list(found)

def _special_links(dt: str, name: str) -> List[Tuple[str, str]]:
    """
    Your explicit relationships:
    - Sales Invoice -> Automated BOM Manufacturing via ABM.reference_name
    - Automated BOM Manufacturing -> Stock Entry via Stock Entry.automated_bom_manufacturing
    Plus a few common ones (PE refs, DN Items vs SI).
    """
    out = []

    if dt == "Sales Invoice":
        # ABM rows where reference_name = this SI
        for abm in frappe.get_all(
            "Automated BOM Manufacturing",
            filters={"reference_name": name},
            pluck="name",
        ):
            out.append(("Automated BOM Manufacturing", abm))

        # Common: Payment Entry Reference -> Payment Entry
        for r in frappe.get_all(
            "Payment Entry Reference",
            filters={"reference_doctype": "Sales Invoice", "reference_name": name},
            fields=["parent"],
            distinct=True,
        ):
            out.append(("Payment Entry", r.parent))

        for kot in frappe.get_all(
            "Kitchen Order Ticket",
            filters={"sales_invoice": name},
            pluck="name",
        ):
            out.append(("Kitchen Order Ticket", kot))

        # Delivery Notes that were made against this SI (if used in your flow)
        for r in frappe.get_all(
            "Delivery Note Item",
            filters={"against_sales_invoice": name},
            fields=["parent"],
            distinct=True,
        ):
            out.append(("Delivery Note", r.parent))

    if dt == "Automated BOM Manufacturing":
        # Stock Entries with custom link field automated_bom_manufacturing
        if frappe.db.has_column("Stock Entry", "automated_bom_manufacturing"):
            for se in frappe.get_all(
                "Stock Entry",
                filters={"automated_bom_manufacturing": name},
                pluck="name",
            ):
                out.append(("Stock Entry", se))

    return out

def _children_of(dt: str, name: str) -> List[Tuple[str, str]]:
    hits = set()

    # 1) explicit special links (your fields)
    for x in _special_links(dt, name):
        hits.add(x)

    # 2) dynamic links
    for x in _dynamic_link_parents(dt, name):
        hits.add(x)

    # 3) generic link fields (parent or via child tables)
    for x in _docs_from_link_fields(dt, name):
        hits.add(x)

    ordered = sorted(hits, key=lambda x: CANCEL_PRIORITY.index(x[0]) if x[0] in CANCEL_PRIORITY else 999)
    return ordered

def _cancel_doc(dt: str, name: str, report: List[str], visited: Set[Tuple[str, str]]):
    key = (dt, name)
    if key in visited:
        return
    visited.add(key)

    # Cancel children first (depth-first)
    for c_dt, c_name in _children_of(dt, name):
        _cancel_doc(c_dt, c_name, report, visited)

    # Then cancel this doc
    doc = frappe.get_doc(dt, name)
    if doc.docstatus == 1:
        doc.cancel()
        report.append(f"Cancelled {dt} {name}")
    elif doc.docstatus == 2:
        report.append(f"Already cancelled {dt} {name}")
    else:
        report.append(f"Skipped {dt} {name} (Draft)")

@frappe.whitelist()
def cascade_cancel_sales_invoice(si_name: str):
    frappe.only_for(("System Manager", "Accounts Manager"))
    si = frappe.get_doc("Sales Invoice", si_name)
    if si.docstatus != 1:
        return {"ok": False, "log": [f"{si_name} is not Submitted (docstatus={si.docstatus})."]}

    report: List[str] = []
    _cancel_doc("Sales Invoice", si_name, report, set())
    return {"ok": True, "log": report}