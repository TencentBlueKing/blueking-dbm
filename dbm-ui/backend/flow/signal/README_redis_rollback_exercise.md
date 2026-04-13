# Redis回档演练信号处理说明

## 概述

`redis_rollback_exercise_handler.py` 用于处理 Redis 回档演练相关子单据的状态回调，目标是让主流程中的 `FlowRunner` 在子流程终态后尽快被唤醒，避免因轮询任务丢失或调度锁异常导致主流程长期卡住。

该机制专门服务于 `REDIS_ROLLBACK_EXERCISE` 场景，不额外注册独立的 `post_set_state` 处理器，而是复用通用回调分发链路。

## 关键能力

### 1) 子单据类型注册

通过 `@create_ticket_handler(...)` 注册以下子单据类型：

- `TicketType.REDIS_DATA_STRUCTURE`
- `TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE`

当对应子流程状态变更时，通用信号处理器会路由到这里执行。

### 2) Drill 场景保护（is_drill guard）

处理器仅在父单据类型为 `TicketType.REDIS_ROLLBACK_EXERCISE` 时执行唤醒逻辑：

- 非演练单据直接忽略
- 仅终态触发（`FINISHED` / `FAILED` / `REVOKED`）

这保证了回调逻辑不会影响普通 Redis 流程。

### 3) 主流程 Runner 唤醒

`wakeup_redis_rollback_runner_by_child(...)` 的核心步骤：

1. 通过 `RedisRollbackExerciseReport` 中的 `rollback_flow_obj_id/delete_flow_obj_id` 反查子流程关联报告
2. 使用 `report.ticket_id` 反查父流程 `root_id`（不改表结构）
3. 在父流程运行中节点里定位与该 `child_root_id` 对应的 runner 节点
4. 清理 `Schedule.scheduling=True` 且未完成的陈旧锁
5. 调用 `BambooEngine.callback(...)` 触发 runner 立即进入下一轮 `_schedule`

## 为什么需要清理 Schedule 锁

在滚动升级或 worker 异常中断场景下，schedule 任务可能在持锁阶段退出，导致 `scheduling=True` 长时间残留。  
此时即使子流程已结束，主流程轮询也可能无法继续推进。

在回调前显式执行锁修复，可以提升恢复成功率，并且该操作是幂等、可重复调用的。

## 周期兜底任务

`db_periodic_task/local_tasks/redis_backup_rollback/task.py` 中的 `repair_stuck_redis_rollback_exercise` 提供二级保障：

- 扫描超过 `polling_timeout` 且仍在中间阶段的报告
- 若子流程已终态，复用同一个 `wakeup_redis_rollback_runner_by_child(...)` 进行修复
- 若超过 `3 * polling_timeout` 仍异常，输出告警日志用于可观测性

## 触发链路（简版）

1. 子流程状态进入终态  
2. `post_set_state` 通用处理器按 `ticket_type` 分发到 redis 回调处理函数  
3. 命中 drill 场景保护后执行 wakeup  
4. runner 收到 callback 并尝试快速完成主流程调度

## 相关文件

- `redis_rollback_exercise_handler.py`：Redis 回调与唤醒实现
- `callback_map.py`：`create_ticket_handler` 注册机制
- `handlers.py`：通用 `post_set_state` 分发入口
- `test_redis_rollback_exercise_handler.py`：信号处理单测
- `db_periodic_task/local_tasks/redis_backup_rollback/task.py`：周期修复任务
