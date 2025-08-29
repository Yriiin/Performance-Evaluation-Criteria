# -*- coding: utf-8 -*-
# from odoo import http


# class MutiDevPerformanceEvaluationCriteria(http.Controller):
#     @http.route('/muti_dev_performance_evaluation_criteria/muti_dev_performance_evaluation_criteria/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/muti_dev_performance_evaluation_criteria/muti_dev_performance_evaluation_criteria/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('muti_dev_performance_evaluation_criteria.listing', {
#             'root': '/muti_dev_performance_evaluation_criteria/muti_dev_performance_evaluation_criteria',
#             'objects': http.request.env['muti_dev_performance_evaluation_criteria.muti_dev_performance_evaluation_criteria'].search([]),
#         })

#     @http.route('/muti_dev_performance_evaluation_criteria/muti_dev_performance_evaluation_criteria/objects/<model("muti_dev_performance_evaluation_criteria.muti_dev_performance_evaluation_criteria"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('muti_dev_performance_evaluation_criteria.object', {
#             'object': obj
#         })
