# DBHA v2

DBHA v2（Database High Availability v2）是蓝鲸 DBM 的数据库高可用监测与自动切换组件。

边缘节点上的 **probe** 采集实例状态并上报；服务端 **receiver** 落库，**analysis** 做故障判定与切换，**admin** 提供配置下发与运维 API。

**模块路径**：`dbm-services/common/dbha-v2`

## 服务一览


| 服务           | 二进制             | 职责                                                      |
| ------------ | --------------- | ------------------------------------------------------- |
| **admin**    | `dbha-admin`    | 配置中心与运维 API；向 probe 下发配置；etcd 注册；策略/切换日志等 HTTP Open API |
| **receiver** | `dbha-receiver` | 探测数据汇聚；接收 probe gRPC 或 Kafka，写入 MySQL                   |
| **analysis** | `dbha-analysis` | 故障判定与切换引擎；同步 DBM 元数据、扫描、二次探测、策略匹配、执行切换                  |
| **probe**    | `dbha-probe`    | 边缘采集（MySQL / ProxyAdmin / Redis）；上报；keepalive；跨平台进程守护   |


## 文档


| 文档                                    | 说明                      |
| ------------------------------------- | ----------------------- |
| [架构总览](docs/architecture/overview.md) | 组件职责、部署拓扑、外部依赖、端到端数据流   |
| [工作流程](docs/flows/README.md)          | 配置下发、采集上报、故障判定与切换（含顺序图） |
| [探测设计](docs/detection/detection-doc-index.md) | 探测/切换设计文档索引（含 MySQL 家族设计） |
| [部署与脚本](scripts/README.md)            | 配置渲染、启停、安装              |
| [开发指引](CODEBUDDY.md)                  | 目录结构、构建/测试约定、开发脚本       |
| [变更记录](CHANGELOG.md)                  | 版本与变更说明                 |




## 构建与测试

```bash
# 生成 protobuf（构建前需要）
make proto

# 构建全部服务与工具
make all

# 单服务
make admin
make analysis
make receiver
make probe

# 测试
make test
```

发布包：`make package`（或 `package-server` / `package-probe`）。更多命令见 [CODEBUDDY.md](CODEBUDDY.md) 与 `Makefile`。

## 配置与部署（简要）

- 模板：`etc/templates/*.yaml`，示例 RC：`etc/dbha-v2.server.rc.example`、`etc/dbha-v2.probe.rc.example`
- 渲染：`python3 scripts/render_configs.py --module server|probe --rc <rc-file>`
- 部署细节见 [scripts/README.md](scripts/README.md)

