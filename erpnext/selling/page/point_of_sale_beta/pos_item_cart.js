erpnext.PointOfSale.ItemCart = class {
    constructor({ wrapper, events }) {
		this.wrapper = wrapper;
		this.events = events;
        this.customer_info = undefined;
        
        this.intialize_component();
    }
    
    intialize_component() {
        this.prepare_dom();
        this.initialize_child_components();
		this.bind_events();
    }

    prepare_dom() {
		this.wrapper.append(
            `<section class="col-span-4 flex flex-col shadow rounded item-cart bg-white mx-h-70 h-100"></section>`
        )

        this.$component = this.wrapper.find('.item-cart');
    }

    initialize_child_components() {
        this.initialize_customer_selector();
        this.initialize_cart_components();
    }

    initialize_customer_selector() {
		this.$component.append(
            `<div class="customer-section rounded border flex flex-col m-8 mb-0 pr-4 pl-4"></div>`
        )
		this.$customer_section = this.$component.find('.customer-section');
	}
	
	reset_customer_selector() {
		const frm = this.events.get_frm();
		frm.set_value('customer', '');
		this.$customer_section.removeClass('border pr-4 pl-4');
		this.show_customer_selector();
		this.customer_field.set_focus();
	}
    
    initialize_cart_components() {
        this.$component.append(
            `<div class="cart-container flex flex-col items-center p-8 pt-0 rounded flex-1">
                <div class="flex text-grey cart-header pt-2 pb-2 p-4 mt-2 mb-2 w-full">
                    <div class="ml-2 mr-6">Qty</div>
                    <div class="flex-1">Item</div>
                    <div class="ml-auto mr-1">Rate</div>
                </div>
                <div class="cart-items-section flex flex-col rounded border border-grey w-full"></div>
                <div class="cart-totals-section flex flex-col mt-auto border border-grey rounded w-full"></div>
                <div class="numpad-section flex flex-col mt-auto d-none w-full p-8 pt-0 pb-0"></div>
            </div>`
        );
		this.$cart_container = this.$component.find('.cart-container');

		this.make_cart_totals_section();
		this.make_cart_items_section();
        this.make_cart_numpad();
    }

    make_cart_items_section() {
        this.$cart_header = this.$component.find('.cart-header');
        this.$cart_items_wrapper = this.$component.find('.cart-items-section');

		this.make_no_items_placeholder();
    }
    
    make_no_items_placeholder() {
		this.$cart_header.addClass('d-none');
		this.$cart_items_wrapper.html(
			`<div class="no-item-wrapper flex items-center h-18">
				<div class="flex-1 text-center text-grey">No items in cart</div>
			</div>`
		)
		this.$cart_items_wrapper.removeClass('border border-grey').addClass('mt-4 border-grey border-dashed');
	}

    make_cart_totals_section() {
        this.$totals_section = this.$component.find('.cart-totals-section');

		this.$totals_section.append(
			`<div>
				<div class="net-total flex justify-between items-center h-16 pr-8 pl-8 border-b-grey">
					<div class="flex flex-col">
						<div class="text-md text-dark-grey text-bold">Net Total</div>
					</div>
					<div class="flex flex-col text-right">
						<div class="text-md text-dark-grey text-bold">0.00</div>
					</div>
				</div>
				<div class="taxes"></div>
				<div class="grand-total flex justify-between items-center h-16 pr-8 pl-8 border-b-grey">
					<div class="flex flex-col">
						<div class="text-md text-dark-grey text-bold">Grand Total</div>
					</div>
					<div class="flex flex-col text-right">
						<div class="text-md text-dark-grey text-bold">0.00</div>
					</div>
				</div>
				<div class="checkout-btn flex items-center justify-center h-16 pr-8 pl-8 text-center text-grey no-select pointer rounded-b text-md text-bold">
					Checkout
				</div>
				<div class="edit-cart-btn flex items-center justify-center h-16 pr-8 pl-8 text-center text-grey no-select pointer d-none text-md text-bold">
					Edit Cart
				</div>
			</div>`
		)
    }
    
    make_cart_numpad() {
		this.$numpad_section = this.$component.find('.numpad-section');

		this.number_pad = new erpnext.PointOfSale.NumberPad({
			wrapper: this.$numpad_section,
			events: {
				numpad_event: this.on_numpad_event.bind(this)
			},
			cols: 5,
			keys: [
				[ 1, 2, 3, 'Quantity' ],
				[ 4, 5, 6, 'Discount' ],
				[ 7, 8, 9, 'Rate' ],
				[ '.', 0, 'Delete', 'Remove' ]
			],
			css_classes: [
				[ '', '', '', 'col-span-2' ],
				[ '', '', '', 'col-span-2' ],
				[ '', '', '', 'col-span-2' ],
				[ '', '', '', 'col-span-2 text-danger' ]
			],
			fieldnames_map: { 'Quantity': 'qty', 'Discount': 'discount_percentage' }
		})

		this.$numpad_section.prepend(
			`<div class="flex mb-2 justify-between">
				<span class="numpad-net-total"></span>
				<span class="numpad-grand-total"></span>
			</div>`
		)

		this.$numpad_section.append(
			`<div class="numpad-btn flex items-center justify-center h-16 text-center text-md no-select pointer 
				rounded bg-primary text-white text-bold mt-4" data-button-value="done">
				Done
			</div>`
		)
    }
    
    bind_events() {
		const me = this;
		this.$customer_section.on('click', '.add-remove-customer', function (e) {
			const customer_info_is_visible = me.$cart_container.hasClass('d-none');
			if (customer_info_is_visible) {
				me.toggle_customer_info(false);
			} else {
				me.reset_customer_selector();
			}
		});

		this.$customer_section.on('click', '.customer-header', function(e) {
			// don't run the event if .add-remove-customer btn is clicked which is under .customer-header
			if ($(e.target).closest('.add-remove-customer').length) return;

			const show = !me.$cart_container.hasClass('d-none');
			me.toggle_customer_info(show);
		});

		this.$cart_items_wrapper.on('click', '.cart-item-wrapper', function() {
			const $cart_item = $(this);
			const edit_cart_btn = me.$totals_section.find('.edit-cart-btn');

			if (!edit_cart_btn.hasClass('d-none')) {
				// payment section is visible
				// edit cart then open item details section
				edit_cart_btn.click();
			}

			const item_code = unescape($cart_item.attr('data-item-code'));
			const batch_no = unescape($cart_item.attr('data-batch-no'));
			me.events.cart_item_clicked(item_code, batch_no);
		});

		this.$totals_section.on('click', '.checkout-btn', () => {
			this.events.checkout();
			this.toggle_checkout_btn(false);
		});

		this.$totals_section.on('click', '.edit-cart-btn', () => {
			this.events.edit_cart();
			this.toggle_checkout_btn(true);
		});
    }
    
    show_customer_selector() {
        this.$customer_section.html(`<div class="customer-search-field flex flex-1 items-center"></div>`);
        
		const me = this;
		this.customer_field = frappe.ui.form.make_control({
			df: {
				label: __('Customer'),
				fieldtype: 'Link',
				options: 'Customer',
				placeholder: __('Search by customer name, phone, email.'),
				onchange: function() {
					if (this.value) {
						const frm = me.events.get_frm();
						frappe.dom.freeze();
						frappe.model.set_value(frm.doc.doctype, frm.doc.name, 'customer', this.value);
						frm.script_manager.trigger('customer', frm.doc.doctype, frm.doc.name).then(() => {
							frappe.run_serially([
								() => me.fetch_customer_details(this.value),
								() => me.update_customer_section(frm),
								() => me.update_totals_section(frm),
								() => frappe.dom.unfreeze()
							]);
						})
					}
				},
			},
			parent: this.$customer_section.find('.customer-search-field'),
			render_input: true,
		});
		this.customer_field.toggle_label(false);
	}
	
	fetch_customer_details(customer) {
		return new Promise((resolve) => {
			frappe.db.get_value('Customer', customer, ["email_id", "mobile_no", "image", "loyalty_program"]).then(({ message }) => {
				const { loyalty_program } = message;
				if (loyalty_program) {
					frappe.call({
						method: "erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_program_details_with_points",
						args: { customer, loyalty_program, "silent": true },
						callback: (r) => {
							const { loyalty_points } = r.message;
							if (!r.exc) {
								this.customer_info = { ...message, customer, loyalty_points };
								resolve();
							}
						}
					});
				} else {
					this.customer_info = { ...message, customer };
					resolve();
				}
			});
		});
	}
    
    update_customer_section(frm) {
		const { customer, email_id='', mobile_no='', image } = this.customer_info || {};

		function get_customer_description() {
			if (!email_id && !mobile_no) {
				return `<div class="text-grey-200 italic">Click to add email / phone</div>`
			} else if (email_id && !mobile_no) {
				return `<div class="text-grey">${email_id}</div>`
			} else if (mobile_no && !email_id) {
				return `<div class="text-grey">${mobile_no}</div>`
			} else {
				return `<div class="text-grey">${email_id} | ${mobile_no}</div>`
			}
		}

		function get_customer_image() {
			if (image) {
				return `<div class="icon flex items-center justify-center w-12 h-12 rounded bg-light-grey mr-4 text-grey-200">
							<img class="h-full" src="${image}" alt="${image}" style="object-fit: cover;">
						</div>`
			} else {
				return `<div class="icon flex items-center justify-center w-12 h-12 rounded bg-light-grey mr-4 text-grey-200">
							${frappe.get_abbr(customer)}
						</div>`
			}
		}

		if (customer) {
			this.$customer_section.addClass('border pr-4 pl-4').html(
				`<div class="customer-details flex flex-col">
					<div class="customer-header flex items-center rounded h-18">
						${get_customer_image()}
						<div class="customer-name flex flex-col flex-1">
							<div class="text-md text-dark-grey text-bold">${customer}</div>
							${get_customer_description()}
						</div>
						<div class="add-remove-customer flex items-center" data-customer="${escape(customer)}">
							<svg width="32" height="32" viewBox="0 0 14 14" fill="none">
								<path d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759" stroke="#8D99A6"/>
							</svg>
						</div>
					</div>
				</div>`
			);
		} else {
            // reset customer selector
			this.reset_customer_selector();
		}
    }
    
    update_totals_section(frm) {
		this.render_net_total(frm.doc.base_net_total);
		this.render_grand_total(frm.doc.base_grand_total);

		const taxes = frm.doc.taxes.map(t => { return { description: t.description, rate: t.rate }})
		this.render_taxes(frm.doc.base_total_taxes_and_charges, taxes);
    }
    
    render_net_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section.find('.net-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Net Total</div>
			</div>
			<div class="flex flex-col text-right">
				<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
			</div>`
		)

		this.$numpad_section.find('.numpad-net-total').html(`Net Total: <span class="text-bold">${format_currency(value, currency)}</span>`)
    }
    
    render_grand_total(value) {
		const currency = this.events.get_frm().doc.currency;
		this.$totals_section.find('.grand-total').html(
			`<div class="flex flex-col">
				<div class="text-md text-dark-grey text-bold">Grand Total</div>
			</div>
			<div class="flex flex-col text-right">
				<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
			</div>`
		)

		this.$numpad_section.find('.numpad-grand-total').html(`Grand Total: <span class="text-bold">${format_currency(value, currency)}</span>`)
	}

	render_taxes(value, taxes) {
		if (taxes.length) {
			const currency = this.events.get_frm().doc.currency;
			this.$totals_section.find('.taxes').html(
				`<div class="flex items-center justify-between h-16 pr-8 pl-8 border-b-grey">
					<div class="flex">
						<div class="text-md text-dark-grey text-bold w-fit">Tax Charges</div>
						<div class="flex ml-6 text-dark-grey">
						${	
							taxes.map((t, i) => {
								let margin_left = '';
								if (i !== 0) margin_left = 'ml-2';
								return `<span class="border-grey p-1 pl-2 pr-2 rounded ${margin_left}">${t.description} @${t.rate}%</span>`
							}).join('')
						}
						</div>
					</div>
					<div class="flex flex-col text-right">
						<div class="text-md text-dark-grey text-bold">${format_currency(value, currency)}</div>
					</div>
				</div>`
			)
		} else {
			this.$totals_section.find('.taxes').html('')
		}
    }

    get_cart_item({ item_code, batch_no }) {
        const item_selector = batch_no ? 
            `.cart-item-wrapper[data-batch-no="${escape(batch_no)}"]` : `.cart-item-wrapper[data-item-code="${escape(item_code)}"]`;
            
        return this.$cart_items_wrapper.find(item_selector);
    }
    
    update_item_html(item, remove_item) {
		const $item = this.get_cart_item(item);

		if (remove_item) {
			$item && $item.remove();
		} else {
			const { item_code, batch_no } = item;
			const search_field = batch_no ? 'batch_no' : 'item_code';
			const search_value = batch_no || item_code;
			const item_row = this.events.get_frm().doc.items.find(i => i[search_field] === search_value);
			
			this.render_cart_item(item_row, $item);
		}

		const no_of_cart_items = this.$cart_items_wrapper.children().length;
		no_of_cart_items > 0 && this.highlight_checkout_btn(no_of_cart_items > 0);
        
		this.update_empty_cart_section(no_of_cart_items);
	}
    
    render_cart_item(item_data, $item_to_update) {
		const currency = this.events.get_frm().doc.currency;
		
        if (!$item_to_update.length) {
            this.$cart_items_wrapper.append(
                `<div class="cart-item-wrapper flex items-center h-18 pr-4 pl-4 border-b-grey pointer no-select" 
                        data-item-code="${escape(item_data.item_code)}" data-batch-no="${escape(item_data.batch_no || '')}">
                </div>`
            )
            $item_to_update = this.get_cart_item(item_data);
        }

		$item_to_update.html(
			`<div class="flex w-10 h-10 rounded bg-light-grey mr-4 items-center justify-center font-bold f-shrink-0">
                <span>${item_data.qty || 0}</span>
            </div>
            <div class="flex flex-col f-shrink-1">
                <div class="text-md text-dark-grey text-bold overflow-hidden whitespace-nowrap">
                    ${item_data.item_name}
                </div>
                ${get_description_html()}
            </div>
            <div class="flex flex-col f-shrink-0 ml-auto text-right">
                ${get_rate_discount_html()}
            </div>`
        )
        
		function get_rate_discount_html() {
			if (item_data.rate && item_data.price_list_rate && item_data.rate !== item_data.price_list_rate) {
				return `<div class="text-md text-dark-grey text-bold">${format_currency(item_data.rate, currency)}</div>
						<div class="text-grey line-through">${format_currency(item_data.price_list_rate, currency)}</div>`
			} else {
				return `<div class="text-md text-dark-grey text-bold">${format_currency(item_data.price_list_rate || item_data.rate, currency)}</div>`
			}
		}

		function get_description_html() {
			if (item_data.description) {
				item_data.description.indexOf('<div>') != -1 && (item_data.description = $(item_data.description).text());
				item_data.description = frappe.ellipsis(item_data.description, 45);
				return `<div class="text-grey overflow-hidden whitespace-nowrap">${item_data.description}</div>`
			}
			return ``;
		}
	}
	
	update_batch_in_cart_item(batch_no, item) {
		const $item_to_update = this.get_cart_item(item);
		$item_to_update.attr('data-batch-no', batch_no);
	}

    toggle_checkout_btn(show_checkout) {
		if (show_checkout) {
			this.$totals_section.find('.checkout-btn').removeClass('d-none');
			this.$totals_section.find('.edit-cart-btn').addClass('d-none');
		} else {
			this.$totals_section.find('.checkout-btn').addClass('d-none');
			this.$totals_section.find('.edit-cart-btn').removeClass('d-none');
		}
	}

    highlight_checkout_btn(toggle) {
		const has_primary_class = this.$totals_section.find('.checkout-btn').hasClass('bg-primary');
		if (toggle && !has_primary_class) {
			this.$totals_section.find('.checkout-btn').addClass('bg-primary text-white text-lg');
		} else if (!toggle && has_primary_class) {
			this.$totals_section.find('.checkout-btn').removeClass('bg-primary text-white text-lg');
		}
	}
    
    update_empty_cart_section(no_of_cart_items) {
		const $no_item_element = this.$cart_items_wrapper.find('.no-item-wrapper');

		// if cart has items and no item is present
		no_of_cart_items > 0 && $no_item_element && $no_item_element.remove()
			&& this.$cart_items_wrapper.removeClass('mt-4 border-grey border-dashed').addClass('border border-grey') && this.$cart_header.removeClass('d-none');

		no_of_cart_items === 0 && !$no_item_element.length && this.make_no_items_placeholder();
    }
    
    on_numpad_event($btn) {
		const current_action = $btn.attr('data-button-value');
		const action_is_field_edit = ['qty', 'discount_percentage', 'rate'].includes(current_action);

		this.highlight_numpad_btn($btn, current_action);

        const action_is_pressed_twice = this.prev_action === current_action;
        const first_click_event = !this.prev_action;
        const field_to_edit_changed = this.prev_action && this.prev_action != current_action;

		if (action_is_field_edit) {

			if (first_click_event || field_to_edit_changed) {
                this.prev_action = current_action;
			} else if (action_is_pressed_twice) {
				this.prev_action = undefined;
			}
            this.numpad_value = '';
            
		} else if (current_action === 'done') {
			this.prev_action = undefined;
			this.events.numpad_event(undefined, current_action);
			return;
		} else if (current_action === 'remove') {
			this.prev_action = undefined;
			this.events.numpad_event(undefined, current_action);
			return;
		} else {
			this.numpad_value = current_action === 'delete' ? this.numpad_value.slice(0, -1) : this.numpad_value + current_action;
			this.numpad_value = this.numpad_value || 0;
		}

        const first_click_event_is_not_field_edit = !action_is_field_edit && first_click_event;

		if (first_click_event_is_not_field_edit) {
			frappe.show_alert({
				indicator: 'red',
				message: __('Please select a field to edit from numpad')
			});
			return;
		}
		
		if (flt(this.numpad_value) > 100 && this.prev_action === 'discount_percentage') {
			frappe.show_alert({
				message: __('Discount cannot be greater than 100%'),
				indicator: 'orange'
			});
			this.numpad_value = current_action;
		}

        this.events.numpad_event(this.numpad_value, this.prev_action);
    }
    
    highlight_numpad_btn($btn, curr_action) {
        const curr_action_is_highlighted = $btn.hasClass('shadow-inner');
        const curr_action_is_action = ['qty', 'discount_percentage', 'rate', 'done'].includes(curr_action);

        if (!curr_action_is_highlighted) {
            $btn.addClass('shadow-inner bg-selected');
        }
        if (this.prev_action === curr_action && curr_action_is_highlighted) {
            // if Qty is pressed twice
            $btn.removeClass('shadow-inner bg-selected');
        }
        if (this.prev_action && this.prev_action !== curr_action && curr_action_is_action) {
            // Order: Qty -> Rate then remove Qty highlight
            const prev_btn = $(`[data-button-value='${this.prev_action}']`);
            prev_btn.removeClass('shadow-inner bg-selected');
        }
        if (!curr_action_is_action || curr_action === 'done') {
            // if numbers are clicked
            setTimeout(() => {
                $btn.removeClass('shadow-inner bg-selected');
            }, 100);
        }
    }

    toggle_numpad(show) {
		if (show) {
			this.$totals_section.addClass('d-none');
			this.$numpad_section.removeClass('d-none');
		} else {
			this.$totals_section.removeClass('d-none');
			this.$numpad_section.addClass('d-none');
		}
	}

	toggle_numpad_field_edit(fieldname) {
		if (['qty', 'discount_percentage', 'rate'].includes(fieldname)) {
			this.$numpad_section.find(`[data-button-value="${fieldname}"]`).click();
		}
	}

	toggle_customer_info(show) {
		if (show) {
			this.$cart_container.addClass('d-none')
			this.$customer_section.addClass('flex-1 scroll').removeClass('mb-0 border pr-4 pl-4')
			this.$customer_section.find('.icon').addClass('w-24 h-24').removeClass('w-12 h-12')
			this.$customer_section.find('.customer-header').removeClass('h-18');
			this.$customer_section.find('.customer-details').addClass('sticky z-100 bg-white');

			this.$customer_section.find('.customer-name').html(
				`<div class="text-md text-dark-grey text-bold">${this.customer_info.customer}</div>
				<div class="last-transacted-on text-grey-200"></div>`
			)
	
			this.$customer_section.find('.customer-details').append(
				`<div class="customer-form">
					<div class="text-grey mt-4 mb-6">CONTACT DETAILS</div>
					<div class="grid grid-cols-2 gap-4">
						<div class="email_id-field"></div>
						<div class="mobile_no-field"></div>
						<div class="loyalty_program-field"></div>
						<div class="loyalty_points-field"></div>
					</div>
					<div class="text-grey mt-4 mb-6">RECENT TRANSACTIONS</div>
				</div>`
			)
			// transactions need to be in diff div from sticky elem for scrolling
			this.$customer_section.append(`<div class="customer-transactions flex-1 border rounded"></div>`)

			this.render_customer_info_form();
			this.fetch_customer_transactions();

		} else {
			this.$cart_container.removeClass('d-none');
			this.$customer_section.removeClass('flex-1 scroll').addClass('mb-0 border pr-4 pl-4');
			this.$customer_section.find('.icon').addClass('w-12 h-12').removeClass('w-24 h-24');
			this.$customer_section.find('.customer-header').addClass('h-18')
			this.$customer_section.find('.customer-details').removeClass('sticky z-100 bg-white');

			this.update_customer_section();
		}
	}

	render_customer_info_form() {
		const $customer_form = this.$customer_section.find('.customer-form');

		const dfs = [{
			fieldname: 'email_id',
			label: __('Email'),
			fieldtype: 'Data',
			options: 'email',
			placeholder: __("Enter customer's email")
		},{
			fieldname: 'mobile_no',
			label: __('Phone Number'),
			fieldtype: 'Data',
			placeholder: __("Enter customer's phone number")
		},{
			fieldname: 'loyalty_program',
			label: __('Loyalty Program'),
			fieldtype: 'Link',
			options: 'Loyalty Program',
			placeholder: __("Select Loyalty Program")
		},{
			fieldname: 'loyalty_points',
			label: __('Loyalty Points'),
			fieldtype: 'Int',
			read_only: 1
		}];

		const me = this;
		dfs.forEach(df => {
			this[`customer_${df.fieldname}_field`] = frappe.ui.form.make_control({
				df: { ...df,
					onchange: handle_customer_field_change,
				},
				parent: $customer_form.find(`.${df.fieldname}-field`),
				render_input: true,
			});
			this[`customer_${df.fieldname}_field`].set_value(this.customer_info[df.fieldname]);
		})

		function handle_customer_field_change() {
			const current_value = me.customer_info[this.df.fieldname];
			const current_customer = me.customer_info.customer;

			if (this.value && current_value != this.value && this.df.fieldname != 'loyalty_points') {
				frappe.call({
					method: 'erpnext.selling.page.point_of_sale.point_of_sale.set_customer_info',
					args: {
						fieldname: this.df.fieldname,
						customer: current_customer,
						value: this.value
					},
					callback: (r) => {
						if(!r.exc) {
							me.customer_info[this.df.fieldname] = this.value;
							frappe.show_alert({
								message: __("Customer contact updated successfully."),
								indicator: 'green'
							})
						}
					}
				});
			}
		}
	}

	fetch_customer_transactions() {
		frappe.db.get_list('POS Invoice', { 
			filters: { customer: this.customer_info.customer, docstatus: 1 },
			fields: ['name', 'grand_total', 'status', 'posting_date', 'posting_time', 'currency'],
			limit: 20
		}).then((res) => {
			const transaction_container = this.$customer_section.find('.customer-transactions');

			if (!res.length) {
				transaction_container.removeClass('flex-1 border rounded').html(
					`<div class="text-grey text-center">No recent transactions found</div>`
				)
				return;
			};

			const elapsed_time = moment(res[0].posting_date+" "+res[0].posting_time).fromNow();
			this.$customer_section.find('.last-transacted-on').html(`Last transacted ${elapsed_time}`);

			res.forEach(invoice => {
				const posting_datetime = moment(invoice.posting_date+" "+invoice.posting_time).format("Do MMMM, h:mma");
				let indicator_color = '';
				in_list(['Paid', 'Consolidated'], invoice.status) && (indicator_color = 'green');
				invoice.status === 'Draft' && (indicator_color = 'red');
				invoice.status === 'Return' && (indicator_color = 'grey');

				transaction_container.append(
					`<div class="invoice-wrapper flex p-3 justify-between border-b-grey pointer no-select" data-invoice-name="${escape(invoice.name)}">
						<div class="flex flex-col justify-end">
							<div class="text-dark-grey text-bold overflow-hidden whitespace-nowrap mb-2">${invoice.name}</div>
							<div class="flex items-center f-shrink-1 text-dark-grey overflow-hidden whitespace-nowrap">
								${posting_datetime}
							</div>
						</div>
						<div class="flex flex-col text-right">
							<div class="f-shrink-0 text-md text-dark-grey text-bold ml-4">
								${format_currency(invoice.grand_total, invoice.currency, 0) || 0}
							</div>
							<div class="f-shrink-0 text-grey ml-4 text-bold indicator ${indicator_color}">${invoice.status.toUpperCase()}</div>
						</div>
					</div>`
				)
			});
		})
	}

	load_cart_data_from_invoice() {
		const frm = this.events.get_frm();
		this.update_customer_section(frm);
		
		this.$cart_items_wrapper.html('');
		if (frm.doc.items.length) {
			frm.doc.items.forEach(item => {
				this.update_item_html(item);
			});
		} else {
			this.make_no_items_placeholder();
			this.highlight_checkout_btn(false);
		}

		this.update_totals_section(frm);

		if(frm.doc.docstatus === 1) {
			this.$totals_section.find('.checkout-btn').addClass('d-none');
			this.$totals_section.find('.edit-cart-btn').addClass('d-none');
			this.$totals_section.find('.grand-total').removeClass('border-b-grey');
		} else {
			this.$totals_section.find('.checkout-btn').removeClass('d-none');
			this.$totals_section.find('.edit-cart-btn').addClass('d-none');
			this.$totals_section.find('.grand-total').addClass('border-b-grey');
		}
	}

	disable_cart() {
        this.$component.addClass('d-none');
    }
    
}