# API密钥使用指南

## 概述

API密钥用于控制公开API的访问频率。当请求未提供有效API密钥时，将应用更严格的速率限制。

## API密钥管理

### 创建API密钥

1. 登录管理后台
2. 导航到 `/config` 页面
3. 滚动到"API密钥管理"部分
4. 输入密钥名称（如：移动端应用、第三方集成等）
5. 点击"创建密钥"按钮
6. **重要**：立即复制并保存密钥，关闭模态框后将无法再次查看完整密钥

### 管理API密钥

- **查看列表**：显示所有API密钥及其状态（密钥已掩码显示）
- **启用/禁用**：可以临时禁用某个密钥而不删除
- **删除**：永久删除密钥（操作不可恢复）

## 使用API密钥

有两种方式在API请求中使用密钥：

### 方式1：HTTP Header（推荐）

```bash
curl -X GET "https://your-domain/api/public/random/artwork?limit=1" \
  -H "X-API-Key: your-api-key-here"
```

### 方式2：Query参数

```bash
curl -X GET "https://your-domain/api/public/random/artwork?limit=1&api_key=your-api-key-here"
```

## 速率限制

### 配置说明

在 `.env` 文件中配置以下参数：

```env
# 无API密钥时的限制次数（每分钟）
RATE_LIMIT_NO_KEY=10

# 有API密钥时的限制次数（每分钟）
RATE_LIMIT_WITH_KEY=60

# 时间窗口（秒）
RATE_LIMIT_WINDOW_SECONDS=60
```

### 限制规则

| 情况 | 每分钟请求数 |
|------|------------|
| 未提供API密钥 | 10次（默认） |
| 提供有效API密钥 | 60次（默认） |
| 提供无效API密钥 | 10次（默认） |

### 响应头

API返回的响应包含以下速率限制信息：

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 1706784000
```

- `X-RateLimit-Limit`：当前时间窗口的限制次数
- `X-RateLimit-Remaining`：剩余可用次数
- `X-RateLimit-Reset`：限制重置的时间戳（Unix时间戳）

### 超出限制

当超出速率限制时，API将返回HTTP 429状态码：

```json
{
  "success": false,
  "message": "Rate limit exceeded",
  "error": "rate_limit_exceeded"
}
```

## 受影响的API

### 需要速率限制

- `GET /api/public/random/artwork` - 获取随机作品

### 不需要速率限制

- `GET /api/public/stats` - 获取统计信息

## 反向代理/CDN支持

系统支持在反向代理或CDN环境下获取真实客户端IP，支持以下代理头：

1. **X-Forwarded-For**（标准代理头，优先级最高）
2. **X-Real-IP**（Nginx等）
3. **CF-Connecting-IP**（Cloudflare）
4. **request.remote_addr**（直连情况）

## 安全建议

1. **保护密钥**：不要将API密钥提交到版本控制系统
2. **定期轮换**：定期创建新密钥并删除旧密钥
3. **最小权限**：为不同的应用场景创建不同的密钥
4. **监控使用**：定期检查密钥的使用统计，发现异常及时处理
5. **及时删除**：不再使用的密钥应立即删除

## 密钥统计

在管理后台可以查看每个密钥的使用统计：

- **使用次数**：该密钥被使用的总次数
- **状态**：密钥当前是启用还是禁用状态
- **创建时间**：密钥的创建时间
- **最后使用时间**：该密钥最后一次被使用的时间

## 故障排查

### 密钥无效

如果收到 "Rate limit exceeded" 但您提供了密钥：

1. 确认密钥是否正确复制（无多余空格）
2. 检查密钥是否已被禁用
3. 确认密钥是否已被删除
4. 查看服务器日志了解详情

### 速率限制仍然触发

即使提供了有效密钥，如果达到限制次数仍会触发速率限制：

1. 查看响应头中的 `X-RateLimit-Remaining` 了解剩余次数
2. 等待时间窗口重置（默认60秒）
3. 考虑增加 `RATE_LIMIT_WITH_KEY` 配置值

## 配置示例

### 严格模式（推荐用于生产环境）

```env
RATE_LIMIT_NO_KEY=5
RATE_LIMIT_WITH_KEY=30
RATE_LIMIT_WINDOW_SECONDS=60
```

### 宽松模式（适用于内网或测试环境）

```env
RATE_LIMIT_NO_KEY=30
RATE_LIMIT_WITH_KEY=300
RATE_LIMIT_WINDOW_SECONDS=60
```

### 禁用速率限制（不推荐）

将限制值设置为一个非常大的数字：

```env
RATE_LIMIT_NO_KEY=10000
RATE_LIMIT_WITH_KEY=10000
RATE_LIMIT_WINDOW_SECONDS=60
```

## 技术实现说明

- **速率限制算法**：基于内存的滑动窗口算法
- **存储方式**：内存字典（单实例部署）
- **支持环境**：反向代理、CDN、直连
- **密钥生成**：使用Python secrets模块生成32字符十六进制密钥
- **使用统计**：每次成功请求自动更新使用次数和最后使用时间