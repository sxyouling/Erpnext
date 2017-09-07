// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Variant Settings', {
	setup: function(frm) {
		const allow_fields = [];
		const exclude_fields = ["item_code", "item_name", "show_in_website", "show_variant_in_website", "standard_rate"];

		frappe.model.with_doctype('Item', () => {
			frappe.get_meta('Item').fields.forEach(d => {
				if(!in_list(['HTML', 'Section Break', 'Column Break', 'Button'], d.fieldtype)
					&& !d.no_copy && !in_list(exclude_fields, d.fieldname)) {
					allow_fields.push(d.fieldname);
				}
			});

			const child = frappe.meta.get_docfield("Variant Field", "field_name", frm.doc.name);
			child.options = allow_fields;
		});
	}
});
