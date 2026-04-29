# Copyright (c) 2026, Hussain and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, flt
from erpnext.accounts.utils import get_balance_on
from frappe.utils import today, flt


class PaymentClearingReconciliationEntry(Document):
	def validate(self):
		self.total_amount = sum((row.amount or 0) for row in (self.payment_clearing_accounts or []))

		if abs(self.gross_amount_as_per_pos) != abs(self.net_amount):
			frappe.throw("POS Gross Amount must be equal to Net Amount")

	def _sum_child_debits(self, doc):
		total = 0.0
		for row in (doc.payment_clearing_accounts or []):
			if row.accounts and flt(row.amount) > 0:
				total += flt(row.amount)
		return total

	def on_submit(self):

		"""Create & submit a Journal Entry on submit of parent doc.
		Credits the clearing_account with gross; debits each child account with its amount.
		"""
		# ensure we have a full doc object (method may pass a dict during testing)
		doc = self
		if isinstance(doc, dict):
			doc = frappe.get_doc(doc.get("doctype"), doc.get("name"))

		if not doc.company:
			frappe.throw("Company is required.")
		if not doc.clearing_account:
			frappe.throw("Clearing Account is required.")
		if not doc.payment_clearing_accounts:
			frappe.throw("At least one line is required.")

		# totals
		child_total = self._sum_child_debits(doc)
		gross = flt(doc.gross_amount_as_per_pos) or child_total

		if child_total <= 0:
			frappe.throw("Child debit total must be greater than zero.")

		# If gross not provided, force it = child_total for a perfect balance
		# If provided and differs slightly, we trust 'gross' and let credit = gross
		posting_date = doc.posting_date or today()

		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": doc.company,
			"posting_date": posting_date,
			"user_remark": f"Auto-created from {doc.doctype} {doc.name}",
			"accounts": []
		})

		# add debit lines from child table
		for row in doc.payment_clearing_accounts:
			amt = flt(row.amount)
			if not row.accounts or amt <= 0:
				continue
			je.append("accounts", {
				"account": row.accounts,
				"debit_in_account_currency": amt,
				"cost_center": getattr(row, "cost_center", None),
				# Optional: link back to the source for traceability
			})

		# add credit line to clearing account
		je.append("accounts", {
			"account": doc.clearing_account,
			"credit_in_account_currency": gross,
		})

		# final sanity: totals must match
		total_debit = sum(flt(a.debit_in_account_currency) for a in je.accounts)
		total_credit = sum(flt(a.credit_in_account_currency) for a in je.accounts)

		# If there’s tiny rounding difference, push it into the clearing line
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency") or 2
		diff = round(total_debit - total_credit, precision)
		if diff != 0:
			# adjust credit line (clearing)
			clearing_row = next((a for a in je.accounts if a.account == doc.clearing_account and a.credit_in_account_currency), None)
			if clearing_row:
				clearing_row.credit_in_account_currency = flt(clearing_row.credit_in_account_currency) + diff
				total_credit = sum(flt(a.credit_in_account_currency) for a in je.accounts)

		if round(total_debit, precision) != round(total_credit, precision):
			frappe.throw(f"Journal not balanced (Dr {total_debit} vs Cr {total_credit}). Check amounts.")

		# create & submit
		je.insert(ignore_permissions=True)
		je.submit()

		self.journal_entry_status = 'Created'
		self.journal_entry = je.name

		# store link back on the parent (add a Link field 'journal_entry' on your parent doctype)
		if hasattr(doc, "journal_entry"):
			frappe.db.set_value(doc.doctype, doc.name, "journal_entry", je.name)

	def on_cancel(doc, method=None):
		"""Cancel the linked Journal Entry when parent is cancelled."""
		if isinstance(doc, dict):
			doc = frappe.get_doc(doc.get("doctype"), doc.get("name"))

		je_name = getattr(doc, "journal_entry", None)
		if not je_name:
			# try to find by reference if field not present
			jelist = frappe.get_all(
				"Journal Entry Account",
				filters={"reference_type": doc.doctype, "reference_name": doc.name, "docstatus": 1},
				fields=["parent"],
				distinct=True,
			)
			if not jelist:
				return
			je_name = jelist[0].parent

		try:
			je = frappe.get_doc("Journal Entry", je_name)
			if je.docstatus == 1:
				je.cancel()
		except frappe.DoesNotExistError:
			pass
	

@frappe.whitelist()
def get_account_balances(account: str, from_date: str = None, to_date: str = None, company: str = None):
	
	"""Return opening (as of day before from_date), period debit/credit, and closing (as of to_date)."""
	if not (account and from_date and to_date):
		frappe.throw("Please select Account, From Date and To Date")

	# company fallback from Account master if not given
	if not company:
		company = frappe.db.get_value("Account", account, "company")

	# opening = balance just before from_date
	opening = flt(get_balance_on(
		account=account,
		date=add_days(from_date, -1),
		company=company
	))

	# closing = balance as of to_date
	closing = flt(get_balance_on(
		account=account,
		date=to_date,
		company=company
	))

	# period movement (sum of GL)
	row = frappe.db.get_all(
		"GL Entry",
		filters={
			"account": account,
			"company": company,
			"is_cancelled": 0,
			"posting_date": ["between", [from_date, to_date]],
		},
		fields=["sum(debit) as debit", "sum(credit) as credit"],
		limit=1,
	)
	debit = flt(row[0].debit) if row else 0.0
	credit = flt(row[0].credit) if row else 0.0

	return {
		"opening": opening,
		"debit": debit,
		"credit": credit,
		"closing": closing,
	}