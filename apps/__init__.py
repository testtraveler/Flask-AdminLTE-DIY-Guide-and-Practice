# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module

db = SQLAlchemy()
login_manager = LoginManager()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

from apps.authentication.oauth import github_blueprint, google_blueprint

def create_app(config):

    # Contextual
    static_prefix = '/static'
    templates_dir = os.path.dirname(config.BASE_DIR)

    TEMPLATES_FOLDER = os.path.join(templates_dir,'templates')
    STATIC_FOLDER = os.path.join(templates_dir,'static')

    print(' > TEMPLATES_FOLDER: ' + TEMPLATES_FOLDER)
    print(' > STATIC_FOLDER:    ' + STATIC_FOLDER)

    app = Flask(__name__, static_url_path=static_prefix, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)
    
    # 注册全局变量
    import apps.globals
    apps.globals.logger = app.logger
    
    app.config.from_object(config)

    # 启用 Jinja2 的 do 扩展
    app.jinja_env.add_extension('jinja2.ext.do')
    
    register_extensions(app)
    register_blueprints(app)
    app.register_blueprint(github_blueprint, url_prefix="/login")    
    app.register_blueprint(google_blueprint, url_prefix="/login")   
    

    
    return app
