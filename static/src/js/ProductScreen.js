/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';

export const MayanProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        
        async _updateSelectedOrderline(event) {
            console.log("this ", this.env.pos);
            console.log("event ", event);
            console.log(this.env.pos.employees);
            if(event.detail.key === 'Backspace' && this.env.pos.cashier.allow_delete_line){
                console.log("Se esta eliminando")
                return super._updateSelectedOrderline(...arguments);
            }else{
                console.log("No puede eliminar linea, ni nada");
            }
            
        }
    };
Registries.Component.extend(ProductScreen, MayanProductScreen);