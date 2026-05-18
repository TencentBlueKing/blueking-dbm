# DBHA-v2 Change Log

## unversioned

- 【新增】DBM API 调用统计。
- 【新增】探针（Probe）新增Keepalive工作模式用于辅助二次探测检测主机的存活状态。
- 【新增】运维脚本增加crontab守护配置，启动进程时自动注册crontab守护，stop时自动删除crontab守护配置。
- 【优化】切换流程支持可配置的整体截止时间（`workflow.switchTimeout`）。默认值为 10m；未配置有效值时，回退上限亦为 10m。  
- 【优化】切换链路支持分段超时配置，新增下列项及默认值：  
  - 写切换日志到DB（`switchflow.switchLogWriteTimeout`）：1s  
  - 与DB实例建立连接（`switchflow.dbConnectTimeout`）：3s  
  - 切换时的集群锁等待（`switchflow.clusterLockTimeout`）：60s  
  - 切换步骤内的SQL执行时长（`switchflow.execSqlTimeout`）：6s  
- 【优化】切换调度默认值调整：滑动窗口时长（`workflow.windowDuration`）由 10s 调整为 0。  
- 【优化】切换时访问DBM的并发请求上限（`switchflow.dbmApiMaxConcurrentRequests`）由 16 调整为 8。  
- 【修复】cluster 工具在并行调用 DBM 时，因共用 HTTP 客户端致使各请求超时参数相互覆盖的问题。
- 【修复】滑动窗口 metric 统计的数据残留问题。

