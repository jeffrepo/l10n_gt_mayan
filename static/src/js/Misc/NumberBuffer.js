odoo.define('l10n_gt_mayan.simple_backspace', function (require) {
"use strict";

console.log("🔧 Módulo de Backspace cargado");

// Agregar el event listener globalmente
window.addEventListener("keydown", function(ev) {
    if (ev.key === 'Backspace') {
        console.log("🎹 Backspace presionado a nivel global");
        console.log("📍 En elemento:", ev.target);
        console.log("🔍 Tipo de elemento:", ev.target.tagName);
        console.log("📝 Valor actual:", ev.target.value || 'N/A');
    }
});

function _tuFuncionPersonalizada(ev) {
    console.log("🔄 Ejecutando función personalizada para Backspace");
    // Tu código personalizado
}

return {};
});