"""Flask应用配置."""
import os
import tomllib
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=False)


# 读取pyproject.toml获取GitHub URL
def _load_github_url() -> str | None:
    """
    从pyproject.toml中读取GitHub URL.

    Returns:
        GitHub URL或None
    """

    try:
        pyproject_path = Path(__file__).parent / 'pyproject.toml'
        if not pyproject_path.exists():
            return None

        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)

        # 从project.urls中获取Repository URL
        if 'project' in data and 'urls' in data['project']:
            return str(data['project']['urls'].get('Repository'))

        return None
    except Exception:
        # 如果读取失败，返回None
        return None


GITHUB_URL = _load_github_url()


class Config:
    """应用配置类."""

    # Flask配置
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', '')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # 数据库配置
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'pixcollector')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')

    ADMIN_USER = os.getenv('ADMIN_USER', 'user')
    ADMIN_PWD = os.getenv('ADMIN_PWD', 'Pix@1234')

    # Pixiv图片代理
    PIXIV_PROXY_URL = os.getenv('PIXIV_PROXY_URL', 'https://i.pixiv.re')

    # GitHub仓库URL
    GITHUB_URL = GITHUB_URL

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://"
        f"{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )
