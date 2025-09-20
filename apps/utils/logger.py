from flask import Flask
from logging import Logger

logger: Logger = None          # 将在 create_app 阶段被重新绑定

def init_logger(app: Flask):
    """把 app.logger 挂到扩展模块，供全项目 import"""
    global logger
    logger = app.logger        # 就是同一个 Logger 实例