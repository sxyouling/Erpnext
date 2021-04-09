# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import cint
import frappe
from frappe.model.document import Document

class TransactionsCleanup(Document):
	def before_save(self):
		# prepopulating the 'Additional DocTypes' table if it's not empty
		if not self.doctypes:
			doctypes = frappe.get_all('Doctype',
				filters={
					'issingle' : 0,
					'istable' : 0
				})
			
			for doctype in doctypes:
				doctype_obj = frappe.get_doc('DocType', doctype.name)
				doctype_dict = doctype_obj.as_dict()
				doctype_fields = doctype_dict['fields']
				for doctype_field in doctype_fields:
					if doctype_field['fieldname'] == "company":
						self.append('doctypes',{
							"doctype_name" : doctype.name,
						})
						break
		
	def on_submit(self):
		for doctype in self.doctypes or self.customisable_doctypes:
			frappe.db.delete(doctype.doctype_name, {
				'company' : self.company
			})

			naming_series = frappe.db.get_value('DocType', doctype.doctype_name, 'autoname')
			if naming_series:
				if '#' in naming_series:
					self.update_naming_series(naming_series, doctype.doctype_name)

	def update_naming_series(self, naming_series, doctype_name):
		if '.' in naming_series:
			prefix, hashes = naming_series.rsplit(".", 1)
		else:
			prefix, hashes = naming_series.rsplit("{", 1)
		last = frappe.db.sql("""select max(name) from `tab{0}`
						where name like %s""".format(doctype_name), prefix + "%")
		if last and last[0][0]:
			last = cint(last[0][0].replace(prefix, ""))
		else:
			last = 0

		frappe.db.sql("""update tabSeries set current = %s where name=%s""", (last, prefix))