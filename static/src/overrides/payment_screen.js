/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async sendPaymentRequest() {
        const order = this.currentOrder;
        if (!(await this.pos.checkMayanCredit(order)) || this.currentOrder !== order) {
            return;
        }
        return super.sendPaymentRequest(...arguments);
    },

    async _finalizeValidation() {
        // Odoo may select a required customer during _isOrderValid.
        const order = this.currentOrder;
        if (!(await this.pos.checkMayanCredit(order)) || this.currentOrder !== order) {
            return;
        }
        return super._finalizeValidation(...arguments);
    },

    async validateOrder() {
        const order = this.currentOrder;
        if (!(await this.pos.checkMayanCredit(order)) || this.currentOrder !== order) {
            return;
        }
        return super.validateOrder(...arguments);
    },
});
