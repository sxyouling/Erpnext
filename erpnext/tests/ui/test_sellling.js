QUnit.module("sales");

QUnit.test("test: lead", function (assert) {
	assert.expect(1);
	let done = assert.async();
	let random = frappe.utils.get_random(10);
	frappe.run_serially([
		() => frappe.tests.setup_doctype("Lead"),
		() => frappe.set_route("List", "Lead"),
		() => frappe.new_doc("Lead"),
		() => cur_frm.set_value("lead_name", random),
		() => cur_frm.save(),
		() => {
			assert.ok(cur_frm.doc.lead_name.includes(random));
			return done();
		}
	]);
});

QUnit.test("test: opportunity", function (assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make("Opportunity", [{
				enquiry_from: "Lead"
			},
			{
				lead: "LEAD-00002"
			}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.lead === "LEAD-00002");
			return done();
		}
	]);
});

QUnit.only("test: quotation", function (assert) {
	assert.expect(10);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.tests.setup_doctype("Customer"),
		() => frappe.tests.setup_doctype("Item"),
		() => frappe.tests.setup_doctype("Address"),
		() => frappe.tests.setup_doctype("Contact"),
		() => frappe.tests.setup_doctype("Price List"),
		() => frappe.tests.setup_doctype("Terms and Conditions"),
		() => {
			return frappe.tests.make("Quotation", [{
				customer: "Test Customer 1"
			},
			{
				items: [
					[{
						"item_code": "Test Product 1"
					},
					{
						"qty": 5
					}
					]
				]
			}
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name == "Test Product 1", "Added Test Product 1");

			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.grand_total == 500, "Total Amount is correct");
		},
		() => cur_frm.set_value("customer_address", "Test1-Billing"),
		() => cur_frm.set_value("shipping_address_name", "Test1-Warehouse"),
		() => cur_frm.set_value("contact_person", "Contact 1-Test Customer 1"),
		() => cur_frm.set_value("currency", "USD"),
		() => frappe.timeout(0.3),
		() => cur_frm.set_value("selling_price_list", "Test-Selling-USD"),
		() => frappe.timeout(0.3),
		() => cur_frm.doc.items[0].rate = 200,
		() => frappe.timeout(0.3),
		() => cur_frm.set_value("terms", "Test Term 1"),
		() => cur_frm.save(),
		() => {
			// Check Address
			assert.ok(cur_frm.doc.address_display.includes("Billing Street 1"), "Address Changed");
			assert.ok(cur_frm.doc.shipping_address.includes("Warehouse Street 1"), "Address Changed");
			assert.ok(cur_frm.doc.contact_display == "Contact 1", "Contact info changed");
			assert.ok(cur_frm.doc_currency == "USD", "Currency Changed");
			assert.ok(cur_frm.doc.selling_price_list == "Test-Selling-USD", "Price List Changed");
			assert.ok(cur_frm.doc.items[0].rate == 200, "Price Changed Manually");
			assert.ok(cur_frm.doc.total == 1000, "New Total Calculated");
			assert.ok(cur_frm.doc.terms == "Test Term 1", "Terms and Conditions Checked");
		},
		() => done()
	]);
});