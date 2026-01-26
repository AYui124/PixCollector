"""Flask应用主文件."""
import logging
import os

from flask import Flask, redirect, render_template, url_for

from auth import init_auth, login_manager
from config import Config
from controllers.artwork_controller import artwork_api
from controllers.auth_controller import auth_api
from controllers.collect_controller import collect_api
from controllers.config_controller import config_api
from controllers.follow_controller import follow_api
from controllers.public_controller import public_api
from core.database import get_engine
from services import services
from web import web


def create_app() -> Flask:
    """
    创建并配置Flask应用.

    Returns:
        Flask应用实例
    """
    # 创建Flask应用
    app = Flask(__name__)

    # 加载配置
    app.config.from_object(Config)

    # 初始化日志
    setup_logging(app)

    # 初始化数据库引擎
    get_engine()

    # 初始化错误处理器
    setup_error_handlers(app)

    # 初始化认证系统（需要 auth service）
    init_auth(app, services.auth)

    # 配置未登录访问重定向到首页
    @login_manager.unauthorized_handler
    def unauthorized_callback():
        """未登录用户访问需要登录的页面时重定向到首页."""
        return redirect(url_for('web.index'))

    # 注册蓝图
    app.register_blueprint(web)

    # 注册API蓝图
    app.register_blueprint(public_api, url_prefix='/api')
    app.register_blueprint(auth_api, url_prefix='/api')
    app.register_blueprint(config_api, url_prefix='/api')
    app.register_blueprint(collect_api, url_prefix='/api')
    app.register_blueprint(artwork_api, url_prefix='/api')
    app.register_blueprint(follow_api, url_prefix='/api')

    return app


def setup_logging(app: Flask) -> None:
    """
    配置日志系统.

    Args:
        app: Flask应用实例
    """
    # 确保logs目录存在
    os.makedirs('logs', exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                'logs/pixcollector.log',
                encoding='utf-8',
                errors='ignore'
            ),
        ]
    )
    app.logger.setLevel(logging.INFO)


def setup_error_handlers(app: Flask) -> None:
    """
    配置全局错误处理器.

    Args:
        app: Flask应用实例
    """

    @app.errorhandler(404)
    def not_found(error):
        """处理404错误."""
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """处理500错误."""
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(error):
        """处理403错误."""
        return render_template('errors/403.html'), 403


def create_app_context() -> Flask:
    """
    创建应用上下文（用于脚本）.

    Returns:
        Flask应用实例
    """
    return create_app()


if __name__ == '__main__':
    app = create_app()

    app.run(
        host='0.0.0.0',
        port=app.config.get('FLASK_PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )
