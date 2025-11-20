# 资源状态变更日志使用说明

## 表结构说明

`tb_rp_status_change_log` 表用于记录资源池中机器状态变更的详细日志，包括变更原因和上下文信息。

### 表字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | int(11) | 主键ID |
| bk_host_id | int(11) | bk主机ID |
| ip | varchar(20) | IP地址 |
| bk_cloud_id | int(11) | 云区域ID |
| old_status | varchar(20) | 原状态 |
| new_status | varchar(20) | 新状态 |
| change_reason | varchar(50) | 变更原因类型 |
| reason_detail | text | 详细原因描述 |
| reason_context | json | 变更上下文信息 |
| operator | varchar(64) | 操作者 |
| create_time | timestamp | 创建时间 |

### 状态变更原因类型

- `cc_module_not_allow`: CC模块不在允许范围内
- `host_not_found_in_cc`: 在CC中查询不到主机信息
- `agent_status_abnormal`: Agent状态异常
- `manual_update`: 手动更新
- `system_error`: 系统错误

## 常用查询示例

### 1. 查询特定主机的状态变更历史

```sql
SELECT 
    bk_host_id,
    ip,
    old_status,
    new_status,
    change_reason,
    reason_detail,
    create_time
FROM tb_rp_status_change_log
WHERE bk_host_id = 12345
ORDER BY create_time DESC;
```

### 2. 查询最近24小时内变更为UsedByOther的机器

```sql
SELECT 
    bk_host_id,
    ip,
    change_reason,
    reason_detail,
    reason_context,
    create_time
FROM tb_rp_status_change_log
WHERE new_status = 'UsedByOther'
  AND create_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY create_time DESC;
```

### 3. 按变更原因统计最近7天的状态变更

```sql
SELECT 
    change_reason,
    COUNT(*) as change_count,
    COUNT(DISTINCT bk_host_id) as affected_hosts
FROM tb_rp_status_change_log
WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
  AND new_status = 'UsedByOther'
GROUP BY change_reason
ORDER BY change_count DESC;
```

### 4. 查询CC模块不允许的具体信息（包含业务和模块详情）

```sql
SELECT 
    bk_host_id,
    ip,
    reason_detail,
    JSON_EXTRACT(reason_context, '$.bk_biz_id') as current_biz_id,
    JSON_EXTRACT(reason_context, '$.dedicated_biz') as dedicated_biz_id,
    JSON_EXTRACT(reason_context, '$.bk_set_id') as bk_set_id,
    JSON_EXTRACT(reason_context, '$.bk_module_id') as current_module_id,
    JSON_EXTRACT(reason_context, '$.allowed_modules') as allowed_modules,
    JSON_EXTRACT(reason_context, '$.sub_zone') as sub_zone,
    JSON_EXTRACT(reason_context, '$.city') as city,
    JSON_EXTRACT(reason_context, '$.device_class') as device_class,
    create_time
FROM tb_rp_status_change_log
WHERE change_reason = 'cc_module_not_allow'
  AND create_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY create_time DESC;
```

### 5. 查询在CC中找不到的主机信息（包含主机详细信息）

```sql
SELECT 
    bk_host_id,
    ip,
    reason_detail,
    JSON_EXTRACT(reason_context, '$.bk_biz_id') as current_biz_id,
    JSON_EXTRACT(reason_context, '$.dedicated_biz') as dedicated_biz_id,
    JSON_EXTRACT(reason_context, '$.sub_zone') as sub_zone,
    JSON_EXTRACT(reason_context, '$.city') as city,
    JSON_EXTRACT(reason_context, '$.device_class') as device_class,
    JSON_EXTRACT(reason_context, '$.request_id') as request_id,
    JSON_EXTRACT(reason_context, '$.batch_size') as batch_size,
    JSON_EXTRACT(reason_context, '$.inspection_type') as inspection_type,
    create_time
FROM tb_rp_status_change_log
WHERE change_reason = 'host_not_found_in_cc'
  AND create_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY create_time DESC;
```

### 6. 按业务ID统计状态变更情况

```sql
SELECT 
    JSON_EXTRACT(reason_context, '$.bk_biz_id') as biz_id,
    JSON_EXTRACT(reason_context, '$.sub_zone') as sub_zone,
    change_reason,
    COUNT(*) as change_count,
    COUNT(DISTINCT bk_host_id) as affected_hosts
FROM tb_rp_status_change_log
WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
  AND new_status = 'UsedByOther'
  AND JSON_EXTRACT(reason_context, '$.bk_biz_id') IS NOT NULL
GROUP BY biz_id, sub_zone, change_reason
ORDER BY change_count DESC;
```

### 7. 查询特定园区的状态变更情况

```sql
SELECT 
    bk_host_id,
    ip,
    JSON_EXTRACT(reason_context, '$.bk_biz_id') as biz_id,
    JSON_EXTRACT(reason_context, '$.dedicated_biz') as dedicated_biz_id,
    JSON_EXTRACT(reason_context, '$.sub_zone') as sub_zone,
    JSON_EXTRACT(reason_context, '$.city') as city,
    change_reason,
    reason_detail,
    create_time
FROM tb_rp_status_change_log
WHERE JSON_EXTRACT(reason_context, '$.sub_zone') = '光明'
  AND create_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY create_time DESC;
```

## Go代码使用示例

### 1. 记录状态变更日志（包含完整的主机业务信息）

```go
import "dbm-services/common/db-resource/internal/model"

// 记录CC模块不允许的状态变更，包含完整的主机业务和模块信息
inspectionType := "cc_module_validation"
context := &model.StatusChangeContext{
    // 主机业务信息
    BKBizID:      &machineDetail.BkBizId,
    DedicatedBiz: &machineDetail.DedicatedBiz,
    
    // CC拓扑信息
    BKSetID:        &setID,
    BKModuleID:     &moduleID,
    AllowedModules: []int{allowedModuleID},
    
    // 资源信息
    SubZone:     &machineDetail.SubZone,
    SubZoneID:   &machineDetail.SubZoneID,
    City:        &machineDetail.City,
    CityID:      &machineDetail.CityID,
    DeviceClass: &machineDetail.DeviceClass,
    
    // 其他信息
    RequestID:      &requestID,
    InspectionType: &inspectionType,
}

err := model.LogStatusChange(
    hostID,
    ip,
    cloudID,
    model.Unused,
    model.UsedByOther,
    model.ReasonCCModuleNotAllow,
    fmt.Sprintf("主机所在模块ID[%d]不在允许的资源模块[%d]范围内，当前业务ID[%d]，集合ID[%d]，园区[%s]", 
        moduleID, allowedModuleID, machineDetail.BkBizId, setID, machineDetail.SubZone),
    context,
    "system",
)
```

### 2. 批量记录状态变更日志

```go
logs := []model.TbRpStatusChangeLog{
    {
        BkHostID:     hostID1,
        IP:          ip1,
        BkCloudID:   cloudID,
        OldStatus:   model.Unused,
        NewStatus:   model.UsedByOther,
        ChangeReason: model.ReasonHostNotFoundInCC,
        ReasonDetail: "在CC中查询不到主机信息",
        Operator:    "system",
    },
    // ... 更多日志记录
}

err := model.BatchLogStatusChange(logs)
```

### 3. 查询主机状态变更历史

```go
// 获取主机最近10条状态变更记录
logs, err := model.GetStatusChangeHistory(hostID, 10)
if err != nil {
    logger.Error("get status change history failed: %s", err.Error())
    return
}

for _, log := range logs {
    fmt.Printf("Time: %s, Status: %s -> %s, Reason: %s\n", 
        log.CreateTime.Format("2006-01-02 15:04:05"),
        log.OldStatus, log.NewStatus, log.ChangeReason)
}
```

### 4. 查询指定时间范围的状态变更

```go
startTime := time.Now().Add(-24 * time.Hour)
endTime := time.Now()

// 查询最近24小时内所有CC模块不允许的变更
logs, err := model.GetStatusChangesByTimeRange(
    startTime, 
    endTime, 
    model.ReasonCCModuleNotAllow, 
    100,
)
```

## 业务分析查询示例

### 1. 分析各业务的资源使用情况

```sql
-- 查看各业务在不同园区的资源变更情况
SELECT 
    JSON_EXTRACT(reason_context, '$.bk_biz_id') as biz_id,
    JSON_EXTRACT(reason_context, '$.dedicated_biz') as dedicated_biz,
    JSON_EXTRACT(reason_context, '$.sub_zone') as sub_zone,
    JSON_EXTRACT(reason_context, '$.city') as city,
    change_reason,
    COUNT(*) as total_changes,
    COUNT(DISTINCT bk_host_id) as unique_hosts,
    MIN(create_time) as first_change,
    MAX(create_time) as last_change
FROM tb_rp_status_change_log
WHERE create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
  AND new_status = 'UsedByOther'
  AND JSON_EXTRACT(reason_context, '$.bk_biz_id') IS NOT NULL
GROUP BY biz_id, dedicated_biz, sub_zone, city, change_reason
ORDER BY total_changes DESC;
```

### 2. 查询跨模块异常的主机

```sql
-- 查找经常出现模块异常的主机
SELECT 
    bk_host_id,
    ip,
    JSON_EXTRACT(reason_context, '$.bk_biz_id') as current_biz_id,
    JSON_EXTRACT(reason_context, '$.sub_zone') as sub_zone,
    COUNT(*) as exception_count,
    GROUP_CONCAT(DISTINCT JSON_EXTRACT(reason_context, '$.bk_module_id')) as problem_modules,
    MAX(create_time) as last_exception_time
FROM tb_rp_status_change_log
WHERE change_reason = 'cc_module_not_allow'
  AND create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY bk_host_id, ip
HAVING exception_count >= 3
ORDER BY exception_count DESC, last_exception_time DESC;
```

### 3. 设备类型与状态变更的关联分析

```sql
-- 分析不同设备类型的状态变更模式
SELECT 
    JSON_EXTRACT(reason_context, '$.device_class') as device_class,
    JSON_EXTRACT(reason_context, '$.sub_zone') as sub_zone,
    change_reason,
    COUNT(*) as change_count,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, 
        STR_TO_DATE('1970-01-01 08:00:01', '%Y-%m-%d %H:%i:%s'), 
        create_time)), 2) as avg_hours_since_epoch
FROM tb_rp_status_change_log
WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
  AND JSON_EXTRACT(reason_context, '$.device_class') IS NOT NULL
GROUP BY device_class, sub_zone, change_reason
ORDER BY change_count DESC;
```

## 维护建议

1. **数据清理**: 建议定期清理超过90天的历史记录，保持表性能
2. **索引优化**: 根据实际查询需求，可以添加复合索引，如：
   ```sql
   -- 为JSON字段添加虚拟列索引
   ALTER TABLE tb_rp_status_change_log 
   ADD COLUMN bk_biz_id_virtual INT AS (JSON_EXTRACT(reason_context, '$.bk_biz_id')) STORED,
   ADD INDEX idx_bk_biz_id_virtual (bk_biz_id_virtual);
   ```
3. **监控告警**: 可以基于此表设置告警，监控异常状态变更的频率
4. **数据分析**: 定期分析状态变更原因，优化资源管理策略
5. **业务优化**: 
   - 根据状态变更日志分析业务模块配置是否合理
   - 识别频繁发生异常的园区或设备类型
   - 监控专属业务和当前业务的匹配情况
