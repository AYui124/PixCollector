# PixCollector

Pixiv图片采集系统 - 基于Python Flask的Pixiv图片自动采集、管理和展示系统。

## 功能特性

### Web管理界面

- **用户认证**：基于Flask-Login的安全登录系统
- **作品管理**：采集作品列表展示，支持多条件过滤、分页浏览，标记废弃
- **采集日志**：实时查看采集任务执行情况和错误信息
- **系统配置**：可视化的配置管理界面，配置保存在数据库中

### 采集功能

- **官方排行榜**：支持采集日/周/月排行榜
- **关注用户**：自动同步关注列表，采集关注用户新作品
- **自定义榜单**：基于关键词搜索，按评分筛选高质量作品

## 技术栈

- **后端框架**: Python 3.12+ + Flask 3.0
- **数据库ORM**: SQLAlchemy 3.1
- **数据库**: MySQL 5.7+ / PyMySQL 1.1.0
- **异步及任务**: huey + croniter(解析cron表达式)
- **Pixiv API**: pixivpy3 3.7.5
- **前端框架**: Bulma CSS + Animate.css + Jinja2模板引擎

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
具体参数说明参考环境变量一节

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
#在2个终端里分别运行
python run_app.py # api及web
python run_huey.py # 异步任务
```

flask将监听5000端口，访问 `http://127.0.0.1:5000` 即可。

#### 7. 系统初始化

首次访问系统时：

1. 修改 `.env` 配置管理员账户密码
2. 使用命令行初始化系统：
```bash
curl -X POST http://127.0.0.1:5000/api/init
```
3. 访问登录页面：`http://127.0.0.1:5000/login`
4. 进入"配置"页面
5. 配置Pixiv API Token（详见下文）

### 获取Pixiv API Token

需要Pixiv的 `refresh_token` 才能使用。

#### 方法1：使用pixiv的oauth工具

1. 在github搜索类似工具，如 [get-pixivpy-token](https://github.com/eggplants/get-pixivpy-token)
2. 按照readme操作登录Pixiv，工具会输出所需的token。

#### 方法2：使用app（推荐）

推荐原因：免代理，易于操作
1. 手机或虚拟机安装 [pixez](https://github.com/Notsfsssf/pixez-flutter)
2. app登录后在更多-账户信息点击Token export
3. 复制输出的refresh_token

#### 方法3：浏览器开发者工具

1. 登录[Pixiv](https://www.pixiv.net)网站
2. 打开开发者工具（F12）
3. 切换到 Network 标签
4. 在网站上浏览作品，找到API请求
5. 从请求头中提取 `Authorization` 字段的值（Bearer token格式）

## API文档

### 公开API（无需认证）
详见启动后首页

## Docker部署

### 镜像拉取或构建

项目已提供Dockerfile可以自行build  
```bash
docker build -t pixcollector:latest .
```
或者从本项目拉取
``` bash
 docker pull ghcr.io/ayui124/pixcollector:latest
```

### 使用Docker Compose

1. 复制`env.example`为`app.env` 文件（修改见上文）
2. 修改docker-compose.yml  
   默认带redis但没有mysql，按自己环境调整修改
3. 启动服务
   ```bash
   docker-compose up -d
   ```
4. 初始化数据库
   ```bash
   docker-compose exec web python migrate.py
   ```
5. 访问应用：`http://your-ip:5000`


## 配置说明

### 数据库配置项

系统支持通过Web界面动态配置以下参数，配置保存在数据库中：

#### Pixiv API配置
- `access_token`: Pixiv访问令牌（自动获取）
- `refresh_token`: Pixiv刷新令牌（必需）
- `token_expires_at`: Token过期时间（自动管理）
- `pixiv_user`: Pixiv用户ID（自动获取）

#### 自定义榜单配置
- `custom_ranking_keywords`: 自定义榜单关键词列表（逗号分隔）
  - 示例：`黒スト,贫乳,女の子`
  - 系统会依次搜索每个关键词，按评分筛选高质量作品

#### API请求配置
- `api_delay_min`: 最小请求延迟（秒）
- `api_delay_max`: 最大请求延迟（秒）
- `error_delay_429_min`: 429错误最小延迟（秒）
- `error_delay_429_max`: 429错误最大延迟（秒）
- `error_delay_403_min`: 403错误最小延迟（秒）
- `error_delay_403_max`: 403错误最大延迟（秒）
- `error_delay_other_min`: 其他错误最小延迟（秒）
- `error_delay_other_max`: 其他错误最大延迟（秒）

#### 排行榜采集配置
- `ranking_collect_pages`: 官方排行榜采集页数（默认5页）

#### 关注用户配置
- `new_user_backtrack_years`: 新用户回采年限（默认2年）

#### 作品更新配置
- `update_interval_days`: 作品更新间隔天数（默认30天）
- `update_max_per_run`: 每次更新最大作品数（默认200）
- `invalid_artwork_action`: 失效作品处理策略（delete/mark，默认mark）

#### 日志配置
- `log_retention_days`: 日志保留天数（默认90天）

### 自定义榜单评分规则

自定义榜单使用智能评分系统筛选高质量作品：

**评分公式**: `score = bookmark_count / (hours_since_post + 2) × (bookmark_count / total_view)`
- AI作品调整：如果作品包含AI相关标签（如"AI生成"、"Stable Diffusion"等）评分按权重调整：
   - 24小时内：score *= 0.45
   - 24小时后：score *= 0.65

**筛选条件**:
- 发布时间 < 3小时 → 跳过
- 收藏数 < 300 → 跳过
- R-18 → 跳过
- 超过5页 → 跳过
- 非插画或tags带漫画 → 跳过
- 动态阈值：按评分公式计算score
   - 24小时内：score < 9.0 → 跳过
   - 24小时后：score < 3.2 → 跳过

**查询策略**:
- 每个关键词循环查询，直到满足以下任一条件：
  - offset >= 3000
  - 当前页最老作品发布时间 < (当前时间 - 72小时)
  - 符合条件作品数量 > 50
- 每个关键词查询结束后立即保存

### 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| ENV | 环境类型 | Prod | 否 |
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
| HUEY_REDIS_HOST | HUEY redis 地址 | localhost | 是 |
| HUEY_REDIS_PORT | HUEY redis 端口 | 6479 | 是 |
| HUEY_REDIS_DB  | HUEY redis 库名 | 0 | 是 |
| HUEY_REDIS_PASSWORD | HUEY redis 密码 | - | 否 |
| HUEY_TASK_TIMEOUT | HUEY 任务超时 | 86400 | 否 |
| HUEY_RESULT_TIMEOUT | HUEY 结果缓存时长 | 604800 | 否 |
| HUEY_WORKER_TYPE | HUEY 任务类型 | thread | 否 |
| HUEY_WORKER_COUNT | HUEY 任务数量 | 2 | 否 |
| RATE_LIMIT_NO_KEY | 没有key时的可调用次数 | 10 | 否 |
| RATE_LIMIT_WITH_KEY | 有key时的可调用次数 | 60 | 否 |
| RATE_LIMIT_WINDOW_SECONDS | 限制器计数窗口时间 | 60 | 否 |

## 许可证

本项目仅供学习和研究使用。请遵守Pixiv的服务条款和相关法律法规。

## 贡献

欢迎提交Issue和Pull Request！

## 致谢

- [pixivpy3](https://github.com/upbit/pixivpy3) - Pixiv API Python SDK
- [Bulma](https://bulma.io/) - 前端UI框架

## 联系方式

如有问题或建议，请提交Issue。
