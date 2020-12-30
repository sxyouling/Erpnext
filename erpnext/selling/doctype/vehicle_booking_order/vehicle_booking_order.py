# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import cint, flt, getdate, today
from frappe.model.utils import get_fetch_values
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from erpnext.accounts.party import set_contact_details, get_party_account
from erpnext.stock.get_item_details import get_item_warehouse, get_item_price, get_default_supplier
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_source.item_source import get_item_source_defaults
from erpnext.accounts.doctype.transaction_type.transaction_type import get_transaction_type_defaults
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.vehicles.doctype.vehicle_withholding_tax_rule.vehicle_withholding_tax_rule import get_withholding_tax_amount
from six import string_types
import json

force_fields = ['customer_name', 'item_name', 'item_group', 'brand', 'address_display',
	'contact_display', 'contact_email', 'contact_mobile', 'contact_phone', 'withholding_tax_amount']

force_if_not_empty_fields = ['selling_transaction_type', 'buying_transaction_type',
	'receivable_account', 'payable_account']

class VehicleBookingOrder(AccountsController):
	def validate(self):
		if self.get("_action") != "update_after_submit":
			self.set_missing_values(for_validate=True)

		self.ensure_supplier_is_not_blocked()
		self.validate_date_with_fiscal_year()

		self.validate_customer()
		self.validate_vehicle_item()
		self.validate_vehicle()
		self.validate_party_accounts()

		self.set_title()
		self.clean_remarks()

		self.calculate_taxes_and_totals()
		self.validate_amounts()
		self.validate_taxes_and_charges_accounts()
		self.set_total_in_words()

		self.validate_payment_schedule()

		self.update_payment_status()
		self.update_delivery_status()
		self.update_invoice_status()
		self.set_status()

	def before_submit(self):
		if not self.vehicle:
			frappe.throw(_("Please create or set a Vehicle document before submitting"))

	def on_submit(self):
		self.set_status()

	def on_cancel(self):
		self.set_status()

	def onload(self):
		self.set_vehicle_details()

	def before_print(self):
		self.set_vehicle_details()

	def set_title(self):
		self.title = self.company if self.customer_is_company else self.customer_name

	def validate_customer(self):
		if not self.customer and not self.customer_is_company:
			frappe.throw(_("Customer is mandatory"))

		if self.customer:
			self.validate_party()

	def validate_vehicle_item(self):
		item = frappe.get_cached_doc("Item", self.item_code)
		validate_vehicle_item(item)

	def validate_vehicle(self):
		if self.vehicle:
			vehicle_item_code = frappe.db.get_value("Vehicle", self.vehicle, "item_code")
			if vehicle_item_code != self.item_code:
				frappe.throw(_("Vehicle {0} is not {1}").format(self.vehicle, self.item_name or self.item_code))

			existing_booking = frappe.get_all("Vehicle Booking Order", filters={"docstatus": 1, "vehicle": self.vehicle})
			existing_booking = existing_booking[0].name if existing_booking else None
			if existing_booking:
				frappe.throw(_("Cannot select Vehicle {0} because it is already ordered in {1}")
					.format(self.vehicle, existing_booking))

	def set_missing_values(self, for_validate=False):
		customer_details = get_customer_details(self.as_dict(), get_withholding_tax=False)
		for k, v in customer_details.items():
			if not self.get(k) or k in force_fields or (v and k in force_if_not_empty_fields):
				self.set(k, v)

		item_details = get_item_details(self.as_dict())
		for k, v in item_details.items():
			if not self.get(k) or k in force_fields or (v and k in force_if_not_empty_fields):
				self.set(k, v)

		self.set_vehicle_details()

	def set_vehicle_details(self, update=False):
		if self.vehicle:
			values = get_fetch_values(self.doctype, "vehicle", self.vehicle)
			if update:
				self.db_set(values)
			else:
				for k, v in values.items():
					self.set(k, v)

	def calculate_taxes_and_totals(self):
		self.round_floats_in(self, ['vehicle_amount', 'fni_amount', 'withholding_tax_amount'])

		self.invoice_total = flt(self.vehicle_amount + self.fni_amount + self.withholding_tax_amount,
			self.precision('invoice_total'))

		if self.docstatus == 0:
			self.customer_advance = 0
			self.supplier_advance = 0
			self.customer_outstanding = self.invoice_total
			self.supplier_outstanding = self.invoice_total

	def validate_amounts(self):
		for field in ['vehicle_amount', 'invoice_total']:
			self.validate_value(field, '>', 0)
		for field in ['fni_amount', 'registration_amount', 'margin_amount', 'discount_amount']:
			self.validate_value(field, '>=', 0)

	def set_total_in_words(self):
		from frappe.utils import money_in_words
		self.in_words = money_in_words(self.invoice_total, self.company_currency)

	def validate_payment_schedule(self):
		self.validate_payment_schedule_dates()
		self.set_due_date()
		self.set_payment_schedule()
		self.validate_payment_schedule_amount()
		self.validate_due_date()

	def validate_party_accounts(self):
		company_currency = erpnext.get_company_currency(self.company)
		receivable_currency, receivable_type = frappe.db.get_value('Account', self.receivable_account, ['account_currency', 'account_type'])
		payable_currency, payable_type = frappe.db.get_value('Account', self.payable_account, ['account_currency', 'account_type'])

		if company_currency != receivable_currency:
			frappe.throw(_("Receivable account currency should be same as company currency {0}")
				.format(company_currency))
		if company_currency != payable_currency:
			frappe.throw(_("Payable account currency should be same as company currency {0}")
				.format(company_currency))
		if receivable_type != 'Receivable':
			frappe.throw(_("Receivable Account must be of type Receivable"))
		if payable_type != 'Payable':
			frappe.throw(_("Payable Account must be of type Payable"))

	def validate_taxes_and_charges_accounts(self):
		if self.fni_amount and not self.fni_account:
			frappe.throw(_("Freight and Insurance Amount is set but account is not provided"))
		if self.withholding_tax_amount and not self.withholding_tax_account:
			frappe.throw(_("Withholding Tax Amount is set but account is not provided"))

	def update_payment_status(self, update=False):
		self.customer_outstanding = flt(self.invoice_total - self.customer_advance, self.precision('customer_outstanding'))
		self.supplier_outstanding = flt(self.invoice_total - self.supplier_advance, self.precision('supplier_outstanding'))

		if self.customer_outstanding < 0:
			frappe.throw(_("Customer Advance Received cannot be greater than the Invoice Total"))
		if self.supplier_outstanding < 0:
			frappe.throw(_("Supplier Advance Paid cannot be greater than the Invoice Total"))

		if self.customer_outstanding > 0:
			if getdate(today()) > getdate(self.due_date):
				self.customer_payment_status = "Overdue"
			elif self.customer_advance == 0:
				self.customer_payment_status = "Unpaid"
			else:
				self.customer_payment_status = "Partially Paid"
		else:
			self.customer_payment_status = "Paid"

		if self.supplier_outstanding > 0:
			if getdate(today()) > getdate(self.due_date):
				self.supplier_payment_status = "Overdue"
			elif self.supplier_advance == 0:
				self.supplier_payment_status = "Unpaid"
			else:
				self.supplier_payment_status = "Partially Paid"
		else:
			self.supplier_payment_status = "Paid"

		if update:
			self.db_set({
				'customer_outstanding': self.customer_outstanding,
				'supplier_outstanding': self.supplier_outstanding,
				'customer_payment_status': self.customer_payment_status,
				'supplier_payment_status': self.supplier_payment_status,
			})

	def update_delivery_status(self, update=False):
		purchase_receipt = None
		delivery_note = None

		if self.docstatus != 0:
			purchase_receipt = frappe.db.get_all("Purchase Receipt", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date', 'supplier_delivery_note'])
			delivery_note = frappe.db.get_all("Delivery Note", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date'])

			if len(purchase_receipt) > 1:
				frappe.throw(_("Purchase Receipt already exists against Vehicle Booking Order"))
			if len(delivery_note) > 1:
				frappe.throw(_("Delivery Note already exists against Vehicle Booking Order"))

		purchase_receipt = purchase_receipt[0] if purchase_receipt else frappe._dict()
		delivery_note = delivery_note[0] if delivery_note else frappe._dict()

		if purchase_receipt and not purchase_receipt.supplier_delivery_note:
			frappe.throw(_("Supplier Delivery Note is mandatory for Purchase receipt against Vehicle Booking Order"))

		self.vehicle_received_date = purchase_receipt.posting_date
		self.vehicle_delivered_date = delivery_note.posting_date
		self.supplier_delivery_note = purchase_receipt.supplier_delivery_note

		if not purchase_receipt:
			self.delivery_status = "To Receive"
		elif not delivery_note:
			self.delivery_status = "To Deliver"
		else:
			self.delivery_status = "Delivered"

		if update:
			self.db_set({
				"vehicle_received_date": self.vehicle_received_date,
				"vehicle_delivered_date": self.vehicle_delivered_date,
				"supplier_delivery_note": self.supplier_delivery_note,
				"delivery_status": self.delivery_status
			})

	def update_invoice_status(self, update=False):
		purchase_invoice = None
		sales_invoice = None

		if self.docstatus != 0:
			purchase_invoice = frappe.db.get_all("Purchase Invoice", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date', 'bill_no', 'bill_date'])
			sales_invoice = frappe.db.get_all("Sales Invoice", {"vehicle_booking_order": self.name, "docstatus": 1},
				['name', 'posting_date'])

			if len(purchase_invoice) > 1:
				frappe.throw(_("Purchase Invoice already exists against Vehicle Booking Order"))
			if len(sales_invoice) > 1:
				frappe.throw(_("Sales Invoice already exists against Vehicle Booking Order"))

			if sales_invoice and not purchase_invoice:
				frappe.throw(_("Cannot make Sales Invoice against Vehicle Booking Order before making Purchase Invoice"))

		purchase_invoice = purchase_invoice[0] if purchase_invoice else frappe._dict()
		sales_invoice = sales_invoice[0] if sales_invoice else frappe._dict()

		if purchase_invoice and (not purchase_invoice.bill_no or not purchase_invoice.bill_date):
			frappe.throw(_("Supplier Invoice No and Supplier Invoice Date is mandatory for Purchase Invoice against Vehicle Booking Order"))

		self.invoice_received_date = purchase_invoice.posting_date
		self.invoice_delivered_date = sales_invoice.posting_date
		self.bill_no = purchase_invoice.bill_no
		self.bill_date = purchase_invoice.bill_date

		if not purchase_invoice:
			self.invoice_status = "To Receive"
		elif not sales_invoice:
			self.invoice_status = "To Deliver"
		else:
			self.invoice_status = "Delivered"

		if update:
			self.db_set({
				"invoice_received_date": self.invoice_received_date,
				"invoice_delivered_date": self.invoice_delivered_date,
				"bill_no": self.bill_no,
				"bill_date": self.bill_date,
				"invoice_status": self.invoice_status
			})

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		previous_status = self.status

		if self.docstatus == 2:
			self.status = "Cancelled"

		elif self.docstatus == 1:
			if self.customer_outstanding > 0 or self.supplier_outstanding > 0:
				if self.customer_advance > self.supplier_advance:
					self.status = "To Deposit Payment"
				else:
					self.status = "To Receive Payment"

			elif self.delivery_status == "To Receive":
				self.status = "To Receive Vehicle"

			elif self.invoice_status == "To Receive":
				self.status = "To Receive Invoice"

			elif self.delivery_status == "To Deliver":
				self.status = "To Deliver Vehicle"

			elif self.invoice_status == "To Deliver":
				self.status = "To Deliver Invoice"

			else:
				self.status = "Completed"

		else:
			self.status = "Draft"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified=update_modified)


@frappe.whitelist()
def get_customer_details(args, get_withholding_tax=True):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	args.customer_is_company = cint(args.customer_is_company)

	if not args.company:
		frappe.throw(_("Company is mandatory"))
	if not args.customer and not args.customer_is_company:
		frappe.throw(_("Customer is mandatory"))

	out = frappe._dict()

	if args.customer_is_company:
		out.customer = None
		out.customer_name = args.company

	party_type = "Company" if args.customer_is_company else "Customer"
	party_name = args.company if args.customer_is_company else args.customer
	party = frappe.get_cached_doc(party_type, party_name)

	if party_type == "Customer":
		out.customer_name = party.customer_name

	out.tax_id = party.get('tax_id')
	out.tax_cnic = party.get('tax_cnic')
	out.tax_strn = party.get('tax_strn')
	out.tax_status = party.get('tax_status')
	out.tax_overseas_cnic = party.get('tax_overseas_cnic')
	out.passport_no = party.get('passport_no')

	out.customer_address = args.customer_address or get_default_address(party_type, party_name)
	out.address_display = get_address_display(out.customer_address) if out.customer_address else None

	set_contact_details(out, party, party_type)

	vehicles_settings = frappe.get_cached_doc("Vehicles Settings", None)

	out.selling_transaction_type = vehicles_settings.selling_transaction_type_company if args.customer_is_company \
		else vehicles_settings.selling_transaction_type_customer
	out.buying_transaction_type = vehicles_settings.buying_transaction_type_company if args.customer_is_company \
		else vehicles_settings.buying_transaction_type_customer

	out.receivable_account = get_party_account("Customer", None if args.customer_is_company else args.customer,
		args.company, transaction_type=out.selling_transaction_type)
	out.payable_account = get_party_account("Supplier", args.supplier,
		args.company, transaction_type=out.buying_transaction_type)

	selling_vehicle_booking_defaults = get_transaction_type_defaults(out.selling_transaction_type, args.company,
		fieldname='vehicle_booking_defaults')
	buying_vehicle_booking_defaults = get_transaction_type_defaults(out.buying_transaction_type, args.company,
		fieldname='vehicle_booking_defaults')

	out.fni_account = buying_vehicle_booking_defaults.get('fni_account') or selling_vehicle_booking_defaults.get('fni_account')
	out.withholding_tax_account = buying_vehicle_booking_defaults.get('withholding_tax_account') or \
		selling_vehicle_booking_defaults.get('withholding_tax_account')

	if get_withholding_tax and args.item_code:
		out.withholding_tax_amount = get_withholding_tax_amount(args.transaction_date, args.item_code, out.tax_status, args.company)
	return out


@frappe.whitelist()
def get_item_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.company:
		frappe.throw(_("Company is mandatory"))
	if not args.item_code:
		frappe.throw(_("Vehicle Item Code is mandatory"))

	out = frappe._dict()

	item = frappe.get_cached_doc("Item", args.item_code)
	validate_vehicle_item(item)

	out.item_name = item.item_name
	out.item_group = item.item_group
	out.brand = item.brand

	item_defaults = get_item_defaults(item.name, args.company)
	item_group_defaults = get_item_group_defaults(item.name, args.company)
	brand_defaults = get_brand_defaults(item.name, args.company)
	item_source_defaults = get_item_source_defaults(item.name, args.company)
	transaction_type = args.buying_transaction_type or args.selling_transaction_type
	transaction_type_defaults = get_transaction_type_defaults(transaction_type, args.company)

	if not args.supplier:
		out.supplier = get_default_supplier(args, item_defaults, item_group_defaults, brand_defaults, item_source_defaults,
			transaction_type_defaults)

	out.warehouse = get_item_warehouse(item, args, overwrite_warehouse=True, item_defaults=item_defaults, item_group_defaults=item_group_defaults,
		brand_defaults=brand_defaults, item_source_defaults=item_source_defaults, transaction_type_defaults=transaction_type_defaults)

	out.vehicle_price_list = get_default_price_list(item, args, item_defaults=item_defaults, item_group_defaults=item_group_defaults,
		brand_defaults=brand_defaults, item_source_defaults=item_source_defaults, transaction_type_defaults=transaction_type_defaults)

	fni_price_list_settings = frappe.get_cached_value("Vehicles Settings", None, "fni_price_list")
	if fni_price_list_settings:
		out.fni_price_list = fni_price_list_settings

	if args.customer:
		args.tax_status = frappe.get_cached_value("Customer", args.customer, "tax_status")
	if out.vehicle_price_list:
		out.update(get_vehicle_price(item.name, out.vehicle_price_list, out.fni_price_list, args.transaction_date, args.tax_status, args.company))

	return out


@frappe.whitelist()
def get_vehicle_default_supplier(item_code, company):
	if not company:
		frappe.throw(_("Company is mandatory"))
	if not item_code:
		frappe.throw(_("Vehicle Item Code is mandatory"))

	item = frappe.get_cached_doc("Item", item_code)

	item_defaults = get_item_defaults(item.name, company)
	item_group_defaults = get_item_group_defaults(item.name, company)
	brand_defaults = get_brand_defaults(item.name, company)
	item_source_defaults = get_item_source_defaults(item.name, company)

	default_supplier = get_default_supplier(frappe._dict({"item_code": item_code, "company": company}),
		item_defaults, item_group_defaults, brand_defaults, item_source_defaults, {})

	return default_supplier


def get_vehicle_price(item_code, vehicle_price_list, fni_price_list, transaction_date, tax_status, company):
	if not item_code:
		frappe.throw(_("Vehicle Item Code is mandatory"))
	if not vehicle_price_list:
		frappe.throw(_("Vehicle Price List is mandatory for Vehicle Price"))

	transaction_date = getdate(transaction_date)
	item = frappe.get_cached_doc("Item", item_code)

	out = frappe._dict()
	vehicle_price_args = {
		"price_list": vehicle_price_list,
		"transaction_date": transaction_date,
		"uom": item.stock_uom
	}

	vehicle_item_price = get_item_price(vehicle_price_args, item_code, ignore_party=True)
	vehicle_item_price = vehicle_item_price[0][1] if vehicle_item_price else 0
	out.vehicle_amount = flt(vehicle_item_price)

	out.withholding_tax_amount = get_withholding_tax_amount(transaction_date, item_code, tax_status, company)

	if fni_price_list:
		fni_price_args = vehicle_price_args.copy()
		fni_price_args['price_list'] = fni_price_list
		fni_item_price = get_item_price(fni_price_args, item_code, ignore_party=True)
		fni_item_price = fni_item_price[0][1] if fni_item_price else 0
		out.fni_amount = flt(fni_item_price)
	else:
		out.fni_amount = 0

	return out


def get_default_price_list(item, args, item_defaults, item_group_defaults, brand_defaults, item_source_defaults,
			transaction_type_defaults):
		price_list = (transaction_type_defaults.get('default_price_list')
			or item_defaults.get('default_price_list')
			or item_source_defaults.get('default_price_list')
			or brand_defaults.get('default_price_list')
			or item_group_defaults.get('default_price_list')
			or args.get('price_list')
		)

		if not price_list:
			price_list = frappe.get_cached_value("Vehicles Settings", None, "vehicle_price_list")
		if not price_list:
			price_list = frappe.get_cached_value("Buying Settings", None, "buying_price_list")
		if not price_list:
			price_list = frappe.get_cached_value("Selling Settings", None, "selling_price_list")

		return price_list


def validate_vehicle_item(item):
	from erpnext.stock.doctype.item.item import validate_end_of_life
	validate_end_of_life(item.name, item.end_of_life, item.disabled)

	if not item.is_vehicle:
		frappe.throw(_("{0} is not a Vehicle Item").format(item.item_name or item.name))
	if not item.include_in_vehicle_booking:
		frappe.throw(_("Vehicle Item {0} is not allowed for Vehicle Booking").format(item.item_name or item.name))


@frappe.whitelist()
def get_next_document(vehicle_booking_order, doctype):
	doc = frappe.get_doc("Vehicle Booking Order", vehicle_booking_order)

	if doc.docstatus != 1:
		frappe.throw(_("Vehicle Booking Order must be submitted"))

	if doctype == "Purchase Receipt":
		return get_purchase_receipt(doc)
	elif doctype == "Purchase Invoice":
		return get_purchase_invoice(doc)
	elif doctype == "Delivery Note":
		return get_delivery_note(doc)
	elif doctype == "Sales Invoice":
		return get_sales_invoice(doc)
	else:
		frappe.throw(_("Invalid DocType"))


def get_purchase_receipt(source):
	check_if_doc_exists("Purchase Receipt", source.name)

	target = frappe.new_doc("Purchase Receipt")

	vehicle_item = set_next_document_values(source, target, 'buying')
	prev_doc, prev_vehicle_item = get_previous_doc("Purchase Order", source)

	if prev_vehicle_item:
		vehicle_item.purchase_order = prev_vehicle_item.parent
		vehicle_item.purchase_order_item = prev_vehicle_item.name

	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")
	return target


def get_purchase_invoice(source):
	check_if_doc_exists("Purchase Invoice", source.name)

	target = frappe.new_doc("Purchase Invoice")

	vehicle_item = set_next_document_values(source, target, 'buying')
	prev_doc, prev_vehicle_item = get_previous_doc("Purchase Receipt", source)

	if not prev_doc:
		frappe.throw(_("Cannot make Purchase Invoice against Vehicle Booking Order before making Purchase Receipt"))

	if prev_vehicle_item:
		vehicle_item.purchase_receipt = prev_vehicle_item.parent
		vehicle_item.pr_detail = prev_vehicle_item.name

	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")
	return target


def get_delivery_note(source):
	check_if_doc_exists("Delivery Note", source.name)

	target = frappe.new_doc("Delivery Note")
	set_next_document_values(source, target, 'selling')
	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")
	return target


def get_sales_invoice(source):
	check_if_doc_exists("Sales Invoice", source.name)

	target = frappe.new_doc("Sales Invoice")

	vehicle_item = set_next_document_values(source, target, 'selling')
	prev_doc, prev_vehicle_item = get_previous_doc("Delivery Note", source)

	if not prev_doc:
		frappe.throw(_("Cannot make Sales Invoice against Vehicle Booking Order before making Delivery Note"))

	if prev_vehicle_item:
		vehicle_item.delivery_note = prev_vehicle_item.parent
		vehicle_item.dn_detail = prev_vehicle_item.name

	target.run_method("set_missing_values")
	target.run_method("calculate_taxes_and_totals")
	return target


def check_if_doc_exists(doctype, vehicle_booking_order):
	existing = frappe.db.get_value(doctype, {"vehicle_booking_order": vehicle_booking_order, "docstatus": ["<", 2]})
	if existing:
		frappe.throw(_("{0} already exists").format(frappe.get_desk_link(doctype, existing)))


def get_previous_doc(doctype, source):
	prev_docname = frappe.db.get_value(doctype, {"vehicle_booking_order": source.name, "docstatus": 1})
	if not prev_docname:
		return None, None

	prev_doc = frappe.get_doc(doctype, prev_docname)

	vehicle_item = prev_doc.get('items', filters={'item_code': source.item_code})
	vehicle_item = vehicle_item[0] if vehicle_item else None

	if not vehicle_item:
		frappe.throw(_("{0} {1} does not have Vehicle Item {2}").format(doctype, prev_docname, source.item_name or source.item_code))

	return prev_doc, vehicle_item


def set_next_document_values(source, target, buying_or_selling):
	target.vehicle_booking_order = source.name
	target.company = source.company
	target.ignore_pricing_rule = 1

	if buying_or_selling == "buying":
		target.supplier = source.supplier
		target.transaction_type = source.buying_transaction_type
		target.buying_price_list = source.vehicle_price_list
	else:
		target.customer = source.customer
		target.transaction_type = source.selling_transaction_type
		target.selling_price_list = source.vehicle_price_list
		target.customer_address = source.customer_address
		target.contact_person = source.contact_person

		for d in source.sales_team:
			target.append('sales_team', {
				'sales_person': d.sales_person, 'allocated_percentage': d.allocated_percentage
			})

	if target.meta.has_field('debit_to'):
		target.debit_to = source.receivable_account
	if target.meta.has_field('credit_to'):
		target.debit_to = source.payable_account

	vehicle_item = target.append('items')
	vehicle_item.item_code = source.item_code
	vehicle_item.qty = 1
	vehicle_item.vehicle = source.vehicle
	vehicle_item.price_list_rate = source.vehicle_amount
	vehicle_item.rate = source.vehicle_amount
	vehicle_item.discount_percentage = 0

	if source.fni_amount:
		add_taxes_and_charges_row(target, source.fni_account, source.fni_amount)
	if source.withholding_tax_amount:
		add_taxes_and_charges_row(target, source.withholding_tax_account, source.withholding_tax_amount)

	return vehicle_item


def add_taxes_and_charges_row(target, account, amount):
	row = target.append('taxes')

	row.charge_type = 'Actual'
	row.account_head = account
	row.tax_amount = amount

	if row.meta.has_field('category'):
		row.category = 'Valuation and Total'

	if row.meta.has_field('add_deduct_tax'):
		row.add_deduct_tax = 'Add'
