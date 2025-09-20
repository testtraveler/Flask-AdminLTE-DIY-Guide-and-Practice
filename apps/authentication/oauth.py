# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
from flask import current_app as app 
from flask_login import current_user, login_user
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.github import github, make_github_blueprint
from flask_dance.contrib.google import google, make_google_blueprint
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from sqlalchemy.orm.exc import NoResultFound
from apps.config import Config
from apps import db
from apps.authentication.models import User, OAuth
from flask import redirect, url_for
from flask import flash

github_blueprint = make_github_blueprint(
    client_id=Config.GITHUB_ID,
    client_secret=Config.GITHUB_SECRET,
    scope = 'user',
    storage=SQLAlchemyStorage(
        OAuth,
        db.session,
        user=current_user,
        user_required=False,        
    ),   
)

@oauth_authorized.connect_via(github_blueprint)
def github_logged_in(blueprint, token):
    info = github.get("/user")

    if info.ok:
        account_info = info.json()
        username = account_info["login"]

        # 添加软删除过滤
        query = User.query.filter_by(oauth_github=username, deleted_at=None)
        try:
            user = query.one()
            login_user(user)
        except NoResultFound:
            # 创建新用户
            user = User()
            user.username = '(gh)' + username
            user.oauth_github = username
            db.session.add(user)
            db.session.commit()
            login_user(user)

# Google

google_blueprint = make_google_blueprint(
    client_id=Config.GOOGLE_ID,
    client_secret=Config.GOOGLE_SECRET,
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ],
    storage=SQLAlchemyStorage(
        OAuth,
        db.session,
        user=current_user,
        user_required=False,        
    ),   
)

@oauth_authorized.connect_via(google_blueprint)
def google_logged_in(blueprint, token):
    info = google.get("/oauth2/v1/userinfo")

    if info.ok:
        account_info = info.json()
        username = account_info["given_name"]
        email = account_info["email"]

        # 添加软删除过滤
        query = User.query.filter_by(oauth_google=username, deleted_at=None)
        try:
            user = query.one()
            login_user(user)
        except NoResultFound:
            # 创建新用户
            user = User()
            user.username = '(google)' + username
            user.oauth_google = username
            user.email = email
            db.session.add(user)
            db.session.commit()
            login_user(user)
