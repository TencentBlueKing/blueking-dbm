# Changelog

本文件记录 bk-dbmon 的版本变更历史，采用倒序排列。

## [v0.23] - 2026-10-20

### 变更

- 全备前磁盘高利用率清理策略生效范围扩展：由仅 tendisplus 实例生效，扩展为 tendisplus / tendisSSD 均生效，
  且阈值按类型区分：tendisplus 43%（`consts.DiskUsageCleanThreshold`）、tendisSSD 65%（`consts.DiskUsageCleanThresholdSSD`）

### 新增

- binlog 备份前磁盘高利用率清理策略（与 tendisplus 全备清理策略对齐，tendisSSD / tendisplus 均生效）：
  - 发起下一次 binlog 备份前，若数据盘利用率超过 `consts.DiskUsageCleanThresholdBinlog`（75%），
  先清理该实例本地文件未被清理的历史 binlog 备份文件和 sqlite 记录（每次最多清理最旧的 10 个，多轮渐进清理）
  - 清理前轮询保护：正在上传备份系统的文件（上传进程持有文件句柄，删除后空间不立即释放），
  每 1 分钟轮询上传任务状态，待上传结束（成功/失败）后再删除；
  与全备单文件最多等待 1 小时不同，binlog 文件数量多，所有文件的等待总时长上限为 1 小时，
  超时仍在上传则记录 error 日志后继续删除，不无限阻塞
  - 清理后检查被清理的备份是否已成功上传备份系统，未上传成功仅记录 error 日志，不截断清理流程
  - 单个文件/记录删除失败仅记录 error 日志并继续清理其余文件，下次任务对未清理成功的继续重试
  - data1（数据盘）空间保护：数据盘利用率达到 90%（`consts.DiskUsageForceCleanThreshold`）时，
  无论备份盘是否超阈值都会触发清理，且不再等待上传备份系统任务结束，直接强制删除本地文件，力保数据盘；
  等待上传过程中每轮轮询实时监测数据盘，达到 90% 立即中断等待强制清理

## [v0.22] - 2026-10-16

### 变更

- 修复 `redisbinlogbackup` 清理天数错误引用全备配置的 bug（`job.go` `DeleteTooOldBinlogbackup`）：
  - 原实现误用 `redis_fullbackup.old_file_left_day`，导致 `redis_binlogbackup.old_file_left_day` 配置不生效；
  现已改读 binlog 自身配置（未配置时默认 3 天不变）

### 新增

- 全备前磁盘高利用率清理策略（仅 tendisplus 实例生效）：
  - 发起下一次全备前，若数据盘利用率 > 50%（`consts.DiskUsageCleanThreshold`），
  先清理该实例上一次备份的本地文件和 sqlite 记录
  - 清理前轮询保护：若上一次备份正在上传备份系统（上传进程持有文件句柄，删除后空间不立即释放），
  每 1 分钟轮询上传任务状态、最多等待 1 小时，待上传结束（成功/失败）后再删除；
  超时仍在上传则记录 error 日志后继续删除，不无限阻塞
  - 清理后检查该备份是否已成功上传备份系统，未上传成功仅记录 error 日志，不截断清理流程

- keylifecycle 离线分析任务（大key/key模式统计）：tendisplus 支持按 **kvstore 维度**分析
  - 每个 kvstore（独立 rocksdb）单独 `tscan` 导出 keys（`v.<port>.<db>.keys`）、单独执行 keystat，
    不再将整个实例的 key 合并成一份统一分析（`bigAndMode4TendisPlus`）
  - 每个维度产出独立的报告文件：`tendis.keystat.bigkeys.<port>.<db>.info`、`tendis.keystat.keymode.<port>.<db>.info`
  - cache（rdb/aof）、TendisSSD、热key 路径保持原有整实例粒度不变
- 上报前按**实例维度聚合** tendisplus 各 kvstore 的统计结果，再统一写入上报文件
  （`dbareport/keylifecycle/redis_bigkey_*.log` / `redis_keymode_*.log`）：
  - 大key：各 kvstore 榜单按 `sortby` 分组合并，按 `valsize` 降序重排、重编 `top_idx`，
    截取每个维度 topN（实例 topN 的大key必然在其所属 kvstore 的 topN 内，聚合结果即实例真实 topN）；
    记录保留 `db` 字段标识大key所在 kvstore
  - key模式：按 `(key_type, partten)` 合并，`count`/`keys_expired`/`keys_nottl` 累加，
    `avg_fileds`/`avg_valsize` 按 count 加权平均，`max_*` 取最大，`samples` 去重合并，
    按 `count` 降序重排、重编 `top_idx`（注：模式需进入至少一个 kvstore 的 topN 才会被聚合到，结果为近似 topN）
- 临时文件（`v.*.keys`）清理策略：
  - 产生即登记，`RunStat` 退出时 defer 统一清理（任意退出路径：正常结束/出错返回/跳过实例）
  - 每轮任务启动时兜底清扫历史遗留文件（覆盖进程被杀、panic 等未走正常清理的场景）
- `stop.sh` / `restart.sh` / `start.sh` 增加遗留临时 keys 文件清理
  （均在确认进程已停止/未运行后执行，避免误删分析中的文件），覆盖重启、重装、进程被 kill -9 后 crontab 拉起等场景


- 版本号 `v0.21` → `v0.22`
