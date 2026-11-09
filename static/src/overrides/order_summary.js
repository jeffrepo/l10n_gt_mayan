/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    _setValue(value) {
        if (
            value === "remove" &&
            this.pos.numpadMode === "quantity" &&
            this.currentOrder.get_selected_orderline() &&
            this.pos.config.module_pos_hr &&
            !this.pos.get_cashier()?.allow_delete_line
        ) {
            this.numberBuffer.reset();
            this.dialog.add(AlertDialog, {
                title: _t("Acción no permitida"),
                body: _t("Este empleado no tiene permiso para eliminar líneas del pedido."),
            });
            return;
        }
        return super._setValue(...arguments);
    },
});
