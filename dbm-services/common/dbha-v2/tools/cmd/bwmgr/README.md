# bwmgr 使用说明

`bwmgr`（构建产物为 `dbha-bwmgr`）是 DBHA v2 附带的命令行工具，用于通过 HADB HTTP API 管理数据库切换黑白名单。

底层调用的 API 包括：

- `get_black_white_list` — 查询
- `insert_black_white_list` — 新增
- `update_black_white_list` — 更新
- `delete_black_white_list` — 删除

## 命令总览

| 命令 | 说明 |
|------|------|
| `list` | 查询黑白名单列表 |
| `add` | 新增一条记录 |
| `update` | 更新已有记录 |
| `delete` | 删除记录 |
| `import` | 从 JSON Lines 文件批量导入 |
| `version` | 打印版本及 v1/v2 切换说明 |

---

## 构建与运行

在 `dbha-v2` 根目录执行：

```bash
make bwmgr
./build/dbha-bwmgr version
```

本地开发也可直接构建：

```bash
CGO_ENABLED=0 go build -o dbha-bwmgr ./tools/cmd/bwmgr
```

---

### 部署后使用（server 安装目录）

通过 `deploy.sh -m install -r server` 安装后，二进制与配置位于安装根目录：

```bash
cd /usr/local/dbha-v2
./toolkits/dbha-bwmgr -c ./etc/bwmgr.yaml list
./toolkits/dbha-bwmgr -c ./etc/bwmgr.yaml version
```

仅执行 `deploy update` 会更新 `toolkits/dbha-bwmgr` 二进制，不会自动覆盖 `etc/bwmgr.yaml`。

## 配置

### 配置优先级（高 → 低）

1. **命令行参数**：`--api-endpoint`、`--api-bk-cloud-id`、`--api-token`、`--api-timeout`
2. **环境变量**：`BWMGR_API_ENDPOINT`、`BWMGR_API_BK_CLOUD_ID`、`BWMGR_API_TOKEN`、`BWMGR_API_TIMEOUT`
3. **配置文件**：默认 `./etc/bwmgr.yaml`（可用 `-c` / `--config` 指定）

### 配置文件示例

配置文件模板见 [`etc/bwmgr.yaml`](../../../etc/bwmgr.yaml)：

```yaml
api:
  endpoint: "http://127.0.0.1:80/blackwhitelist/"
  bk_cloud_id: 0
  timeout: 30s
  token: ""
```

| 字段 | 说明 |
|------|------|
| `api.endpoint` | HADB API 完整地址（含路径） |
| `api.bk_cloud_id` | 请求体中的 `bk_cloud_id`（`0` 表示直连云区域） |
| `api.timeout` | 单次 HTTP 请求超时，如 `30s` |
| `api.token` | `db_cloud_token`，**生产环境建议通过 `BWMGR_API_TOKEN` 环境变量注入，勿写入版本库** |

### 全局参数（所有子命令可用）

| 参数 | 说明 |
|------|------|
| `-c, --config` | 配置文件路径（默认 `./etc/bwmgr.yaml`） |
| `--api-endpoint` | 覆盖 API 地址 |
| `--api-bk-cloud-id` | 覆盖请求体中的 `bk_cloud_id` |
| `--api-token` | 覆盖 API token |
| `--api-timeout` | 覆盖 HTTP 超时，如 `30s` |

示例：

```bash
export BWMGR_API_TOKEN="your-token"
dbha-bwmgr --api-endpoint "http://hadb.example.com/blackwhitelist/" list
```

---

## 字段与枚举说明

| 字段 | 取值 | 说明 |
|------|------|------|
| `switch_version` | `v1` / `v2` | 切换版本：`v1` 为旧版 ha-module 切换；`v2` 为 dbha-v2 白名单 |
| `status` | `enabled` / `disabled` | 启用 / 禁用 |
| 业务唯一键 | `bk_biz_id + bk_cloud_id + cluster_id` | `add --upsert` 及 `import --upsert` 的匹配依据 |

### v1 / v2 行为说明

执行 `dbha-bwmgr version` 可查看版本信息及下列说明：

- **v1**：由 ha-module(v1) 管理的旧版切换。若同一集群存在 `switch_version=v2` 且 `status=enabled` 的记录，v1 将跳过该集群的切换。
- **v2**：由 dbha-v2 管理的新版切换。仅 `switch_version=v2` **且** `status=enabled` 的记录会被 ha-module(v1) 视为白名单。

---

## 子命令详解

### `list` — 查询列表

列出黑白名单，支持按条件过滤及多种输出格式。

| 参数 | 说明 |
|------|------|
| `--bk-biz-id` | 按业务 ID 过滤 |
| `--bk-cloud-id` | 按云区域 ID 过滤 |
| `--cluster-id` | 按集群 ID 过滤 |
| `--cluster-name` | 按集群名过滤 |
| `--switch-version` | 按切换版本过滤（`v1` / `v2`） |
| `--status` | 按状态过滤（`enabled` / `disabled`） |
| `--output` | 输出格式：`table`（默认）或 `json` |
| `--output-file` | 将结果以 **JSON Lines**（每行一条 JSON）写入指定文件；设置后 **不向 stdout 输出**，与 `--output` 及参数顺序无关 |

示例：

```bash
# 表格输出（默认）
dbha-bwmgr list

# 按条件过滤
dbha-bwmgr list --bk-biz-id 1 --switch-version v2

# 缩进 JSON 输出到 stdout
dbha-bwmgr list --output json

# JSON Lines 写入文件（stdout 无输出）
dbha-bwmgr list --output-file ./bwlist.jsonl
```

`table` 模式输出列：`ID`、`BK_BIZ_ID`、`BK_CLOUD_ID`、`CLUSTER_ID`、`CLUSTER_NAME`、`SWITCH_VERSION`、`STATUS`、`CREATED_AT`、`UPDATED_AT`。

---

### `add` — 新增

向黑白名单新增一条记录。

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--bk-biz-id` | 是 | — | 业务 ID |
| `--cluster-id` | 是 | — | 集群 ID |
| `--cluster-name` | 是 | — | 集群名称 |
| `--bk-cloud-id` | 否 | `0` | 云区域 ID（`0` 为直连云区域） |
| `--switch-version` | 否 | `v2` | 切换版本 |
| `--status` | 否 | `enabled` | 状态 |
| `--upsert` | 否 | `false` | 若已存在相同业务键则更新而非插入 |
| `--yes` | 否 | `false` | 跳过风险操作确认 |

示例：

```bash
# 普通新增
dbha-bwmgr add \
  --bk-biz-id 1 \
  --bk-cloud-id 0 \
  --cluster-id 100 \
  --cluster-name cluster-a

# 已存在则更新（upsert）
dbha-bwmgr add \
  --bk-biz-id 1 \
  --bk-cloud-id 0 \
  --cluster-id 100 \
  --cluster-name cluster-a \
  --switch-version v2 \
  --status enabled \
  --upsert \
  --yes
```

#### `--upsert` 行为说明

- **匹配键**：`bk_biz_id + bk_cloud_id + cluster_id`
- 命中已有记录时走 `update`，使用 **服务端查到的 ID**，不使用命令行上的 `id`
- 仅更新 **显式传入** 的 `--cluster-name`、`--switch-version`、`--status`（未传 flag 的字段不会用默认值覆盖）
- 至少需提供一个可更新且为有效值的字段，否则会报错

成功时输出：

- 普通新增：`Successfully added black-white list entry with ID: <id>`
- upsert 更新：`Successfully upserted black-white list entry, rows affected: <n>`

---

### `update` — 更新

更新已有记录。

**定位条件**（至少指定一项）：`--id`、`--bk-biz-id`、`--cluster-id`、`--cluster-name`（可与 `--bk-cloud-id` 组合）

**更新字段**（至少指定一项）：`--set-cluster-name`、`--switch-version`、`--status`

| 参数 | 说明 |
|------|------|
| `--yes` | 跳过风险确认（将 `status` 设为 `disabled` 或将 `switch-version` 设为 `v1` 时） |

示例：

```bash
# 按 ID 禁用
dbha-bwmgr update --id 11 --status disabled

# 按业务键修改切换版本
dbha-bwmgr update \
  --bk-biz-id 1 \
  --bk-cloud-id 0 \
  --cluster-id 100 \
  --switch-version v1 \
  --yes

# 修改集群名
dbha-bwmgr update --id 11 --set-cluster-name cluster-b
```

成功时输出：`Successfully updated <n> black-white list entry(ies)`

---

### `delete` — 删除

删除匹配的记录。

**定位条件**（至少指定一项）：`--id`、`--bk-biz-id`、`--cluster-id`、`--cluster-name`（可与 `--bk-cloud-id` 组合）

| 参数 | 说明 |
|------|------|
| `--yes` | 跳过删除确认 |

示例：

```bash
# 按 ID 删除
dbha-bwmgr delete --id 11 --yes

# 按业务键删除
dbha-bwmgr delete --bk-biz-id 1 --cluster-id 100 --yes
```

成功时输出：`Successfully deleted <n> black-white list entry(ies)`

---

### `import` — 批量导入

从 JSON Lines 文件批量执行 `add` / `update` / `delete`。每行一条 JSON，必须包含 `action` 字段。

| 参数 | 说明 |
|------|------|
| `--file` | JSON Lines 导入文件路径 |
| `--create-template` | 生成空模板（含 add/update/delete 各一行示例）后退出 |
| `--create-template-from-list` | 将当前列表导出为 `action=update` 的 JSON Lines 模板后退出 |
| `--dry-run` | 仅解析并校验文件，不调用 API |
| `--upsert` | 对文件中 `action=add` 的行启用 upsert |
| `--yes` | 跳过 import 及风险 update 的交互确认 |

**注意**：`--create-template` 与 `--create-template-from-list` 不可同时使用。

#### JSON Lines 行格式

**`action=add`**（新增）：

```json
{"action":"add","bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,"cluster_name":"cluster-a","switch_version":"v2","status":"enabled"}
```

必填：`bk_biz_id`、`cluster_id`、`cluster_name`、`switch_version`。

**`action=update`**（更新）：

```json
{"action":"update","id":11,"bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,"cluster_name":"cluster-a","set_cluster_name":"cluster-b","switch_version":"v2","status":"enabled"}
```

- 定位：推荐指定 `id`；也可组合 `bk_biz_id` / `bk_cloud_id` / `cluster_id` / `cluster_name`
- 更新：至少指定 `set_cluster_name`、`switch_version`、`status` 之一
- 导出模板中 `cluster_name` 用于 query，修改集群名需使用 `set_cluster_name`

**`action=delete`**（删除）：

```json
{"action":"delete","id":12,"bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,"cluster_name":"cluster-a"}
```

定位条件至少指定一项。

#### 生成模板

```bash
# 空模板（add/update/delete 示例各一行）
dbha-bwmgr import --create-template ./template.jsonl

# 从当前列表导出（每行 action=update，含服务端 id）
dbha-bwmgr import --create-template-from-list ./bwlist.jsonl
```

导出示例（`--create-template-from-list`）：

```json
{"action":"update","id":11,"bk_biz_id":1,"bk_cloud_id":0,"cluster_id":100,"cluster_name":"cluster-a","switch_version":"v2","status":"enabled"}
```

#### 导入示例

```bash
# 校验文件格式
dbha-bwmgr import --file ./bwlist.jsonl --dry-run

# 执行导入（含 add 行的 upsert）
dbha-bwmgr import --file ./bwlist.jsonl --upsert --yes
```

成功时输出：`Import finished, added: <n>, updated: <n>, deleted: <n>`

#### import 与 upsert 注意事项

- `--upsert` **仅对** `action=add` 的行生效；`action=update` 行不受影响
- `add + --upsert` **忽略** JSON 中的 `id` 字段，按业务键匹配后使用服务端 ID 更新
- **update 不会修改数据库主键 ID**；`added > 0` 才表示发生了新插入
- 全量回灌导出的文件时，建议保持 `action=update`，不要无故改成 `add`

---

### `version` — 版本信息

```bash
dbha-bwmgr version
```

打印工具版本及 v1/v2 切换版本说明（见上文「字段与枚举说明」）。

---

## 风险确认机制

部分操作可能影响 ha-module(v1) 切换行为或造成数据删除，默认需要交互确认（输入 `y` 或 `yes`）。使用 `--yes` 可跳过。

| 场景 | 默认行为 | `--yes` |
|------|----------|---------|
| `delete` | 交互确认 | 跳过 |
| `update` 将 `status` 设为 `disabled` 或 `switch-version` 设为 `v1` | 交互确认 | 跳过 |
| `import` 含 `update`/`delete` 行，或指定了 `--upsert` | 交互确认 | 跳过 |
| `add --upsert` 命中需风险确认的更新 | 交互确认 | 跳过 |

---

## 典型工作流

### 1. 导出当前配置为可编辑模板

```bash
dbha-bwmgr import --create-template-from-list ./bwlist.jsonl
```

### 2. 编辑后校验

```bash
dbha-bwmgr import --file ./bwlist.jsonl --dry-run
```

### 3. 全量回灌（保持 `action=update`）

```bash
dbha-bwmgr import --file ./bwlist.jsonl --yes
```

### 4. 新增单条（已存在则更新）

```bash
dbha-bwmgr add \
  --bk-biz-id 1 \
  --cluster-id 100 \
  --cluster-name cluster-a \
  --upsert \
  --yes
```

### 5. 导出列表快照（JSON Lines）

```bash
dbha-bwmgr list --output-file ./snapshot.jsonl
```

---

## 错误排查

| 错误信息 | 可能原因 |
|----------|----------|
| `failed to load config` | 未配置 `endpoint` 或 `token`；检查配置文件与环境变量 |
| `cluster_name is required` | `add` 或 upsert 时显式传入了空的 `cluster_name` |
| `at least one upsert update field` | upsert 时未显式提供可更新字段 |
| `line N: ...` | import 文件第 N 行解析或校验失败 |
| `create-template and create-template-from-list cannot be used together` | 两个模板参数不可同时使用 |

---

## 参考

命令行参数的权威说明以运行时 help 为准：

```bash
dbha-bwmgr --help
dbha-bwmgr <command> --help
```
