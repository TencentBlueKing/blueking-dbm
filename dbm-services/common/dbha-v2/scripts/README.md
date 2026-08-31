# DBHA v2 Scripts Usage

本文档说明 `scripts` 目录下各脚本的用途与使用方式。

## 目录说明

- `deploy.sh`: 部署与更新脚本（支持按模块安装）
- `render_configs.py`: 按模块用 `etc/dbha-v2.{server,probe}.rc` 与 `etc/templates/*.yaml` 渲染 `etc/*.yaml`
- `compare_probe_config.py`: 校验本地 probe YAML 并检查 health / guard / cron（仅 Linux probe 包）。`-l` 必填；`-r` 与 `--admin-endpoints` 二选一。现场：`./compare_probe_config.py -l etc/probe.yaml --admin-endpoints 127.0.0.1:19001`（可加 `--cloud-id` / `--local-ip` / `--timeout`）。用 `--admin-endpoints` 时会调用 `dbha-probe gen-config` 拉 Admin 最新配置，按 gen-config 树上的 key/value 与本地比对（本地多出的 `admin` 等字段忽略）。`-r` 为离线整树比对，不连 Admin。
- `setup.sh`: 交互式配置生成脚本（仅 server 侧使用）
- `start-server.sh`: 启动 server 侧服务（admin/receiver/analysis）
- `stop-server.sh`: 停止 server 侧服务（admin/receiver/analysis）
- `start-probe.sh`: 启动 probe 服务
- `start-probe-keepalive.sh`: 后台启动 probe keepalive 模式（ping-only）
- `stop-probe-keepalive.sh`: 停止 keepalive 模式并注销 crontab 守护
- `stop-probe.sh`: 停止 probe 服务
- `start-probe.ps1` / `stop-probe.ps1`: Windows 下启动/停止 probe 服务（PowerShell 版）
- `start-probe-keepalive.ps1` / `stop-probe-keepalive.ps1`: Windows 下启动/停止 probe keepalive 模式
- `install-libs.sh`: 安装构建依赖（abseil/protobuf/protoc 插件）
- `devenv.rc`: 本地开发环境变量示例
- `probe-sandbox-full.sh`: 本地 mock 全链路（gen-config → 采集 → 上报），见 [probe-sandbox-mock README](../tools/cmd/probe-sandbox-mock/README.md)

## render_configs.py

根据占位符模板生成运行用的配置文件（默认覆盖 `etc/*.yaml`），**按模块**渲染：

- `--module server`：仅渲染 `admin.yaml`、`analysis.yaml`、`receiver.yaml`
- `--module probe`：仅渲染 `probe.yaml`

```bash
# 在 dbha-v2 根目录执行；按模块复制并编辑 rc
# server 节点
cp etc/dbha-v2.server.rc.example etc/dbha-v2.server.rc
python3 scripts/render_configs.py --module server \
  --rc etc/dbha-v2.server.rc \
  --ip-detect-udp-connect-host 127.0.0.1

# probe 节点
cp etc/dbha-v2.probe.rc.example etc/dbha-v2.probe.rc
python3 scripts/render_configs.py --module probe \
  --rc etc/dbha-v2.probe.rc \
  --ip-detect-udp-connect-host 127.0.0.1

# 也可显式指定模板/输出目录
python3 scripts/render_configs.py --module server \
  --ip-detect-udp-connect-host 127.0.0.1 \
  --rc /path/to/dbha-v2.server.rc \
  --template-dir /path/to/etc/templates --out-dir /path/to/etc
```

- 模板语法：`{{VAR_NAME}}`；可为空字符串的字段在模板中使用 `"{{VAR_NAME}}"`，避免渲染成 YAML null。
- **`--module` 必填**：渲染脚本只读取/校验当前模块所需占位符；缺失另一模块的键不会报错。
- **公共键 `COMMON_*`**：server rc 中包含全部 `COMMON_*`；probe rc 仅包含 probe 模板使用的 `COMMON_VERSION` / `COMMON_LOG_*`。
- **无脚本内建默认值**：所有 `{{PLACEHOLDER}}` 必须在对应 rc 中赋值；可参考 `dbha-v2.server.rc.example` 与 `dbha-v2.probe.rc.example`。
  - **例外**（仅 server 模块；下列键未设置或留空时由脚本推断，均在 stderr 提示）：
    1. `ADMIN_APM_LISTEN_ADDRESS` → `http://<本机检测 IPv4>:50080`（失败则为 `http://127.0.0.1:50080`）。
    2. `RECEIVER_APM_LISTEN_ADDRESS` → `http://<本机检测 IPv4>:50081`（失败则为 `http://127.0.0.1:50081`）。
    3. `ANALYSIS_APM_LISTEN_ADDRESS` → `http://<本机检测 IPv4>:50082`（失败则为 `http://127.0.0.1:50082`）。
    4. `RECEIVER_SOURCE_PROBE_ENDPOINT` → `<本机检测 IPv4>:50052`（失败则为 `127.0.0.1:50052`）。
    5. `ADMIN_GRPC_LISTEN_ADDRESS` → `<本机检测 IPv4>:50051`；若仅为 `:<端口>` 则补全主机段。
    6. `ADMIN_WEB_LISTEN_ADDRESS` → `http://<本机检测 IPv4>:50060`（失败则为 `http://127.0.0.1:50060`）。
    7. `PROBE_INSTALL_DIR` / `ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD` → 默认 `/usr/local/dbha-v2` 与 `cd /usr/local/dbha-v2 && ./bin/dbha-probe health -j`（与 `deploy.sh -t` 及 `start-probe.sh` 一致）。
  - 「本机检测 IPv4」依赖必填参数 `--ip-detect-udp-connect-host`（UDP connect 对端；与上列 (1)–(6) 同一策略）。
- **receiver `service.source` 分片（server）**：`RECEIVER_SOURCE_PROBE_SHARD_FILE` / `RECEIVER_SOURCE_KAFKA_SHARD_FILE` 各对应一类 source 列表项（默认见 `templates/snippets/receiver_source_probe.yaml`、`receiver_source_kafka.yaml`），占位符与 rc 中 `RECEIVER_SOURCE_PROBE_*` / `RECEIVER_SOURCE_KAFKA_*` 一致。
- **probe client（probe）**：`probe.yaml` 的 `client.*` 可配置 probe 侧 gRPC client 的 keepalive/msg size，以及 receiver client 的重连参数；未设置时回退到内置默认值。
- **probe harvester 凭据由 admin 下发（server）**：admin 通过 `GetProbeConfig` 把 `probeMysql` / `probeRedis` 段返回给 probe，probe 侧 `genconfig` 不再硬编码用户名/密码/采集间隔；只有当请求 probe 的元数据包含对应集群家族时才下发对应段。
  - `ADMIN_PROBE_MYSQL_USER` / `ADMIN_PROBE_MYSQL_PASSWORD` / `ADMIN_PROBE_MYSQL_INTERVAL`：仅当 probe 元数据包含 MySQL 系列（`tendbha` / `tendbcluster`）时返回。
  - `ADMIN_PROBE_REDIS_USER` / `ADMIN_PROBE_REDIS_PASSWORD` / `ADMIN_PROBE_REDIS_INTERVAL` / `ADMIN_PROBE_REDIS_TIMEOUT`：仅当 probe 元数据包含 Redis 系列（`redis` / `twemproxy*` / `predixy*`）时返回。
  - 留空或 `0` 视为未设置，将以零值（空字符串）渲染入 `probe.yaml`。
- **receiver `service.sink` mysql 分片（server）**：`RECEIVER_SINK_MYSQL_SHARD_FILE`（默认 `templates/snippets/receiver_sink_mysql.yaml`），占位符为 `RECEIVER_SINK_MYSQL_*`。
- **probe 分片（probe）**：`PROBE_MYSQL_SHARD_FILE` / `PROBE_REDIS_SHARD_FILE` 分别描述 `harvester.mysql` / `harvester.redis`（默认见 `templates/snippets/`）。MySQL / Redis 的 `endpoints[0]` 字段通过 `PROBE_MYSQL_EP_*` / `PROBE_REDIS_EP_*` 在 rc 中配置并由分片模板渲染；`PROBE_REDIS_SHARD_ENABLED=0` 时不生成 `redis:` 段。
- 若已安装 PyYAML，渲染后会做语法校验；可用 `--no-validate-yaml` 跳过。

发布包：
- server 包（`$(VERSION)-server.tar.gz`）携带 `render_configs.py`、`etc/templates/`、`etc/dbha-v2.server.rc.example`、`toolkits/dbha-cluster`、`toolkits/dbha-bwmgr`、`etc/cluster.yaml`、`etc/bwmgr.yaml`
- probe 包（`$(VERSION)-probe.tar.gz`）携带 `render_configs.py`、`compare_probe_config.py`、`etc/templates/`、`etc/dbha-v2.probe.rc.example`

## deploy.sh

### 用法

```bash
./deploy.sh -m <mode> -r <module> -s <source> -t <target> [options]
```

- `-m <mode>`: 部署模式，`install | update`
- `-r <module>`: 模块类型，`server | probe`
- `-s <source>`: 源目录（包含 `bin/`，可选 `etc/`、`toolkits/`、脚本文件）
- `-t <target>`: 目标安装目录
- `--no-restart`: `update` 模式下跳过停启服务
- `-y`: 自动确认
- `-h, --help`: 查看帮助

### 模块行为

- `server`:
  - 安装/更新 `dbha-admin`、`dbha-receiver`、`dbha-analysis`
  - 安装/更新 `admin.yaml`、`receiver.yaml`、`analysis.yaml`（仅 `install` 下发；`update` 跳过）
  - install 时下发 `etc/cluster.yaml`、`etc/bwmgr.yaml`（toolkit 配置模板）
  - 安装/更新 `toolkits/dbha-cluster`、`toolkits/dbha-bwmgr`（`install` 与 `update` 均更新二进制）
  - 安装 `setup.sh`、`start-server.sh`、`stop-server.sh`、`deploy.sh`
  - 处理 `toolkits/`（部署与 backup）
  - 依赖 `lib/guard-utils.sh`，发布包需包含 `lib/` 目录
  - **存量环境**：仅执行 `deploy update` 会更新 toolkit 二进制，不会自动新增或覆盖 `etc/cluster.yaml` / `etc/bwmgr.yaml`；需从包内手工复制或在新装时确认覆盖
- `probe`:
  - 安装/更新 `dbha-probe`
  - 安装/更新 `probe.yaml`
  - 安装 `start-probe.sh`、`stop-probe.sh`、`start-probe-keepalive.sh`、`stop-probe-keepalive.sh`、`deploy.sh`、`compare_probe_config.py`
  - 不安装 `setup.sh`，不处理 `toolkits/`
  - 依赖 `lib/guard-utils.sh`，发布包需包含 `scripts/lib/` 目录

### 示例

```bash
# server 侧全新安装
./deploy.sh -m install -r server -s /tmp/dbha-v2 -t /usr/local/dbha-v2

# probe 侧全新安装
./deploy.sh -m install -r probe -s /tmp/dbha-v2 -t /usr/local/dbha-v2

# server 侧更新（自动停启）
./deploy.sh -m update -r server -s /tmp/dbha-v2 -t /usr/local/dbha-v2

# probe 侧更新（不重启）
./deploy.sh -m update -r probe -s /tmp/dbha-v2 -t /usr/local/dbha-v2 --no-restart
```

## analysis detector / checkProbeProcessCmd

analysis 对漏采实例做 SSH 二次探测时，远程执行 `detector.checkProbeProcessCmd`。标准形态（与 probe 安装布局一致）：

```bash
cd /usr/local/dbha-v2 && ./bin/dbha-probe health -j
```

- `/usr/local/dbha-v2`：须与 `deploy.sh -t` 安装目录一致（`PROBE_INSTALL_DIR`）。
- `./bin/dbha-probe`：与 `start-probe.sh` 使用的二进制路径一致。
- `health -j`：输出 JSON，供 analysis 解析 probe 进程状态。

配置途径：

1. **推荐**：`dbha-v2.server.rc` 中设置 `PROBE_INSTALL_DIR` 与 `ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD`，再执行 `render_configs.py --module server`。
2. **交互式**：`setup.sh` → Setup analysis，会提示 probe 安装目录并写入 `etc/analysis.yaml`。

若 probe 安装在其他路径（例如 `/home/mysql/dbha-v2`），在 server rc 中覆盖 `PROBE_INSTALL_DIR` 与 `ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD` 中的路径即可。

显式覆盖 `ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD` 时，`render_configs.py` 不做全量命令白名单校验；analysis 启动时 `config.Load()` 仍为最终门禁。

验证（开发/CI）：

```bash
cd dbm-services/common/dbha-v2
python3 -m unittest scripts.test_render_configs_detector
```

## setup.sh（仅 server）

`setup.sh` 是交互式配置向导，用于生成 `etc/*.yaml` 配置文件。

```bash
cd /usr/local/dbha-v2
./setup.sh
```

菜单支持：

- 一次性配置全部服务
- 分别配置 `admin` / `receiver` / `analysis` / `probe`
- 重新配置公共参数

> 建议在 server 侧执行；probe 侧通常不需要该脚本。

## start-server.sh / stop-server.sh

用于批量管理 server 侧三个服务：`admin`、`receiver`、`analysis`。
脚本会注册/注销 crontab 守护，并在执行时同时打屏和写系统日志：
`${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}/dbha-v2-admin.log`、
`${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}/dbha-v2-receiver.log`、
`${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}/dbha-v2-analysis.log`。
`start-server.sh` 支持 `--service` 精确启动单个服务，并对空值/越界参数直接报错退出。

```bash
cd /usr/local/dbha-v2
./start-server.sh
./stop-server.sh

# 仅启动单个服务
./start-server.sh --service admin
./start-server.sh --from-cron --service receiver
```

`--service` 错误示例：

```bash
# invalid
./start-server.sh --service
./start-server.sh --service --from-cron
```

## start-probe.sh / stop-probe.sh / start-probe-keepalive.sh / stop-probe-keepalive.sh

用于管理 probe 服务。`start-probe.sh` / `start-probe-keepalive.sh` 通过 Go 子命令 `ensure` / `ensure-keepalive` 纠偏进程形态（InstallRoot chdir + 互斥锁）；crontab 每分钟直接调用  
`cd "$SCRIPT_DIR" && ./bin/dbha-probe ensure -c etc/probe.yaml --from-cron`（keepalive 同理 `ensure-keepalive`）。Linux keepalive 状态文件仍在 XDG runtime（`${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/runtime`），与 Windows 的 `InstallRoot/runtime` 分叉。
`--ping-http-addr` 必须是 `host:port` 或 `[host]:port` 格式，端口范围 `1-65535`；IPv6 地址须使用方括号格式。
`start-probe.sh` / `stop-probe.sh` 会注册/注销 probe crontab 守护，关键步骤写入  
`${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}/dbha-v2-probe.log`。
crontab 注销按 marker 精确过滤后回写；可用 `ps -ef | grep dbha-` 与 `crontab -l | grep DBHA_V2_` 核对。

```bash
cd /usr/local/dbha-v2
./start-probe.sh
./start-probe-keepalive.sh --ping-http-addr 127.0.0.1:18080
./stop-probe-keepalive.sh
./stop-probe.sh
```

地址参数示例：

```bash
# valid
./start-probe-keepalive.sh --ping-http-addr 127.0.0.1:18080
./start-probe-keepalive.sh --ping-http-addr localhost:5001
./start-probe-keepalive.sh --ping-http-addr [::1]:18080

# invalid
./start-probe-keepalive.sh --ping-http-addr 127.0.0.1
./start-probe-keepalive.sh --ping-http-addr 1.1.1.1:70000
./start-probe-keepalive.sh --ping-http-addr ::1:18080
```

keepalive 校验：

```bash
curl http://127.0.0.1:18080/ping
ps -ef | grep dbha-v2-keepalive
crontab -l | grep DBHA_PROBE_KEEPALIVE_GUARD
```

## Windows: start-probe.ps1 / stop-probe.ps1 / start-probe-keepalive.ps1 / stop-probe-keepalive.ps1

Windows 平台使用 PowerShell 脚本管理 probe，与 Linux 的 `*.sh` 一一对应，CLI 语义一致（`daemon-start` / `stop` / keepalive）。二进制为 `bin\dbha-probe.exe`（由 `make probe-windows` 构建、`make package-probe-windows` 打包为 `*-probe-windows.zip`）。

停止模型与 Linux 不同：Linux 用 POSIX 信号（SIGTERM/SIGKILL/SIGHUP），Windows 用**命名事件**（**`Global\`** 命名空间）。Session 0 的 SYSTEM 常驻进程创建事件后，交互会话里的 `stop` / `stop-probe.ps1` 才能 `OpenEvent`（`Local\` 是按会话隔离的，跨会话会失效）。`CreateEvent` 写入 DACL：SYSTEM/Administrators 全权限，Authenticated Users 至少 `EVENT_MODIFY_STATE|SYNCHRONIZE`。创建 `Global\` 对象通常需要 **SeCreateGlobalPrivilege**（Administrators/SYSTEM 具备），因此 Windows 常驻必须以**管理员**注册并由 SYSTEM 拉起；**禁止**非特权交互 `daemon-start` 静默回退 `Local\`。

`stop-probe.ps1` 两段式停止——先 `dbha-probe.exe stop`（置位 Global 停止事件优雅退出），若仍存活再 `Stop-Process` 强杀；强杀前校验可执行路径与 StartTime（对齐 Linux）。升级场景：旧进程仍听 `Local\`，新二进制的优雅停对其无效，**必须依赖 Stage2 强杀**；脚本与二进制需同包升级。

keepalive 不持有由 Go 管理的 pid 文件（脚本/`ensure-keepalive` 写 `runtime\probe-keepalive.pid` / `.addr`），停止事件名按 `--ping-http-addr` 派生：`Global\dbha-probe-<sha1(addr) 前16位十六进制>-stop`（与 `pkg/process/eventname.go` 一致）。

周期保活下沉到 Go：`ensure` / `ensure-keepalive`（`chdir` 到 InstallRoot=`exe/..`，取 `pids/*.ensure.lock` 互斥，抢锁失败退出 0）。管理员执行 `start-probe.ps1`：**先 stop 遗留用户态进程** → 写入 `runtime\run-ensure-probe.cmd`（`cd` 到 InstallRoot 后调用 `ensure … --from-cron`；因 `schtasks /TR` 不能直接含 `&&`）→ `schtasks /Create /RU SYSTEM /F` → **`schtasks /Run`** 冷启动（不再在当前用户会话 `daemon-start`，避免双实例）。非管理员注册失败即报错，**不**降级为当前用户任务。对应 `stop-*.ps1` 以 `schtasks /Delete /F` 注销任务。

**升级顺序**：部署新包（含 `lib\probe-event-utils.ps1`）→ 管理员 `.\stop-probe.ps1`（及 keepalive）→ 确认无本路径残留 → `.\start-probe.ps1` → 验证 health，以及交互会话对新进程为优雅停（Global）。

```powershell
# 以管理员在安装目录执行
Set-Location C:\dbha-v2
powershell -ExecutionPolicy Bypass -File .\start-probe.ps1
powershell -ExecutionPolicy Bypass -File .\start-probe-keepalive.ps1 -PingHttpAddr 127.0.0.1:18080
powershell -ExecutionPolicy Bypass -File .\stop-probe-keepalive.ps1
powershell -ExecutionPolicy Bypass -File .\stop-probe.ps1
```

配置生成：`render_configs.py` 为跨平台（`fcntl` 条件导入，Windows 下跳过网卡 ioctl 回退，仅用 UDP 主路径探测 IP），Windows 上同样用 `--module probe` 渲染 `etc\probe.yaml`。若探针需经 GSE 上报，在 `dbha-v2.probe.rc` 设置 `PROBE_REPORTER_LOCAL_SOCKET_PORT`（Windows 本地 TCP 端口）；缺省 `0` 表示未设置，Linux 回退到 domain socket，行为不变。

```powershell
Copy-Item etc\dbha-v2.probe.rc.example etc\dbha-v2.probe.rc
python scripts\render_configs.py --module probe --rc etc\dbha-v2.probe.rc --ip-detect-udp-connect-host 127.0.0.1
```

> 提示：`gen-config` 在 Windows 上找不到默认网卡（`eth1`）时，会回退到物理网卡 IPv4 扫描；若仍失败则对 `--admin-endpoints` 首地址做 UDP 路由探测（无硬编码公网 IP）。

## install-libs.sh

用于安装构建依赖，包含：

- abseil（静态/动态）
- protobuf（静态/动态）
- `protoc-gen-go`、`protoc-gen-go-grpc`

```bash
cd scripts
bash ./install-libs.sh
```

说明：

- 脚本会下载并编译第三方库，耗时较长
- 需要具备写入 `/usr/local` 的权限（通常需要 root）

## devenv.rc

用于本地开发时快速注入环境变量。

```bash
source ./devenv.rc
```

可根据你的本地环境修改其中的 etcd 地址、用户名和密码。

## 推荐流程

### server 节点

```bash
./deploy.sh -m install -r server -s <source> -t <target>
cd <target> && ./setup.sh
cd <target> && ./start-server.sh
```

### probe 节点

```bash
./deploy.sh -m install -r probe -s <source> -t <target>
# 按需编辑 <target>/etc/probe.yaml
cd <target> && ./start-probe.sh
```
