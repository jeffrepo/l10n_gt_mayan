odoo.define('l10n_gt_mayan.SubmitOrderButtonPatch', function (require) {
    'use strict';

    const { patch } = require('web.utils');
    const rpc = require('web.rpc');
    const SubmitOrderButton = require('pos_restaurant.SubmitOrderButton');

    // ✅ Guardamos referencia al método original
    const originalOnClick = SubmitOrderButton.prototype._onClick;

    patch(SubmitOrderButton.prototype, 'l10n_gt_mayan.SubmitOrderButtonPatch', {
        async _onClick() {
            console.log("🟢 Parche de l10n_gt_mayan funcionando");

            const order = this.env.pos.get_order();

            if (order && order.partner) {
                console.log("Partner id ", order.partner.name);
                try {
                    const result = await rpc.query({
                        model: 'account.move',
                        method: 'get_last_invoice',
                        args: [order.partner.id],
                    }, {
                        timeout: 10000,
                        shadow: true,
                    });

                    console.log("🟡 Resultado de get_last_invoice:", result);

                    if (result) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Cliente con facturas vencidas'),
                            body: this.env._t(result),
                        });
                        return; // 🚫 Cancelamos la ejecución normal
                    }
                } catch (error) {
                    console.error("🔴 Error en RPC:", error);
                    await this._handle_odoo_connection_failure();
                    return;
                }
            }

            // ✅ Llamamos manualmente al método original
            if (originalOnClick) {
                await originalOnClick.apply(this, arguments);
            }
        },
    });
});
