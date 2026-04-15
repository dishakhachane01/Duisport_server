/** @odoo-module **/

import { Component, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class Dashboard extends Component {

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");  // ✅ SAFE

        this.currentCompany = this.user.companyId;
        this.openVendor = this.openVendor.bind(this);
        this.data = {
            po_list: [],
            rfq_list: [],
        };

        this.dataa = {
            sales: {},
            inventory: {},
            manufacturing: {},
        };

        // ✅ LOAD FUNCTION
        this.loadData = async () => {
            const [stats, pending] = await Promise.all([
                this.rpc('/dashboard/stats', {}),
                this.rpc('/pending_dashboard/data', {}),
            ]);

            this.dataa = stats;
            this.data = pending;
            this.render();
        };

        // ✅ INITIAL LOAD
        onWillStart(async () => {
            await this.loadData();
        });

        // ✅ AUTO REFRESH (company change detection)
        onMounted(() => {
            setInterval(() => {
                if (this.currentCompany !== this.user.companyId) {
                    this.currentCompany = this.user.companyId;
                    this.loadData();
                }
            }, 2000); // check every 2 sec
        });

        // ✅ Bind methods
        this.openPO = this.openPO.bind(this);
        this.openRFQ = this.openRFQ.bind(this);
        this.openSales = this.openSales.bind(this);
        this.openInventory = this.openInventory.bind(this);
        this.openMRP = this.openMRP.bind(this);
    }

    // ================= OPEN RECORDS =================

    openPO(id) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'purchase.order',
            res_id: id,
            views: [[false, 'form']],
        });
    }

    openRFQ(id) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'rfq.request',
            res_id: id,
            views: [[false, 'form']],
        });
    }

    openVendor(id) {
    this.action.doAction({
        type: 'ir.actions.act_window',
        res_model: 'res.partner',
        res_id: id,
        views: [[false, 'form']],
        target: 'current',
    });
}

// openVendorsList() {
//     this.action.doAction({
//         type: 'ir.actions.act_window',
//         name: 'Vendors Pending Approval',
//         res_model: 'res.partner',
//         views: [[false, 'list'], [false, 'form']],
//         domain: [['vendor_approval_state', '=', 'to_approve_management']],
//     });
// }

    // ================= CLICKABLE STATS =================

    openSales(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Sales',
            res_model: 'sale.order',
            views: [[false, 'list'], [false, 'form']],
            domain: [['state', '=', state]],
        });
    }

    openInventory(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Inventory',
            res_model: 'stock.picking',
            views: [[false, 'list'], [false, 'form']],
            domain: [['state', '=', state]],
        });
    }

    openMRP(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Manufacturing',
            res_model: 'mrp.production',
            views: [[false, 'list'], [false, 'form']],
            domain: [['state', '=', state]],
        });
    }
}

Dashboard.template = "advanced_dashboard";
registry.category("actions").add("advanced_dashboard", Dashboard);