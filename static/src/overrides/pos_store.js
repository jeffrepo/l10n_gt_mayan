/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async checkMayanCredit(order) {
        const partner = order?.get_partner();
        if (!partner || !order.lines.some((line) => line.qty > 0)) {
            return true;
        }
        let message;
        try {
            // Do not queue this check or reuse a cached result when disconnected.
            if (this.data.network.offline) {
                throw new Error("offline");
            }
            message = await this.data.call("account.move", "get_last_invoice", [
                partner.id,
                this.config.id,
            ]);
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("No se pudo verificar el crédito"),
                body: _t("Compruebe la conexión y vuelva a intentar. Se necesita consultar las facturas antes de continuar."),
            });
            return false;
        }
        // The customer can change while the request is in flight.
        if (order.get_partner()?.id !== partner.id) {
            return this.checkMayanCredit(order);
        }
        if (message) {
            this.dialog.add(AlertDialog, {
                title: _t("Crédito bloqueado"),
                body: message,
            });
            return false;
        }
        return true;
    },

    async pay() {
        const order = this.get_order();
        if (!(await this.checkMayanCredit(order)) || this.get_order() !== order) {
            return;
        }
        return super.pay(...arguments);
    },

    async sendOrderInPreparationUpdateLastChange(order, cancelled = false) {
        if (!cancelled && !(await this.checkMayanCredit(order))) {
            return;
        }
        return super.sendOrderInPreparationUpdateLastChange(...arguments);
    },

    async sendOrderInPreparation(order, cancelled = false) {
        if (!cancelled && !(await this.checkMayanCredit(order))) {
            return;
        }
        return super.sendOrderInPreparation(...arguments);
    },
});
