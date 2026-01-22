# PixCollector

Pixiv图片采集系统 - 基于Python Flask的Pixiv图片自动采集、管理和展示系统。

## 功能特性

### 多种采集模式

- **排行榜采集**：每日/每周/每月排行榜前30作品
- **关注列表同步**：自动同步Pixiv关注用户列表
- **关注用户新作品**：采集关注用户发布的最新作品
- **初始全量采集**：支持对关注用户进行初始历史数据采集，可配置回采年限
- **作品元数据更新**：批量更新已保存作品的元数据信息

### 防风控机制

- 可配置的API调用延迟（1-10秒）
- 分批处理机制（每5个请求暂停）
- 智能错误重试策略：
  - 429错误（请求过多）：延迟30-60秒
  - 403错误（禁止访问）：延迟60-120秒
  - 其他错误：延迟10-20秒

### Web管理界面

- **用户认证**：基于Flask-Login的安全登录系统
- **作品浏览**：作品列表展示，支持多条件过滤、分页浏览
- **多图预览**：支持多图作品全屏预览，可翻页查看
- **关注管理**：关注用户列表，显示用户信息和采集统计
- **采集日志**：实时查看采集任务执行情况和错误信息
- **系统配置**：可视化的配置管理界面，配置保存在数据库中

### 定时任务调度

- 基于APScheduler的灵活调度系统
- 支持Cron表达式配置执行间隔
- 支持独立的任务开关
- 支持动态刷新任务配置（无需重启）
- 自动记录任务执行时间和状态

## 技术栈

- **后端框架**: Python 3.12+ + Flask 3.0
- **数据库ORM**: SQLAlchemy 3.1（使用Typed ORM）
- **数据库**: MySQL 5.7+ / PyMySQL 1.1.0
- **用户认证**: Flask-Login 0.6.3
- **任务调度**: APScheduler 3.10.4
- **Pixiv API**: pixivpy3 3.7.5（使用ByPassSniApi）
- **前端框架**: Bulma CSS + Animate.css + Jinja2模板引擎
- **数据库迁移**: Flask-Migrate 4.0.5
- **密码加密**: Werkzeug 3.0.1 + Cryptography 46.0.3
- **环境变量**: python-dotenv 1.0.0

## 快速开始

### 前置要求

- Python 3.12 或更高版本
- MySQL 5.7 或更高版本
- Pixiv账号（用于获取API Token）

### 本地开发或部署

#### 1. 克隆项目

```bash
git clone https://github.com/AYui124/PixCollector.git
cd PixCollector
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Flask配置
FLASK_SECRET_KEY=your-secret-key-here-change-this
FLASK_PORT=5000

# 管理员账户（首次启动时使用）
ADMIN_USER='admin'
ADMIN_PWD='your-strong-password'

# Pixiv图片代理配置
PIXIV_PROXY_URL=https://i.pixiv.re

# MySQL数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=pixcollector
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
```

#### 4. 创建数据库

```bash
mysql -u root -p
```

在MySQL命令行中执行：

```sql
CREATE DATABASE pixcollector CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

#### 5. 初始化数据库

```bash
python migrate.py
```

这将创建所有必需的表结构。

#### 6. 启动应用

```bash
python run.py
```

应用将在 `http://localhost:5000` 启动。

#### 7. 系统初始化

首次访问系统时：

1. 修改 `.env` 配置管理员账户密码
2. 使用命令行初始化系统：
```bash
curl -X POST http://127.0.0.1:5000/api/init
```
3. 访问登录页面：`http://localhost:5000/login`
4. 进入"配置"页面
5. 配置Pixiv API Token（详见下文）

### 获取Pixiv API Token

需要Pixiv的 `refresh_token` 才能使用。

#### 方法1：使用pixiv的oauth工具

1. 在github搜索类似工具，如[get-pixivpy-token](https://github.com/eggplants/get-pixivpy-token)
2. 按照readme操作登录Pixiv，工具会输出所需的token。

#### 方法2：使用app（推荐）

推荐原因：免代理，易于操作
1. 手机或虚拟机安装[pixez](https://github.com/Notsfsssf/pixez-flutter)
2. app登录后在更多-账户信息点击Token export
3. 复制输出的refresh_token

#### 方法3：浏览器开发者工具

1. 登录Pixiv网站（https://www.pixiv.net）
2. 打开开发者工具（F12）
3. 切换到 Network 标签
4. 在网站上浏览作品，找到API请求
5. 从请求头中提取 `Authorization` 字段的值（Bearer token格式）

## API文档

### 公开API（无需认证）

#### 随机图片API

**接口地址**：`GET /api/random/artwork`

**请求参数**：

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|--------|--------|------|
| limit | integer | 否 | 1 | 返回数量（1-10） |
| tags | string | 否 | 空 | 标签过滤，多个标签用逗号分隔 |
| tags_match | string | 否 | or | 标签匹配方式：and（所有标签）或 or（任一标签） |
| is_r18 | string | 否 | all | R18过滤：true（只R18）、false（只非R18）、all（全部） |

**返回示例**：

```json
{
  "success": true,
  "count": 2,
  "artworks": [
    {
      "illust_id": "121607103",
      "title": "雌小鬼兔糖糖",
      "author_id": "9631509",
      "author_name": "YogurtWZI",
      "url": "https://i.pixiv.re/c/600x1200_90/img-master/img/2024/08/18/15/57/58/121607103_p0_master1200.jpg",
      "share": "https://www.pixiv.net/artworks/121607103",
      "page": "1/1",
      "total_bookmarks": 13967,
      "total_view": 56412,
      "tags": ["オリキャラ", "OC", "ソックス足裏", "白タイツ", "魅惑のふともも", "兔糖糖", "女の子", "メスガキ", "オリジナル10000users入り", "タイツ越しのパンツ"],
      "type": "illust",
      "is_r18": false
    }
  ]
}
```

#### 直接获取图片URL

**接口地址**：`GET /api/random/artwork/image`

**请求参数**：同随机图片API

**返回格式**：

```json
{
  "success": true,
  "image_url": "图片URL",
  "illust_id": "作品ID",
  "title": "作品标题",
  "author_name": "作者名",
  "tags": ["标签1", "标签2"],
  "is_r18": false
}
```

## Docker部署

image未上传仓库，项目已提供dockerfile需自行build
```bash
docker build -t pixcollector:latest .
```
### 使用Docker Compose（推荐）

1. 确保已安装Docker和Docker Compose
2. 复制`env.example`为`app.env` 文件（修改见上文）
3. 修改docker-compose.yml（非必须）
4. 启动服务
   ```bash
   docker-compose up -d
   ```
5. 初始化数据库
   ```bash
   docker-compose exec app python migrate.py
   ```
6. 访问应用：`http://localhost:5000`

### 独立使用Docker

1. 构建镜像
   ```bash
   docker build -t pixcollector .
   ```
2. 运行容器
   ```bash
   docker run -d \
     --name pixcollector \
     -p 5000:5000 \
     --env-file app.env \
     pixcollector
   ```
3. 访问应用：`http://localhost:5000`

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| FLASK_SECRET_KEY | Flask会话密钥 | - | 是 |
| FLASK_PORT | 应用端口 | 5000 | 否 |
| ADMIN_USER | 管理员用户名 | admin | 否 |
| ADMIN_PWD | 管理员密码 | password | 否 |
| PIXIV_PROXY_URL | Pixiv图片代理URL | https://i.pixiv.re | 否 |
| MYSQL_HOST | MySQL主机 | localhost | 是 |
| MYSQL_PORT | MySQL端口 | 3306 | 否 |
| MYSQL_DATABASE | 数据库名 | pixcollector | 是 |
| MYSQL_USER | MySQL用户 | root | 是 |
| MYSQL_PASSWORD | MySQL密码 | - | 是 |

## 许可证

本项目仅供学习和研究使用。请遵守Pixiv的服务条款和相关法律法规。

## 贡献

欢迎提交Issue和Pull Request！

## 致谢

- [pixivpy3](https://github.com/upbit/pixivpy3) - Pixiv API Python SDK
- [Flask](https://flask.palletsprojects.com/) - Python Web框架
- [Bulma](https://bulma.io/) - 前端UI框架
- [APScheduler](https://github.com/agronholm/apscheduler) - Python定时任务调度

## 联系方式

如有问题或建议，请提交Issue。
