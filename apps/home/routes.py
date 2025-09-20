# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request
from flask_login import login_required
from jinja2 import TemplateNotFound

BACKEND_ADMIN_MENU_ITEMS = [
    {
        "label": "首页看板",
        "href": "/dashboard.html",
        "icon": "fa-home",
        "context_key": "dashboard"
    },
    {
        "label": "合同管理",
        "href": "/contracts.html",
        "icon": "fa-file-contract",
        "context_key": "contracts"
    },
    {
        "label": "工单管理",
        "href": "/workorders.html",
        "icon": "fa-tasks",
        "context_key": "workorders"
    },
    {
        "label": "请求审核",
        "href": "/approvals.html",
        "icon": "fa-check-circle",
        "context_key": "approvals"
    },
    {
        "label": "角色管理",
        "href": "/roles.html",
        "icon": "fa-user-shield",
        "context_key": "roles"
    },
    {
        "label": "用户管理",
        "icon": "fa-users",
        "context_key": "users",
        "children": [
            {
                "label": "用户组",
                "href": "/user-groups.html",
                "icon": "fa-circle",
                "context_key": "user-groups"
            },
            {
                "label": "用户列表",
                "href": "/user-list.html",
                "icon": "fa-circle",
                "context_key": "user-list"
            }
        ]
    },
    {
        "label": "资源管理",
        "icon": "fa-boxes",
        "context_key": "resources",
        "children": [
            {
                "label": "基础资源",
                "href": "/basic-resources.html",
                "icon": "fa-circle",
                "context_key": "basic-resources"
            },
            {
                "label": "业务资源",
                "href": "/business-resources.html",
                "icon": "fa-circle",
                "context_key": "business-resources"
            }
        ]
    },
    {
        "label": "告警管理",
        "href": "/alerts.html",
        "icon": "fa-exclamation-triangle",
        "context_key": "alerts"
    },
    {
        "label": "反馈管理",
        "href": "/feedback.html",
        "icon": "fa-comment-dots",
        "context_key": "feedback"
    },
    {
        "label": "日志管理",
        "icon": "fa-clipboard-list",
        "context_key": "logs",
        "children": [
            {
                "label": "审计日志",
                "href": "/audit-logs.html",
                "icon": "fa-circle",
                "context_key": "audit-logs"
            },
            {
                "label": "登录日志",
                "href": "/login-logs.html",
                "icon": "fa-circle",
                "context_key": "login-logs"
            },
            {
                "label": "运行日志",
                "href": "/runtime-logs.html",
                "icon": "fa-circle",
                "context_key": "runtime-logs"
            }
        ]
    }
]


@blueprint.route('/index')
def index():
    return render_template('home/index.html', segment='index', menu_items=BACKEND_ADMIN_MENU_ITEMS)

@blueprint.route('/<template>')
@login_required
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment, menu_items=BACKEND_ADMIN_MENU_ITEMS)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        import logging
        logging.error("route_template 500 错误: %s", exc_info=True)
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
