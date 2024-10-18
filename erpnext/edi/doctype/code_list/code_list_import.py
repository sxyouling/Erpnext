import json

import frappe
import requests
from frappe import _
from frappe.utils.file_manager import save_file
from lxml import etree

URL_PREFIXES = ("http://", "https://")


@frappe.whitelist()
def import_genericode():
	doctype = frappe.form_dict.doctype
	docname = frappe.form_dict.docname
	content = frappe.local.uploaded_file

	# recover the content, if it's a link
	if (file_url := frappe.local.uploaded_file_url) and file_url.startswith(URL_PREFIXES):
		try:
			# If it's a URL, fetch the content and make it a local file (for durable audit)
			response = requests.get(frappe.local.uploaded_file_url)
			response.raise_for_status()
			frappe.local.uploaded_file = content = response.content
			frappe.local.uploaded_filename = frappe.local.uploaded_file_url.split("/")[-1]
			frappe.local.uploaded_file_url = None
		except Exception as e:
			frappe.throw(f"<pre>{e!s}</pre>", title=_("Fetching Error"))

	if file_url := frappe.local.uploaded_file_url:
		file_path = frappe.utils.file_manager.get_file_path(file_url)
		with open(file_path.encode(), mode="rb") as f:
			content = f.read()

	# Parse the xml content
	parser = etree.XMLParser(remove_blank_text=True)
	try:
		root = etree.fromstring(content, parser=parser)
	except Exception as e:
		frappe.throw(f"<pre>{e!s}</pre>", title=_("Parsing Error"))

	# Extract the name (CanonicalVersionUri) from the parsed XML
	name = root.find(".//CanonicalVersionUri").text

	if docname:
		code_list = frappe.get_doc(doctype, docname)
		if code_list.name != name:
			frappe.throw(_("The uploaded file does not match the selected Code List."))
	else:
		# Create a new Code List document with the extracted name
		code_list = frappe.new_doc(doctype)
		code_list.name = name
		code_list.insert(ignore_permissions=True)

	# Attach the file and provide a recoverable identifier
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": "Code List",
			"attached_to_name": code_list.name,
			"folder": "Home/Attachments",
			"file_name": frappe.local.uploaded_filename,
			"file_url": frappe.local.uploaded_file_url,
			"is_private": 1,
			"content": content,
		}
	).save(ignore_permissions=True)

	# Get available columns and example values
	columns, example_values, filterable_columns = get_genericode_columns_and_examples(root)

	return {
		"code_list": code_list.name,
		"file": file_doc.name,
		"columns": columns,
		"example_values": example_values,
		"filterable_columns": filterable_columns,
	}


@frappe.whitelist()
def process_genericode_import(
	code_list_name, file, code_column, title_column=None, description_column=None, filters=None
):
	code_list = frappe.get_doc("Code List", code_list_name)
	return code_list.import_genericode(
		file, code_column, title_column, description_column, filters and json.loads(filters)
	)


def get_genericode_columns_and_examples(root):
	columns = []
	example_values = {}
	filterable_columns = {}

	# Get column names
	for column in root.findall(".//Column"):
		column_id = column.get("Id")
		columns.append(column_id)
		example_values[column_id] = []
		filterable_columns[column_id] = set()

	# Get all values and count unique occurrences
	for row in root.findall(".//SimpleCodeList/Row"):
		for value in row.findall("Value"):
			column_id = value.get("ColumnRef")
			if column_id not in columns:
				# Handle undeclared column
				columns.append(column_id)
				example_values[column_id] = []
				filterable_columns[column_id] = set()

			value_text = value.find("./SimpleValue").text
			filterable_columns[column_id].add(value_text)

	# Get example values (up to 3) and filter columns with cardinality <= 5
	for row in root.findall(".//SimpleCodeList/Row")[:3]:
		for value in row.findall("Value"):
			column_id = value.get("ColumnRef")
			example_values[column_id].append(value.find("./SimpleValue").text)

	filterable_columns = {k: list(v) for k, v in filterable_columns.items() if len(v) <= 5}

	return columns, example_values, filterable_columns
