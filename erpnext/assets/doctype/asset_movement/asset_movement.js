// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Movement', {
	setup: (frm) => {
		frm.set_query("to_employee", "assets", (doc) => {
			return {
				filters: {
					company: doc.company
				}
			};
		})
		frm.set_query("from_employee", "assets", (doc) => {
			return {
				filters: {
					company: doc.company
				}
			};
		})
		frm.set_query("reference_name", (doc) => {
			return {
				filters: {
					company: doc.company,
					docstatus: 1
				}
			};
		})
		frm.set_query("reference_doctype", () => {
			return {
				filters: {
					name: ["in", ["Purchase Receipt", "Purchase Invoice"]]
				}
			};
		})
	},

	onload: (frm) => {
		frm.trigger('set_required_fields');
	},

	purpose: (frm) => {
		frm.trigger('set_required_fields');
	},

	set_required_fields: (frm, cdt, cdn) => {
		let fieldnames_to_be_altered;
		if (frm.doc.purpose === 'Transfer') {
			fieldnames_to_be_altered = {
				target_location: { read_only: 0, reqd: 1 },
				source_location: { read_only: 1, reqd: 1 },
				from_employee: { read_only: 1, reqd: 0 },
				to_employee: { read_only: 1, reqd: 0 }
			};
		}
		else if (frm.doc.purpose === 'Receipt') {
			fieldnames_to_be_altered = {
				target_location: { read_only: 0, reqd: 1 },
				source_location: { read_only: 1, reqd: 0 },
				from_employee: { read_only: 0, reqd: 1 },
				to_employee: { read_only: 1, reqd: 0 }
			};
		}
		else if (frm.doc.purpose === 'Issue') {
			fieldnames_to_be_altered = {
				target_location: { read_only: 1, reqd: 0 },
				source_location: { read_only: 1, reqd: 1 },
				from_employee: { read_only: 1, reqd: 0 },
				to_employee: { read_only: 0, reqd: 1 }
			};
		}
		Object.keys(fieldnames_to_be_altered).forEach(fieldname => {
			let property_to_be_altered = fieldnames_to_be_altered[fieldname];
			Object.keys(property_to_be_altered).forEach(property => {
				let value = property_to_be_altered[property];
				frm.set_df_property(fieldname, property, value, cdn, 'assets');
			});
		});
		frm.refresh_field('assets');
	},

	reference_name: function(frm) {
		if (frm.doc.reference_name && frm.doc.reference_doctype) {
			const reference_doctype = frm.doc.reference_doctype === 'Purchase Invoice' ? 'purchase_invoice' : 'purchase_receipt';
			// On selection of reference name,
			// sets query to display assets linked to that reference doc
			frm.set_query('asset', 'assets', function() {
				return {
					filters: {
						[reference_doctype] : frm.doc.reference_name
					}
				};
			});

			// fetches linked asset & adds to the assets table
			frappe.db.get_list('Asset', {
				fields: ['name', 'location', 'custodian'],
				filters: {
					[reference_doctype] : frm.doc.reference_name
				}
			}).then((docs) => {
				if (docs.length == 0) {
					frappe.msgprint(frappe._(`Please select ${frm.doc.reference_doctype} which has assets.`));
					frm.doc.reference_name = '';
					frm.refresh_field('reference_name');
					return;
				}
				frm.doc.assets = [];
				docs.forEach(doc => {
					frm.add_child('assets', {
						asset: doc.name,
						source_location: doc.location,
						from_employee: doc.custodian
					});
					frm.refresh_field('assets');
				})
			}).catch((err) => {
				console.log(err); // eslint-disable-line
			});
		} else {
			// if reference is deleted then remove query
			frm.set_query('asset', 'assets', () => ({ filters: {} }));
		}
	}
});

frappe.ui.form.on('Asset Movement Item', {
	asset: function(frm, cdt, cdn) {
		// on manual entry of an asset auto sets their source location / employee
		const asset_name = locals[cdt][cdn].asset;
		if (asset_name){
			frappe.db.get_doc('Asset', asset_name).then((asset_doc) => {
				if(asset_doc.location) frappe.model.set_value(cdt, cdn, 'source_location', asset_doc.location);
				if(asset_doc.custodian) frappe.model.set_value(cdt, cdn, 'from_employee', asset_doc.custodian);
			}).catch((err) => {
				console.log(err); // eslint-disable-line
			});
		}
	}
});