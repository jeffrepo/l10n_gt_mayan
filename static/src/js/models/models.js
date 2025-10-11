odoo.define('l10n_gt_mayan.employees', function (require) {
    "use strict";

var { Order } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');
// Order.load_fields('hr.employee', 'allow_delete_line')

const MayanOrder = (Order) => class MayanOrder extends Order {
    constructor(obj, options) {
        super(...arguments);
        console.log("options ", options);
        if (!options.json && this.pos.config.module_pos_hr) {
            this.employee_by_id = this.pos.get_cashier();
        }
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        console.log("JSON ", json);
        if (this.pos.config.module_pos_hr && json.employee_id) {
            this.cashier = this.pos.employee_by_id[json.employee_id];
        }
    }
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.module_pos_hr) {
            json.employee_id = this.cashier ? this.cashier.id : false;
        }
        return json;
    }
}
Registries.Model.extend(Order, MayanOrder);

});
