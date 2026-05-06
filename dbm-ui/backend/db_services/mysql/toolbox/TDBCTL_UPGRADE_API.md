# TdbCtl 升级相关 API 文档

## API 概览

TdbCtl 升级功能提供了三种不同的接口，满足不同的使用场景：

| 接口名称 | URL路径 | 执行方式 | 单据 | 使用场景 |
|---------|---------|---------|------|---------|
| `schedule` | `/apis/mysql/toolbox/tdbctl_upgrade/schedule/` | 异步 | 否 | 批量调度升级，全局或按业务 |
| `upgrade` | `/apis/mysql/toolbox/tdbctl_upgrade/upgrade/` | 同步 | 否 | 直接执行升级，无需审批 |
| `create_upgrade_ticket` | `/apis/mysql/toolbox/tdbctl_upgrade/create_upgrade_ticket/` | 异步 | 是 | 创建升级单据，需要审批 |

---

## 1. 创建升级单据（推荐）

### 接口路径
```
POST /apis/mysql/toolbox/tdbctl_upgrade/create_upgrade_ticket/
```

### 功能说明
- 创建 TdbCtl 升级单据
- 单据需要经过审批流程
- 审批通过后自动执行升级
- 适用于生产环境，提供审批和追溯能力

### 请求参数
```json
{
  "bk_biz_id": 100,
  "pkg_id": 123,
  "cluster_ids": [1, 2, 3],
  "upgrade_all": false
}
```

#### 参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `bk_biz_id` | int | 是 | 业务ID |
| `pkg_id` | int | 是 | tdbctl 升级包ID |
| `cluster_ids` | list[int] | 否 | 集群ID列表（如果 upgrade_all=false，此参数必填） |
| `upgrade_all` | bool | 否 | 是否升级业务下所有 spider 集群（默认 false） |

### 响应示例

**成功响应：**
```json
{
  "result": true,
  "message": "升级单据创建成功",
  "data": {
    "ticket_id": 12345,
    "bk_biz_id": 100,
    "pkg_id": 123,
    "cluster_ids": [1, 2, 3],
    "upgrade_all": false
  }
}
```

**失败响应：**
```json
{
  "result": false,
  "message": "参数错误: 升级包不存在"
}
```

### 使用示例

#### 示例 1：升级指定集群
```bash
curl -X POST "http://your-domain/apis/mysql/toolbox/tdbctl_upgrade/create_upgrade_ticket/" \
  -H "Content-Type: application/json" \
  -d '{
    "bk_biz_id": 100,
    "pkg_id": 123,
    "cluster_ids": [1, 2, 3],
    "upgrade_all": false
  }'
```

#### 示例 2：升级业务下所有集群
```bash
curl -X POST "http://your-domain/apis/mysql/toolbox/tdbctl_upgrade/create_upgrade_ticket/" \
  -H "Content-Type: application/json" \
  -d '{
    "bk_biz_id": 100,
    "pkg_id": 123,
    "upgrade_all": true
  }'
```

---

## 2. 同步执行升级（直接执行）

### 接口路径
```
POST /apis/mysql/toolbox/tdbctl_upgrade/upgrade/
```

### 功能说明
- 直接执行 TdbCtl 升级
- 不创建单据，不需要审批
- 同步执行，立即返回结果
- 适用于测试环境或紧急修复

### 请求参数
与 `create_upgrade_ticket` 相同

### 响应示例
```json
{
  "result": true,
  "data": {
    "upgraded_clusters": [1, 2, 3],
    "skipped_clusters": [],
    "message": "升级成功"
  }
}
```

---

## 3. 批量调度升级（异步）

### 接口路径
```
POST /apis/mysql/toolbox/tdbctl_upgrade/schedule/
```

### 功能说明
- 异步批量调度升级
- 支持全局或指定业务范围
- 自动过滤已升级和正在升级的集群
- 按业务串行调度，避免资源冲突

### 请求参数
```json
{
  "pkg_id": 123,
  "bk_biz_ids": [1, 2, 3],
  "batch_size": 20,
  "schedule_interval_seconds": 180
}
```

#### 参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `pkg_id` | int | 是 | tdbctl 升级包ID |
| `bk_biz_ids` | list[int] | 否 | 业务ID列表，为空则升级全部业务 |
| `batch_size` | int | 否 | 每批集群数量（默认 20，范围 1-100） |
| `schedule_interval_seconds` | int | 否 | 每个业务之间的调度间隔（秒，默认 180，范围 0-3600） |

---

## 4. 查询升级进度

### 接口路径
```
POST /apis/mysql/toolbox/tdbctl_upgrade/progress/
```

### 请求参数
```json
{
  "pkg_id": 123,
  "bk_biz_ids": [1, 2, 3]
}
```

### 响应示例
```json
{
  "result": true,
  "data": {
    "total": 100,
    "pending": 20,
    "running": 10,
    "success": 65,
    "failed": 3,
    "skipped": 2
  }
}
```

---

## 5. 查询升级记录

### 接口路径
```
POST /apis/mysql/toolbox/tdbctl_upgrade/records/
```

### 请求参数
```json
{
  "pkg_id": 123,
  "bk_biz_ids": [1, 2, 3],
  "status": "success",
  "cluster_id": 456,
  "limit": 100,
  "offset": 0
}
```

### 响应示例
```json
{
  "result": true,
  "data": {
    "total": 150,
    "records": [
      {
        "cluster_id": 1,
        "cluster_name": "test-cluster",
        "status": "success",
        "start_time": "2026-01-14 10:00:00",
        "end_time": "2026-01-14 10:15:00",
        "message": "升级成功"
      }
    ]
  }
}
```

---

## 使用场景对比

### 场景 1：生产环境升级（推荐）
**使用接口：** `create_upgrade_ticket`

**原因：**
- ✅ 提供审批流程，确保操作可控
- ✅ 单据记录完整，便于追溯
- ✅ 支持定时执行
- ✅ 失败自动通知

**示例：**
```python
# 创建升级单据，等待审批
response = create_upgrade_ticket({
    "bk_biz_id": 100,
    "pkg_id": 123,
    "cluster_ids": [1, 2, 3]
})
ticket_id = response["data"]["ticket_id"]

# 审批通过后，系统自动执行升级
```

### 场景 2：测试环境快速升级
**使用接口：** `upgrade`

**原因：**
- ✅ 无需审批，快速执行
- ✅ 同步返回结果
- ✅ 适合测试验证

**示例：**
```python
# 直接执行升级
response = upgrade({
    "bk_biz_id": 100,
    "pkg_id": 123,
    "cluster_ids": [1, 2, 3]
})
print(response["data"]["message"])
```

### 场景 3：全局批量升级
**使用接口：** `schedule`

**原因：**
- ✅ 支持大规模批量升级
- ✅ 自动过滤和调度
- ✅ 按业务串行，避免冲突
- ✅ 异步执行，不阻塞

**示例：**
```python
# 异步批量调度升级
response = schedule({
    "pkg_id": 123,
    "batch_size": 20,
    "schedule_interval_seconds": 180
})
task_id = response["task_id"]

# 轮询查询进度
progress = get_progress({"pkg_id": 123})
print(f"成功: {progress['success']}, 失败: {progress['failed']}")
```

---

## 注意事项

1. **权限要求**
   - 所有接口都需要 DBManagePermission 权限
   - 创建单据需要对应业务的操作权限

2. **参数验证**
   - `cluster_ids` 和 `upgrade_all` 必须至少提供一个
   - 升级包必须存在且有效
   - 集群必须是 TendbCluster 类型

3. **幂等性**
   - 已升级到目标版本的集群会自动跳过
   - 重复创建单据不会导致重复升级

4. **错误处理**
   - 参数错误返回 400 状态码
   - 系统异常返回 500 状态码
   - 错误信息会记录到日志

---

## 常见问题

**Q: `create_upgrade_ticket` 和 `upgrade` 有什么区别？**

A:
- `create_upgrade_ticket`：创建单据，需要审批，有完整的流程管理
- `upgrade`：直接执行升级，无需审批，立即返回结果

**Q: 如何查看单据执行状态？**

A: 使用单据ID调用单据查询接口：
```python
GET /apis/tickets/{ticket_id}/
```

**Q: 升级失败如何重试？**

A:
- 如果是通过单据创建的，可以在单据详情页面点击重试
- 如果是直接调用 `upgrade`，可以重新调用接口

**Q: 如何取消正在执行的升级？**

A:
- 单据方式：在单据详情页面点击撤销
- 直接执行方式：需要联系管理员手动停止

---

## 版本历史

- **v1.1.1** (2026-01-14)
  - 修复 `create_upgrade_ticket` 接口的 JSON 序列化问题
  - 使用 `TicketType.TENDBCLUSTER_TDBCTL_UPGRADE.value` 确保类型正确

- **v1.1.0** (2026-01-14)
  - 新增 `create_upgrade_ticket` 接口，支持创建升级单据
  - 所有接口支持完整的国际化

- **v1.0.0** (2025-12-01)
  - 初始版本，提供 `schedule`、`upgrade`、`progress`、`records` 接口

---

## 技术说明

### JSON 序列化问题

在实现过程中遇到了 `TypeError: Object of type __proxy__ is not JSON serializable` 错误。

**问题原因：**
- 传入 `Ticket.create_ticket` 的 `ticket_type` 参数应该使用 `.value` 获取字符串值
- 虽然 Django ORM 可以处理枚举对象，但在某些情况下（如立即使用刚创建的对象），枚举对象可能未被转换为字符串

**解决方案：**
```python
# ❌ 错误：直接使用枚举对象
ticket_type=TicketType.TENDBCLUSTER_TDBCTL_UPGRADE

# ✅ 正确：使用 .value 获取字符串值
ticket_type=TicketType.TENDBCLUSTER_TDBCTL_UPGRADE.value
```

**参考实现：**
- `backend/db_services/redis/autofix/bill.py` - 使用 `.value`
- `backend/db_services/mongodb/autofix/mongodb_autofix_ticket.py` - 使用 `.value`
