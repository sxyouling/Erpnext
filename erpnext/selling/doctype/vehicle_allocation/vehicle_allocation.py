# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document
from six import string_types

class VehicleAllocation(Document):
	def validate(self):
		self.validate_vehicle_item()
		self.validate_duplicate()
		self.validate_period()
		self.set_title()

	def set_title(self):
		self.title = get_allocation_title(self)

	def validate_vehicle_item(self):
		from erpnext.selling.doctype.vehicle_booking_order.vehicle_booking_order import validate_vehicle_item

		item = frappe.get_cached_doc("Item", self.item_code)
		validate_vehicle_item(item)
		if not item.vehicle_allocation_required:
			frappe.throw(_("{0} does not require Vehicle Allocations").format(item.item_name or item.name))

	def validate_period(self):
		allocation_from_date = frappe.get_cached_value("Vehicle Allocation Period", self.allocation_period, "from_date")
		delivery_from_date = frappe.get_cached_value("Vehicle Allocation Period", self.delivery_period, "from_date")

		if getdate(delivery_from_date) < getdate(allocation_from_date):
			frappe.throw(_("Delivery Period {0} cannot be before Allocation Period {1}")
				.format(frappe.bold(self.delivery_period), frappe.bold(self.allocation_period)))

	def validate_duplicate(self):
		filters = {
			"item_code": self.item_code,
			"supplier": self.supplier,
			"allocation_period": self.allocation_period,
			"sr_no": self.sr_no,
			"code": self.code,
			"is_additional": self.is_additional,
			"docstatus": 1
		}
		if not self.is_new():
			filters['name'] = ['!=', self.name]

		duplicates = frappe.get_all("Vehicle Allocation", filters=filters,
			fields=['name', 'code', 'sr_no', 'allocation_period', 'is_additional'], limit=1)

		if duplicates:
			frappe.throw(_("Vehicle Allocation already exists for period {0}: {1}{2}")
				.format(self.allocation_period, get_allocation_title(self), " (Additional Allocation)" if self.is_additional else ""))


@frappe.whitelist()
def get_allocation_title(vehicle_allocation):
	if isinstance(vehicle_allocation, string_types):
		vehicle_allocation = frappe.db.get_value("Vehicle Allocation", vehicle_allocation, ['code', 'sr_no'], as_dict=1)

	return "{0} - {1}".format(vehicle_allocation.sr_no, vehicle_allocation.code)
