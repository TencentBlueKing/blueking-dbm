# 新机器 TCP 内核参数初始化说明

涉及文件：`mysql_os_init.py`

## 背景

- `net.ipv4.tcp_timestamps=1` 用于解决客户端连接偶发因 TIME_WAIT 导致 TCP SYN 重传（约 1s）超时的问题。
- `net.ipv4.tcp_tw_recycle` 在 Linux 内核 **4.12** 中被移除（`/proc/sys/net/ipv4/tcp_tw_recycle` 不存在）。
- 旧内核（< 4.12）上 **不能同时** `tcp_timestamps=1` 且 `tcp_tw_recycle=1`，在 NAT 网络环境下会导致连接不稳定（SYN 被丢弃）。

## 核心原则

1. 新机器内核 >= 4.12：直接设置 `tcp_timestamps=1`。
2. 新机器内核 < 4.12：与老机器保持一致，允许 `ts=0, rc=1`，但不允许 `ts=1 且 rc=1`。

## 执行流程

```
GetOsSysParam (老机器)          SysInit (新机器)
  uname -r                        Python: calc_tcp_sysctl_targets()
  sysctl tcp_timestamps    ──>      根据老机器值，算出 >=4.12 / <4.12 两组目标值
  sysctl tcp_tw_recycle             渲染进 tcp_sysctl_init 脚本
  写入 trans_data.system_info     Shell: uname -r 判断新机器内核，选分支调用 set_sysctl_param
```

1. **采集**：`GetOsSysParam` 在老机器（如老 master）上执行 `get_os_sys_param` 脚本，`<ctx>` JSON 中新增 3 个字段，写入 `trans_data.system_info`：
   - `kernel_release`：`uname -r`，如 `3.10.107-1-tlinux2_kvm_guest-0056`、`5.4.203-1-tlinux4-0011`（仅记录，不参与判断）
   - `tcp_timestamps`：`sysctl -n net.ipv4.tcp_timestamps`
   - `tcp_tw_recycle`：`sysctl -n net.ipv4.tcp_tw_recycle`，参数不存在时为空字符串
2. **计算**：`SysInit._execute` 读取老机器的 `tcp_timestamps` / `tcp_tw_recycle`（非纯数字视为空），调用 `calc_tcp_sysctl_targets()` 得到 4 个模板变量：
   - `ge_412_tcp_timestamps` / `ge_412_tcp_tw_recycle`
   - `lt_412_tcp_timestamps` / `lt_412_tcp_tw_recycle`
   - 空字符串表示 **不设置** 该参数
3. **设置**：`tcp_sysctl_init` 脚本只负责：
   - 解析新机器 `uname -r` 的主次版本号，与 4.12 比较
   - 调用 `set_sysctl_param key val`：值为空或 `/proc/sys/...` 不存在则跳过；否则删除 `/etc/sysctl.conf` 中同名旧配置、追加新值（持久化），并 `sysctl -w`（当前生效）
   - 内核版本解析失败时整体跳过，不影响任务

## 为什么判断的是新机器内核

参数最终设置在新机器上，`tcp_tw_recycle` 是否存在取决于新机器内核。部署前 Python 侧拿不到新机器内核版本：
- 新机器的 `Machine.system_info` 在 MySQL 部署 **之后** 的标准化子流程（`collect_sysinfo`）才写入；
- 资源池返回的 `os_version` 在 `ticket/flow_manager/resource.py::_format_resource_hosts` 中未透传。

因此 Python 预先算好两组值，由 shell 在新机器上按 `uname -r` 选择。

## 目标值对照表

新机器内核 >= 4.12：固定设置 `tcp_timestamps=1`，不设置 `tcp_tw_recycle`。

新机器内核 < 4.12：

| 老机器 ts / rc | 新机器设置 | 说明 |
|---|---|---|
| 1 / 1 | ts=1, rc=0 | 违反原则，强制 rc=0 |
| 1 / 0 | ts=1, rc=0 | 与老机器一致 |
| 1 / 不存在 | ts=1, rc=0 | 老机器内核 >= 4.12 迁移到旧内核 |
| 0 / 1 | ts=0, rc=1 | 允许，与老机器一致 |
| 0 / 0 | ts=0, rc=0 | 与老机器一致 |
| 0 / 不存在 | ts=0, rc 不设置 | |
| 未采集到 | 都不设置 | 由 shell 兜底检查 |

**Shell 兜底**：< 4.12 分支设置完后读取新机器当前值，若为 `ts=1 且 rc=1`，则强制 `rc=0`（同样持久化）。主要覆盖老机器参数未采集到（如新装集群、无老机器）的场景。

## 修改指引

- 调整目标值规则：只改 `calc_tcp_sysctl_targets()`，shell 无需改动。
- 新增需要从老机器继承的内核参数：
  1. `get_os_sys_param` 中采集并加入 `<ctx>` JSON；
  2. `SysInit._execute` 从 `trans_data.system_info` 读取；
  3. 在 `tcp_sysctl_init`（或新的脚本段）中调用 `set_sysctl_param`。
- 注意 `get_os_sys_param` 的 `<ctx>` 输出同时被 `update_machine_system_info_flow` 写入 `db_meta_machine.system_info`，新增字段会一并落库。
