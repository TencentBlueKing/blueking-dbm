# MySQL备份恢复演练信号处理器

## 概述

`mysql_rollback_exercise_handler.py` 是一个专门用于处理MySQL备份恢复演练（MYSQL_ROLLBACK_EXERCISE）单据状态变化的信号处理器。当flow引擎的状态发生变化时，该处理器会自动更新对应的`MySQLBackupRecoverTask`记录的状态。

## 功能特性

### 状态映射

该处理器只维护`phase`与`state`，`task_status`由流程中的`MySQLBackupRecoverTaskMetaComponent`节点更新：

| Flow状态 | phase | 说明 |
|---------|-------|------|
| `StateType.FAILED` | `TaskPhase.DONE` | 流程失败，未恢复成功时`state`置为`abnormal` |
| `StateType.REVOKED` | `TaskPhase.DONE` | 流程撤销，未恢复成功时`state`置为`abnormal` |
| `StateType.FINISHED` | `TaskPhase.DONE` | 节点或流程完成 |
| `StateType.RUNNING` | `TaskPhase.RUNNING` | 流程运行中 |
| `StateType.CREATED` | `TaskPhase.RUNNING` | 流程创建 |
| `StateType.READY` | `TaskPhase.RUNNING` | 流程准备就绪 |

### 耗时记录

流程构建时把全备下载步骤与恢复数据步骤的节点ID写入`exercise_timing_nodes`，节点 FINISHED 信号到达时按节点ID计时（取`FlowNode.started_at/updated_at`），只写一次：

1. **全备下载耗时**：所有下载批次都正常完成（非跳过、非忽略错误）后，写入`backup_download_start_time`（最早开始时间）与`backup_download_duration`（各批次耗时之和，秒）
2. **纯备份恢复耗时**：恢复数据步骤正常完成且`rollback_code == 0`后，按该步骤自身起止时间写入`recover_start_time`、`recover_end_time`、`recover_duration`（秒），不依赖下载耗时
3. binlog 下载与前滚不计入任何耗时

报表中新流程（`exercise_timing_nodes`非空）只展示`recover_duration`，未完成或恢复失败时留空；旧记录仍按起止时间计算。

## 使用方法

### 自动注册

信号处理器通过装饰器`@create_ticket_handler(TicketType.MYSQL_ROLLBACK_EXERCISE)`自动注册到系统中，无需手动调用。

### 触发条件

当以下条件满足时，处理器会自动触发：

1. 单据类型为`MYSQL_ROLLBACK_EXERCISE`
2. Flow引擎状态发生变化
3. 存在对应的`MySQLBackupRecoverTask`记录（通过`task_id`匹配）

### 示例

```python
# 在gen_task.py中创建任务时，确保task_id与flow的root_id一致
task = MySQLBackupRecoverTask(
    task_id=root_id,  # 这个ID会用于匹配flow状态
    task_status=TaskStatus.COMMIT_SUCCESS,
    # ... 其他字段
)

# 启动flow
flow = MySQLRollbackExerciseFlow(root_id=root_id, data=flow_context)
flow.run()

# 信号处理器会自动监听flow状态变化并更新任务状态
```

## 日志记录

处理器会记录详细的日志信息：

- 处理器执行开始
- 任务状态更新成功
- 错误信息获取失败
- 任务未找到的警告
- 未知状态的处理

## 测试

运行测试用例：

```bash
python manage.py test backend.flow.signal.test_mysql_rollback_exercise_handler
```

测试覆盖以下场景：

1. 信号处理器注册验证
2. 失败状态更新
3. 完成状态更新
4. 运行状态更新
5. 任务不存在的情况
6. 未知状态的处理

## 注意事项

1. **任务ID匹配**：确保`MySQLBackupRecoverTask.task_id`与flow的`root_id`一致
2. **错误处理**：处理器包含完整的异常处理，不会因为单个错误影响整个系统
3. **状态一致性**：处理器确保flow状态与任务状态保持同步
4. **国际化支持**：所有日志信息都支持国际化

## 相关文件

- `mysql_rollback_exercise_handler.py` - 信号处理器实现
- `test_mysql_rollback_exercise_handler.py` - 测试用例
- `callback_map.py` - 信号处理器注册机制
- `handlers.py` - 通用信号处理逻辑
