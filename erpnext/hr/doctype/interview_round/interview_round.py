# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json

from frappe.model.document import Document

class InterviewRound(Document):
	pass

@frappe.whitelist()
def create_interview(doc):
	if isinstance(doc, str):
		doc = json.loads(doc)
		doc = frappe.get_doc(doc)

	interview = frappe.new_doc("Interview")
	interview.interview_round = doc.name
	interview.designation = doc.designation

	if doc.interviewer:
		interview.interview_detail = []
		for data in doc.interviewer:
			interview.append("interview_detail", {
					"interviewer": data.user
				})
	return interview



