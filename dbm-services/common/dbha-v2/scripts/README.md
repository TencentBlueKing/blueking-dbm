# DBHA v2 Scripts Usage

本文档说明 `scripts` 目录下各脚本的用途与使用方式。

## 目录说明

- `deploy.sh`: 部署与更新脚本（支持按模块安装）
- `setup.sh`: 交互式配置生成脚本（仅 server 侧使用）
- `start-server.sh`: 启动 server 侧服务（admin/receiver/analysis）
- `stop-server.sh`: 停止 server 侧服务（admin/receiver/analysis）
- `start-probe.sh`: 启动 probe 服务
- `stop-probe.sh`: 停止 probe 服务
- `install-libs.sh`: 安装构建依赖（abseil/protobuf/protoc 插件）
- `devenv.rc`: 本地开发环境变量示例

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
