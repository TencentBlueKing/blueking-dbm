# MySQL备份恢复演练信号处理器

## 概述

`mysql_rollback_exercise_handler.py` 是一个专门用于处理MySQL备份恢复演练（MYSQL_ROLLBACK_EXERCISE）单据状态变化的信号处理器。当flow引擎的状态发生变化时，该处理器会自动更新对应的`MySQLBackupRecoverTask`记录的状态。

## 功能特性

### 状态映射

该处理器实现了以下flow状态到任务状态的映射：

| Flow状态 | 任务状态 | 说明 |
|---------|---------|------|
| `StateType.FAILED` | `TaskStatus.COMMIT_FAILED` | 流程失败 |
| `StateType.REVOKED` | `TaskStatus.COMMIT_FAILED` | 流程撤销 |
| `StateType.FINISHED` | `TaskStatus.RECOVER_SUCCESS` | 流程完成，恢复成功 |
| `StateType.RUNNING` | `TaskStatus.COMMIT_SUCCESS` | 流程运行中 |
| `StateType.CREATED` | `TaskStatus.COMMIT_SUCCESS` | 流程创建 |
| `StateType.READY` | `TaskStatus.COMMIT_SUCCESS` | 流程准备就绪 |

### 特殊处理

1. **成功完成时**：
   - 更新`recover_end_time`为当前时间
   - 设置`status`字段为`True`（巡检结果正常）

2. **失败时**：
   - 尝试从flow engine获取错误信息并记录到`task_info`字段
   - 设置`status`字段为`False`（巡检结果异常）

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
