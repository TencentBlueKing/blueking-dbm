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

## 现场保留与人工确认

当 `drill_config.error_ignorable=False`（默认）时，回档演练进入**现场保留模式**：

- 回档/清理子流程 FAILED 或超时后，runner 以业务失败结果正常结束，并进入对应分支的人工确认节点；
- **不撤销子流程、不清理现场**：临时机器/实例/子流程全部保留，供人工排查；
- 报告标为「现场保留待排查」（`SCENE_PRESERVED`，属失败阶段集合），并嵌入子流程失败节点日志；
- 演练单据保持 `RUNNING`，其他并行分支可继续派生和执行子流程。

### DBA 操作步骤

1. 查看失败 runner 节点的日志（页面或报告 `task_message` 中已嵌入子流程失败节点日志）；
2. 登录临时机排查现场（保留期间告警屏蔽已放大到 `preserve_scene_shield_minutes`，默认 72h）；
3. 排查完成后处理「现场保留」人工确认待办；
4. 流程自动沿条件网关（`rollback_code=1`/`delete_code=1`）标记「回档失败/清理失败」，报告由 `SCENE_PRESERVED` 更新为失败终态（演练最终以失败落库）；
5. 汇聚后主流程执行「最佳尝试清理」：先 revoke 残留子流程（含树状态 FAILED 但仍有兄弟节点运行的情况），再清理临时实例，单据转 SUCCEEDED 后回收主机。

### 护栏（自动机制不触碰保留中单据）

- `wakeup_redis_rollback_runner_by_child` 只唤醒仍在运行（RUNNING/CREATED/READY）的 runner 节点；runner 完成后直接返回并清陈旧缓存；
- `repair_stuck_redis_rollback_exercise` 的过滤集合不含 `SCENE_PRESERVED`，保留中报告永不自动唤醒；
- 异常巡检对保留中单据报 `scene_preserved` reason（“现场保留待排查，需完成人工确认后清理”），不误报 `missing_cleanup_child`；
- `REDIS_ROLLBACK_EXERCISE` 单据超时配置全为 `-1`（无超时自动终止/提醒），`auto_clear_expire_flow` 不会触碰现场保留中的演练单据。

### 已知取舍

- runner 节点 `retryable=False`，子流程失败作为业务结果流向人工确认；强制重试时 runner 仍会在提交新子流程前 revoke report 上遗留的非终态旧子流程，避免孤儿现场；
- 停住期间单据保持 RUNNING，持续占用集群互斥，确认并清理后才释放；
- 不做超时自动确认，现场一直保留到人工处理；注意 `clean_bamboo_engine_expired_data`（默认关闭、360 天）按创建时间清理流程数据且不判断终态，现场保留不应跨越数月。

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
