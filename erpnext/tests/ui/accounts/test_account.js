QUnit.module('accounts');

QUnit.only("test account", function(assert) {
	assert.expect(4);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route('Tree', 'Account'),
		() => frappe.tests.click_button('Expand All'),
		() => frappe.tests.click_link('Debtors'),
		() => frappe.tests.click_button('Edit'),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_frm.doc.root_type=='Asset');
			assert.ok(cur_frm.doc.report_type=='Balance Sheet');
			assert.ok(cur_frm.doc.account_type=='Receivable');
		},
		() => frappe.tests.click_button('Ledger'),
		() => frappe.timeout(1),
		() => {
			// check if general ledger report shown
			assert.deepEqual(frappe.get_route(), ['query-report', 'General Ledger']);
			window.history.back();
			return frappe.timeout(1);
		},
		() => done()
	]);
});
