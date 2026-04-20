# DBHA v2 Scripts Usage

本文档说明 `scripts` 目录下各脚本的用途与使用方式。

## 目录说明

- `deploy.sh`: 部署与更新脚本（支持按模块安装）
- `render_configs.py`: 按模块用 `etc/dbha-v2.{server,probe}.rc` 与 `etc/templates/*.yaml` 渲染 `etc/*.yaml`
- `setup.sh`: 交互式配置生成脚本（仅 server 侧使用）
- `start-server.sh`: 启动 server 侧服务（admin/receiver/analysis）
- `stop-server.sh`: 停止 server 侧服务（admin/receiver/analysis）
- `start-probe.sh`: 启动 probe 服务
- `stop-probe.sh`: 停止 probe 服务
- `install-libs.sh`: 安装构建依赖（abseil/protobuf/protoc 插件）
- `devenv.rc`: 本地开发环境变量示例

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
    1. `COMMON_APM_LISTEN_ADDRESS` → `http://<本机检测 IPv4>:50050`（失败则为 `http://127.0.0.1:50050`）。
    2. `RECEIVER_SOURCE_PROBE_ENDPOINT` → `<本机检测 IPv4>:50051`（失败则为 `127.0.0.1:50051`）。
    3. `ADMIN_GRPC_LISTEN_ADDRESS` → `<本机检测 IPv4>:50051`；若仅为 `:<端口>` 则补全主机段。
    4. `ADMIN_WEB_HOST` → `<本机检测 IPv4>`（失败则为 `127.0.0.1`）；`ADMIN_WEB_PORT` → `50060`。
  - 「本机检测 IPv4」依赖必填参数 `--ip-detect-udp-connect-host`（UDP connect 对端；与上列 (1)–(4) 同一策略）。
- **receiver `service.source` 分片（server）**：`RECEIVER_SOURCE_PROBE_SHARD_FILE` / `RECEIVER_SOURCE_KAFKA_SHARD_FILE` 各对应一类 source 列表项（默认见 `templates/snippets/receiver_source_probe.yaml`、`receiver_source_kafka.yaml`），占位符与 rc 中 `RECEIVER_SOURCE_PROBE_*` / `RECEIVER_SOURCE_KAFKA_*` 一致。
- **receiver `service.sink` mysql 分片（server）**：`RECEIVER_SINK_MYSQL_SHARD_FILE`（默认 `templates/snippets/receiver_sink_mysql.yaml`），占位符为 `RECEIVER_SINK_MYSQL_*`。
- **probe 分片（probe）**：`PROBE_MYSQL_SHARD_FILE` / `PROBE_REDIS_SHARD_FILE` 分别描述 `harvester.mysql` / `harvester.redis`（默认见 `templates/snippets/`）。MySQL / Redis 的 `endpoints[0]` 字段通过 `PROBE_MYSQL_EP_*` / `PROBE_REDIS_EP_*` 在 rc 中配置并由分片模板渲染；`PROBE_REDIS_SHARD_ENABLED=0` 时不生成 `redis:` 段。
- 若已安装 PyYAML，渲染后会做语法校验；可用 `--no-validate-yaml` 跳过。

发布包：
- server 包（`$(VERSION)-server.tar.gz`）携带 `render_configs.py`、`etc/templates/`、`etc/dbha-v2.server.rc.example`
- probe 包（`$(VERSION)-probe.tar.gz`）携带 `render_configs.py`、`etc/templates/`、`etc/dbha-v2.probe.rc.example`

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
  - 安装/更新 `admin.yaml`、`receiver.yaml`、`analysis.yaml`
  - 安装 `setup.sh`、`start-server.sh`、`stop-server.sh`、`deploy.sh`
  - 处理 `toolkits/`（部署与备份）
- `probe`:
  - 安装/更新 `dbha-probe`
  - 安装/更新 `probe.yaml`
  - 安装 `start-probe.sh`、`stop-probe.sh`、`deploy.sh`
  - 不安装 `setup.sh`，不处理 `toolkits/`

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

```bash
cd /usr/local/dbha-v2
./start-server.sh
./stop-server.sh
```

## start-probe.sh / stop-probe.sh

用于管理 probe 服务。

```bash
cd /usr/local/dbha-v2
./start-probe.sh
./stop-probe.sh
```

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
