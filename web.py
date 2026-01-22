"""Web管理界面路由."""
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from auth import WebUser
from database import db
from models import User

# 创建Web蓝图
web = Blueprint('web', __name__)


@web.route('/')
def index():
    """
    首页.
    - 未登录用户显示公开首页（统计信息 + API文档）
    - 已登录用户显示管理首页
    """
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return render_template('public.html')


@web.route('/login', methods=['GET', 'POST'])
def web_login():
    """登录页面."""
    login_error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password') or ''

        user = db.session.query(User).filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(WebUser(user))
            return redirect(url_for('web.index'))
        else:
            login_error = '用户名或密码错误'

    return render_template('login.html', login_error=login_error)


@web.route('/logout')
@login_required
def web_logout():
    """退出登录."""
    logout_user()
    return redirect(url_for('web.index'))


@web.route('/artworks')
@login_required
def artworks():
    """作品列表页面."""
    return render_template('artworks.html')


@web.route('/follows')
@login_required
def follows():
    """关注列表页面."""
    return render_template('follows.html')


@web.route('/collect')
@login_required
def collect():
    """采集管理页面."""
    return render_template('collect.html')


@web.route('/config')
@login_required
def config_page():
    """配置页面."""
    return render_template('config.html')
