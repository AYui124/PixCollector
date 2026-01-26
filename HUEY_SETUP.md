# Huey任务队列使用指南

## 概述

本项目已集成Huey任务队列系统，用于处理长时间运行的采集任务，避免Gunicorn HTTP超时问题。

## 架构说明

### 组件说明

1. **Redis** - 任务队列和结果存储
2. **Huey Worker** - 异步任务执行器
3. **Web服务** - 接收任务请求并返回task_id
4. **Scheduler** - 定时任务调度器

### 工作流程

```
用户点击采集按钮
    ↓
Web服务接收请求，提交Huey任务
    ↓
立即返回task_id给前端
    ↓
前端显示任务进度模态框
    ↓
每3秒轮询一次任务状态
    ↓
Huey Worker在后台执行采集任务
    ↓
任务完成后前端显示结果
```

## Docker Compose服务

### 新增服务

```yaml
redis:
  image: redis:7-alpine
  # Redis作为任务队列和结果存储

huey:
  image: pixcollector:latest
  command: python huey_run.py
  # Huey Worker进程，执行异步任务
```

## 配置说明

### 环境变量

在`.env`文件中配置：

```bash
# Redis配置
REDIS_HOST=localhost           # Redis主机地址
REDIS_PORT=6379              # Redis端口
REDIS_DB=0                   # Redis数据库
REDIS_PASSWORD=               # Redis密码（可选）

# Huey配置
HUEY_TASK_TIMEOUT=86400       # 任务超时时间（秒），默认24小时
HUEY_RESULT_TIMEOUT=604800    # 结果保留时间（秒），默认7天
HUEY_WORKER_TYPE=thread       # Worker类型：thread/process/gevent
HUEY_WORKER_COUNT=2          # Worker数量
```

## 使用说明

### 1. 启动服务

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f huey
```

### 2. 前端使用

当用户点击采集按钮时：
- 立即收到"任务已提交"提示
- 弹出任务进度模态框
- 每3秒自动更新任务状态
- 任务完成后显示结果

### 3. 查看任务状态

任务状态查询API：

```http
GET /api/collect/task/<task_id>
```

返回示例：

```json
{
  "success": true,
  "task_id": "uuid",
  "status": "running",
  "result": null,
  "metadata": {},
  "log": {
    "id": 1,
    "log_type": "ranking_works",
    "status": "running",
    "message": "Collecting daily ranking...",
    "artworks_count": 50
  }
}
```

## 开发调试

### 同步执行模式

开发环境可以设置同步执行：

```python
# core/huey.py
huey = RedisHuey(
    'pixcollector',
    url=Config.REDIS_URL,
    always_eager=True,  # 设置为True同步执行
    ...
)
```

### 本地运行Worker

```bash
# 安装依赖
pip install -r requirements.txt

# 启动Redis
docker run -d -p 6379:6379 redis:7-alpine

# 启动Worker
python huey_run.py
```

## 常见问题

### 1. 任务一直显示"运行中"

**原因**：Worker未正常启动或崩溃

**解决**：
```bash
# 查看Worker日志
docker-compose logs huey

# 重启Worker
docker-compose restart huey
```

### 2. Redis连接失败

**原因**：Redis未启动或配置错误

**解决**：
```bash
# 检查Redis状态
docker-compose ps redis

# 测试Redis连接
docker exec -it pixcollector-redis redis-cli ping
```

### 3. 任务超时

**原因**：任务执行时间超过`HUEY_TASK_TIMEOUT`

**解决**：增加超时配置
```bash
HUEY_TASK_TIMEOUT=172800  # 48小时
```

### 4. Worker数量不足

**原因**：并发任务过多，Worker处理不过来

**解决**：增加Worker数量
```bash
HUEY_WORKER_COUNT=4
```

## 监控和维护

### 查看任务队列

```bash
# 进入Redis容器
docker exec -it pixcollector-redis redis-cli

# 查看队列长度
LLEN huey

# 查看结果键数
KEYS huey:result:*
```

### 清理旧任务结果

Huey会自动清理过期的任务结果，基于`HUEY_RESULT_TIMEOUT`配置。

手动清理：

```bash
# 清理所有结果
docker exec -it pixcollector-redis redis-cli FLUSHDB
```

**警告**：这会清空所有数据，请谨慎使用。

## 性能优化

### 1. Worker类型选择

- **thread**：轻量级，适合IO密集型任务（推荐）
- **process**：重量级，适合CPU密集型任务
- **gevent**：协程，高并发，需要安装gevent

```bash
HUEY_WORKER_TYPE=process  # CPU密集型任务
```

### 2. Worker数量调整

根据服务器配置和任务类型调整：

```bash
# 2核CPU
HUEY_WORKER_COUNT=2

# 4核CPU
HUEY_WORKER_COUNT=4

# 8核CPU
HUEY_WORKER_COUNT=8
```

### 3. Redis持久化

默认开启AOF持久化：

```yaml
redis:
  command: redis-server --appendonly yes
```

## 升级部署

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose build

# 3. 停止旧服务
docker-compose down

# 4. 启动新服务
docker-compose up -d

# 5. 检查服务状态
docker-compose ps
```

## 迁移说明

从同步执行迁移到异步执行：

1. 确保Redis服务正常运行
2. 启动Huey Worker
3. 更新前端代码（已完成）
4. 测试任务提交和状态查询
5. 部署到生产环境

## 回滚方案

如果需要回滚到同步执行模式：

1. 修改`core/huey.py`设置`always_eager=True`
2. 移除或停止Huey Worker
3. 重启Web服务

## 技术支持

如有问题，请查看：

1. Worker日志：`docker-compose logs huey`
2. Web日志：`docker-compose logs web`
3. Redis状态：`docker-compose logs redis`