# -*- coding: utf-8 -*-
# from odoo import http


# class L10nGtMayan(http.Controller):
#     @http.route('/l10n_gt_mayan/l10n_gt_mayan', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_gt_mayan/l10n_gt_mayan/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_gt_mayan.listing', {
#             'root': '/l10n_gt_mayan/l10n_gt_mayan',
#             'objects': http.request.env['l10n_gt_mayan.l10n_gt_mayan'].search([]),
#         })

#     @http.route('/l10n_gt_mayan/l10n_gt_mayan/objects/<model("l10n_gt_mayan.l10n_gt_mayan"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_gt_mayan.object', {
#             'object': obj
#         })

