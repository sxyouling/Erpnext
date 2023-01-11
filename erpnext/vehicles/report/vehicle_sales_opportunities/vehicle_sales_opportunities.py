# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, today
from dateutil.relativedelta import relativedelta
from frappe.contacts.doctype.contact.contact import get_default_contact


def execute(filters=None):
	return VehicleSalesOpportunities(filters).run()


class VehicleSalesOpportunities:
	def __init__(self, filters=None):
		# self.filters = frappe._dict(filters or {})
		# self.filters.from_date = getdate(filters.from_date or today())
		# self.filters.to_date = getdate(filters.to_date or today())

		# if self.filters.from_date > self.filters.to_date:
		# 	frappe.throw(_("Date Range is incorrect"))
		pass

	def run(self):
		self.get_data()
		self.process_data()
		self.get_columns()
		return self.columns, self.data

	def get_data(self):
		self.get_opportunity_data()
		self.get_existing_vehicles_map()
		self.get_lost_reason_map()
		self.get_communication_map()

	def get_opportunity_data(self):
		self.data = frappe.db.sql("""
			SELECT
				opp.name AS opportunity, opp.opportunity_from, opp.party_name, opp.customer_name,
				opp.sales_person, opp.lead_classification, opp.transaction_date, opp.status,
				opp.source, opp.information_source, order_lost_reason,
				opp.contact_mobile, opp.contact_phone,
				opp.applies_to_variant_of_name AS variant_interested_in, first_additional,
				rating_interior, rating_exterior, rating_specifications, rating_price,
				liked_features, remarks,
				address.city AS address_city, lead.city AS lead_city,
				vbo.name AS vehicle_booking_order,
				opp.delivery_period AS opp_delivery_month, vbo.delivery_period AS vbo_delivery_month
			FROM `tabOpportunity` opp
			LEFT JOIN `tabLead` lead ON lead.name = opp.party_name AND opp.opportunity_from = 'Lead'
			LEFT JOIN `tabAddress` address ON address.name = opp.customer_address
			LEFT JOIN `tabVehicle Booking Order` vbo ON vbo.opportunity = opp.name
			WHERE opp.opportunity_type = "Sales"
		""", as_dict=1)

		self.opportunities = [d.opportunity for d in self.data]

	def get_existing_vehicles_map(self):
		existing_vehicles_data = []
		if self.opportunities:
			existing_vehicles_data = frappe.db.sql("""
				SELECT parent AS opportunity, item_name
				FROM `tabLead Existing Item`
				WHERE parenttype = 'Opportunity' AND parent IN %s
			""", [self.opportunities], as_dict=1)

		self.existing_vehicles_map = {}
		for d in existing_vehicles_data:
			self.existing_vehicles_map.setdefault(d.opportunity, []).append(d)

	def get_lost_reason_map(self):
		lost_reason_data = []
		if self.opportunities:
			lost_reason_data = frappe.db.sql("""
				SELECT parent AS opportunity, lost_reason
				FROM `tabLost Reason Detail`
				WHERE parenttype = 'Opportunity' AND parent IN %s
			""", [self.opportunities], as_dict=1)

		self.lost_reason_map = {}
		for d in lost_reason_data:
			self.lost_reason_map.setdefault(d.opportunity, []).append(d)

	def get_communication_map(self):
		communication_data = []
		if self.opportunities:
			communication_data = frappe.db.sql("""
				SELECT reference_name AS opportunity, content
				FROM `tabCommunication`
				WHERE reference_doctype = 'Opportunity' AND reference_name IN %s
					AND sent_or_received = 'Received'
			""", [self.opportunities], as_dict=1, debug=1)

		self.communication_map = {}
		for d in communication_data:
			self.communication_map.setdefault(d.opportunity, []).append(d)

	def process_data(self):
		self.no_of_communications = 1
		for d in self.data:
			d.disable_item_formatter = 1
			d.contact_no = d.contact_mobile or d.contact_phone
			d.city = d.address_city or d.lead_city

			d.sales_done = "Yes" if d.vehicle_booking_order else "No"
			d.delivery_month = d.vbo_delivery_month or d.opp_delivery_month
			

			existing_vehicles = self.existing_vehicles_map.get(d.opportunity) or []
			for i in range(len(existing_vehicles)):
				d["existing_vehicle_" + str(i+1)] = existing_vehicles[i].get('item_name')

			communications = self.communication_map.get(d.opportunity) or []
			self.no_of_communications = max(self.no_of_communications, len(communications))
			for i in range(len(communications)):
				d["comm_" + str(i+1)] = communications[i].get('content')

			if d.status == "Lost":
				if d.order_lost_reason:
					d.lost_reason = d.order_lost_reason
				else:
					lost_reason_list = self.lost_reason_map.get(d.opportunity) or []
					d.lost_reason = ', '.join(map(lambda x:x.get('item_name'), lost_reason_list))

	def get_columns(self):
		columns = [
			{
				"label": _("Opportunity"),
				"fieldname": "opportunity",
				"fieldtype": "Link",
				"options": "Opportunity",
				"width": 110
			},
			{
				"label": _("Opportunity Date"),
				"fieldname": "transaction_date",
				"fieldtype": "Date",
				"width": 130
			},
			{
				"label": _("Sales Person"),
				"fieldname": "sales_person",
				"fieldtype": "Data",
				"width": 120
			},
			{
				"label": _("Source of Lead"),
				"fieldname": "source",
				"fieldtype": "Data",
				"width": 110
			},
			{
				"label": _("Party"),
				"fieldname": "party_name",
				"fieldtype": "Dynamic Link",
				"options": "opportunity_from",
				"width": 100
			},
			{
				"label": _("Customer Name"),
				"fieldname": "customer_name",
				"fieldtype": "Data",
				"width": 140
			},
			{
				"label": _("Contact"),
				"fieldname": "contact_no",
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("City"),
				"fieldname": "city",
				"fieldtype": "Data",
				"width": 80
			},
		]

		for i in range(2):
			columns += [{
				"label": _("Existing Vehicle # " + str(i+1)),
				"fieldname": "existing_vehicle_" + str(i+1),
				"fieldtype": "Data",
				"width": 135
		}]

		columns += [
			{
				"label": _("Variant Interested In"),
				"fieldname": "variant_interested_in",
				"fieldtype": "Data",
				"width": 145
			},
			{
				"label": _("Source of Information"),
				"fieldname": "information_source",
				"fieldtype": "Data",
				"width": 160
			},
			{
				"label": _("1st/Additional/Replacement"),
				"fieldname": "first_additional",
				"fieldtype": "Data",
				"width": 190
			},
			{
				"label": _("Interior"),
				"fieldname": "rating_interior",
				"fieldtype": "Int",
				"width": 70
			},
			{
				"label": _("Exterior"),
				"fieldname": "rating_exterior",
				"fieldtype": "Int",
				"width": 70
			},
			{
				"label": _("Specs"),
				"fieldname": "rating_specifications",
				"fieldtype": "Int",
				"width": 70
			},
			{
				"label": _("Price"),
				"fieldname": "rating_price",
				"fieldtype": "Int",
				"width": 70
			},
			{
				"label": _("Key Features You Like"),
				"fieldname": "liked_features",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Feedback Remark"),
				"fieldname": "remarks",
				"fieldtype": "Data",
				"width": 130
			},
			{
				"label": _("Hot/Warm/Cold"),
				"fieldname": "lead_classification",
				"fieldtype": "Data",
				"width": 120
			},
			{
				"label": _("Sales Done"),
				"fieldname": "sales_done",
				"fieldtype": "Data",
				"width": 00
			},
			{
				"label": _("PBO"),
				"fieldname": "vehicle_booking_order",
				"fieldtype": "Link",
				"options": "Vehicle Booking Order",
				"width": 120
			},
			{
				"label": _("Delivery Month"),
				"fieldname": "delivery_month",
				"fieldtype": "Data",
				"width": 110
			},
			{
				"label": _("Lost Reason"),
				"fieldname": "lost_reason",
				"fieldtype": "Data",
				"width": 120
			},
		]

		for i in range(self.no_of_communications):
			columns += [{
				"label": _("Comm " + str(i+1)),
				"fieldname": "comm_" + str(i+1),
				"fieldtype": "Data",
				"width": 120
			}]

		self.columns = columns
