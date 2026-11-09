import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import vm from "node:vm";

const root = fileURLToPath(new URL("../", import.meta.url));
const source = process.env.ODOO_SOURCE_DIR;
assert.ok(source, "Set ODOO_SOURCE_DIR to the official Odoo 18 source tree.");

function evaluate(context, filename, exports = []) {
    const code = readFileSync(filename, "utf8")
        .replace(/^import\b[\s\S]*?;\s*$/gm, "")
        .replace(/^export\s+(?=class |function |const |let )/gm, "");
    return vm.runInContext(`(() => {${code}\nreturn {${exports.join(",")}};})()`, context, { filename });
}

function runtime() {
    const context = vm.createContext({
        Reactive: class {}, Component: class {},
        registry: { category: () => ({ add() {} }) },
        luxon: { DateTime: {} }, _t: (text) => text,
        AlertDialog: class {}, OrderReceipt: class {}, Numpad: class {},
        PaymentScreenPaymentLines: class {}, PaymentScreenStatus: class {},
        Input: class {}, PartnerLine: class {}, Orderline: class {}, OrderWidget: class {},
        floatIsZero: (number) => Math.abs(number) < 1e-8,
        console,
    });
    for (const [file, names] of [
        ["addons/web/static/src/core/utils/patch.js", ["patch"]],
        ["addons/point_of_sale/static/src/app/store/pos_store.js", ["PosStore"]],
        ["addons/point_of_sale/static/src/app/screens/payment_screen/payment_screen.js", ["PaymentScreen"]],
        ["addons/point_of_sale/static/src/app/screens/product_screen/order_summary/order_summary.js", ["OrderSummary"]],
    ]) {
        Object.assign(context, evaluate(context, join(source, file), names));
    }
    // Only replace terminal/finalization side effects; execute the real pay,
    // validateOrder, preparation, and line-edit methods from Odoo 18 unchanged.
    context.patch(context.PaymentScreen.prototype, {
        async _finalizeValidation() { this.finalized = true; },
        async sendPaymentRequest() { this.terminalStarted = true; },
    });
    for (const file of ["pos_store", "payment_screen", "order_summary"]) {
        evaluate(context, join(root, `static/src/overrides/${file}.js`));
    }
    return context;
}

function fixture({ message = false, qty = [1], partner = { id: 7 }, offline = false } = {}) {
    const ctx = runtime();
    const order = {
        partner, id: "local-order", state: "draft",
        lines: qty.map((q) => ({ qty: q, product_id: { uom_id: { rounding: 1 } },
            get_product: () => ({ tracking: "none" }) })),
        get_partner() { return this.partner; }, canPay: () => true,
        updateLastOrderChange() { this.prepared = true; },
    };
    const pos = Object.create(ctx.PosStore.prototype);
    pos.currentOrder = order;
    pos.get_order = () => pos.currentOrder;
    pos.config = { id: 3 };
    pos.dialogs = [];
    pos.dialog = { add: (_, values) => pos.dialogs.push(values) };
    pos.calls = [];
    pos.data = {
        network: { offline },
        call: async (...args) => { pos.calls.push(args); return message; },
    };
    pos.env = { services: { pos } };
    pos.showScreen = (name) => { pos.screen = name; };
    pos.printers_category_ids_set = new Set();
    const payment = Object.create(ctx.PaymentScreen.prototype);
    Object.defineProperty(payment, "currentOrder", { get: () => pos.currentOrder });
    Object.defineProperty(payment, "paymentLines", { get: () => [] });
    payment.pos = pos;
    payment.numberBuffer = { capture() {} };
    payment.check_cash_rounding_has_been_well_applied = () => true;
    payment._isOrderValid = async () => true;
    return { ctx, pos, order, payment };
}

for (const action of ["pay", "prepare", "submit", "validate", "finalize", "terminal"]) {
    test(`overdue customer blocks ${action}`, async () => {
        const { pos, order, payment } = fixture({ message: "Saldo pendiente de septiembre" });
        if (action === "pay") await pos.pay();
        if (action === "prepare") await pos.sendOrderInPreparation(order);
        if (action === "submit") await pos.sendOrderInPreparationUpdateLastChange(order);
        if (action === "validate") await payment.validateOrder();
        if (action === "finalize") await payment._finalizeValidation();
        if (action === "terminal") await payment.sendPaymentRequest();
        assert.equal(pos.screen, undefined);
        assert.equal(order.prepared, undefined);
        assert.equal(payment.finalized, undefined);
        assert.equal(payment.terminalStarted, undefined);
        assert.equal(pos.dialogs[0].title, "Crédito bloqueado");
        assert.equal(pos.calls[0][0], "account.move");
        assert.equal(pos.calls[0][1], "get_last_invoice");
        assert.deepEqual(Array.from(pos.calls[0][2]), [7, 3]);
    });
}

test("current customer proceeds through native pay, preparation, and validation", async () => {
    const { pos, order, payment } = fixture();
    await pos.pay();
    assert.equal(pos.screen, "PaymentScreen");
    await pos.sendOrderInPreparationUpdateLastChange(order);
    assert.equal(order.prepared, true);
    await payment.validateOrder();
    assert.equal(payment.finalized, true);
    assert.equal(pos.dialogs.length, 0);
});

test("offline cannot authorize a customer's sale", async () => {
    const { pos, payment } = fixture({ offline: true });
    await payment.validateOrder();
    assert.equal(payment.finalized, undefined);
    assert.equal(pos.calls.length, 0);
    assert.equal(pos.dialogs[0].title, "No se pudo verificar el crédito");
});

test("RPC failures cannot authorize a sale", async () => {
    const { pos } = fixture();
    pos.data.call = async () => { throw new Error("server disconnected"); };
    await pos.pay();
    assert.equal(pos.screen, undefined);
    assert.equal(pos.dialogs[0].title, "No se pudo verificar el crédito");
});

test("payment immediately unlocks the next attempt, without reopening POS", async () => {
    const { pos } = fixture({ message: "Pendiente" });
    await pos.pay();
    assert.equal(pos.screen, undefined);
    pos.data.call = async () => false;
    await pos.pay();
    assert.equal(pos.screen, "PaymentScreen");
});

test("pure refunds remain possible for blocked customers", async () => {
    const { pos, payment } = fixture({ message: "Pendiente", qty: [-1, -2] });
    await payment.validateOrder();
    assert.equal(payment.finalized, true);
    assert.equal(pos.calls.length, 0);
});

test("mixed sale and refund still checks credit", async () => {
    const { pos, payment } = fixture({ message: "Pendiente", qty: [-10, 1] });
    await payment.validateOrder();
    assert.equal(payment.finalized, undefined);
    assert.equal(pos.dialogs[0].title, "Crédito bloqueado");
});

test("anonymous sales keep standard behavior", async () => {
    const { pos, payment } = fixture({ partner: null });
    await payment.validateOrder();
    assert.equal(payment.finalized, true);
    assert.equal(pos.calls.length, 0);
});

test("kitchen cancellations do not require credit clearance", async () => {
    const { pos, order } = fixture({ message: "Pendiente" });
    await pos.sendOrderInPreparationUpdateLastChange(order, true);
    assert.equal(order.prepared, true);
    assert.equal(pos.calls.length, 0);
});

test("customer changed during request is checked again", async () => {
    const { pos, order } = fixture();
    let calls = 0;
    pos.data.call = async (model, method, args) => {
        calls++;
        if (args[0] === 7) {
            order.partner = { id: 8 };
            return false;
        }
        return "Cliente 8 bloqueado";
    };
    await pos.pay();
    assert.equal(calls, 2);
    assert.equal(pos.screen, undefined);
    assert.equal(pos.dialogs[0].body, "Cliente 8 bloqueado");
});

test("switching the current order while checking does not pay another order", async () => {
    const { pos } = fixture();
    pos.data.call = async () => { pos.currentOrder = {}; return false; };
    await pos.pay();
    assert.equal(pos.screen, undefined);
});

test("customer selected by native order validation is checked before finalizing", async () => {
    const { pos, order, payment } = fixture({ partner: null, message: "Pendiente" });
    payment._isOrderValid = async () => { order.partner = { id: 7 }; return true; };
    await payment.validateOrder();
    assert.equal(payment.finalized, undefined);
    assert.equal(pos.dialogs[0].title, "Crédito bloqueado");
});

for (const [permission, hr, removed] of [[false, true, false], [true, true, true], [false, false, true]]) {
    test(`line removal: permission=${permission}, employee login=${hr}`, () => {
        const { ctx, pos, order } = fixture();
        pos.config.module_pos_hr = hr;
        pos.numpadMode = "quantity";
        pos.get_cashier = () => ({ allow_delete_line: permission });
        const line = { combo_line_ids: [], set_quantity() { this.changed = true; return true; } };
        order.get_selected_orderline = () => line;
        order.removeOrderline = () => { order.removed = true; };
        const summary = Object.create(ctx.OrderSummary.prototype);
        summary.pos = pos;
        summary.dialog = pos.dialog;
        summary.numberBuffer = { reset() {} };
        summary._setValue("2");
        assert.equal(line.changed, true, "normal quantity edits must remain usable");
        summary._setValue("remove");
        assert.equal(Boolean(order.removed), removed);
    });
}

for (const action of ["_finalizeValidation", "sendPaymentRequest"]) {
    test(`switching orders during ${action} does not act on the other order`, async () => {
        const { pos, payment } = fixture();
        pos.data.call = async () => { pos.currentOrder = {}; return false; };
        await payment[action]();
        assert.equal(payment.finalized, undefined);
        assert.equal(payment.terminalStarted, undefined);
    });
}
