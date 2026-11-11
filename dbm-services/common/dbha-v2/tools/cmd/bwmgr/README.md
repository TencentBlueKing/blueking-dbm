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
| `--create-template-from-xlsx` | 由 DBM 集群导出 xlsx 生成 `action=add` 的 JSON Lines，自动校验后退出（离线，不读取配置） |
| `--xlsx-file` | DBM 集群导出 xlsx 路径（与 `--create-template-from-xlsx` 配合，必填） |
| `--xlsx-bk-biz-id` | 业务 ID；不传时从 xlsx 文件名解析 |
| `--xlsx-switch-version` | 生成记录的切换版本，默认 `v2` |
| `--xlsx-status` | 生成记录的状态，默认 `enabled` |
| `--xlsx-report` | JSON 校验报告路径，默认 `<输出路径>.report.json` |

**注意**：`--create-template` 与 `--create-template-from-list` 不可同时使用；`--create-template-from-xlsx` 与这两者也不可同时使用。单独使用任一 `--xlsx-*` 会报错。

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

#### 由 DBM 集群 xlsx 生成白名单

在 DBM 集群列表页导出 xlsx（文件名形如 `<业务英文名>(<业务ID>)<db_type>_cluster[_YYYYMMDDHHmmss].xlsx`，如 `mysql_cluster`、`k8s_milvus_cluster`），直接生成 `action=add` 的导入文件：

```bash
dbha-bwmgr import --create-template-from-xlsx ./whitelist.jsonl \
  --xlsx-file "./mapleleaf(591)mysql_cluster_20261104101251.xlsx"

# 先校验，再导入
dbha-bwmgr import --file ./whitelist.jsonl --dry-run
dbha-bwmgr import --file ./whitelist.jsonl --upsert --yes
```

该模式离线运行，不读取配置文件和 `BWMGR_API_*` 环境变量，没有 endpoint / token 也能使用。

**列映射**（按表头名称匹配，列顺序不限；中英文表头均可识别，英文不区分大小写）：

| xlsx 列 | JSON 字段 | 规则 |
|---------|-----------|------|
| `集群 ID` / `Cluster ID` | `cluster_id` | 必需；正整数，不超过 2147483647，`123.0` 写法可识别 |
| `主域名` / `Primary domain name` | `cluster_name` | 必需；去掉首尾空白；只允许字母、数字、`.`、`-`、`_`，可带 `:<数字端口>`（会被去掉）；多个域名、空值或出现其他字符（含全角字符、零宽字符）时报错 |
| `管控区域` / `control area` | `bk_cloud_id` | 必需；逐行读取，大于等于 0 且不超过 2147483647 的整数；同一文件可含多个云区域 |
| `集群类型` / `Cluster type`、`状态` / `state` | — | 可选；只用于报告中的统计 |

- **`cluster_name` 必须是主域名**：v1（ha-module）与 v2 都按实例所属集群的主域名（`immute_domain`）匹配白名单，取「集群名称」列会导致白名单不生效。
- **`bk_cloud_id` 是查询过滤条件**：v1 / v2 按 `bk_cloud_id` 查询白名单，值错误会导致该记录静默失效，因此一律取自「管控区域」列。
- `bk_biz_id`：传了 `--xlsx-bk-biz-id` 以它为准；否则从文件名中的 `(<业务ID>)` 解析。浏览器重名下载自动追加 ` (1)` 等后缀时无法解析，需显式传入。
- 同一集群出现多行时只保留一条；同一集群 ID 对应不同域名或不同管控区域、同一域名对应不同集群 ID 时报错。

**拒绝生成的情况**（宁可报错，不误导入）：

- 只有表头、没有数据行；
- 缺少必需列，或同一列的中英文表头同时出现；
- 工作簿包含多个 sheet（含隐藏 sheet）；
- 存在隐藏的非空行：在 Excel 中用筛选或隐藏行"排除"的集群仍在文件中，请先删除这些行再生成；
- 必需列中出现布尔、错误值（如 `#N/A`）或日期类型的单元格。

**生成后自动校验**：先写 `<输出路径>.tmp`，再重新读取源 xlsx（xlsx 解析与生成共用）和临时文件；字段转换（集群 ID、域名、管控区域）、文件名中的业务 ID、重复行冲突检查由校验侧独立实现后逐行比对（C1 可导入、C2 字段集合严格匹配、C3 源行全覆盖、C4 无多余行、C5 字段值一致（按集群 ID 配对；集群 ID 不在源数据中时按域名配对，以便直接报出被篡改的 `cluster_id`）、C6 集群 ID / 域名唯一、C7 计数一致）。传了 `--xlsx-bk-biz-id` 时，校验直接采用该值，无法与文件名交叉核对，请自行确认业务 ID 正确。

- 全部通过（`result: PASS`）才把临时文件改名为正式输出；
- 任一项失败（`result: FAIL`）时删除临时文件、以非 0 退出，正式输出路径上已有的旧文件保持不变（报告中注明 `existing file kept`），请勿把旧文件当作本次结果导入；
- 文本报告打印到 stdout，差异明细每项最多显示 20 条；JSON 报告写入 `--xlsx-report`，包含全部差异；缺少集群类型或状态列时，JSON 报告中对应的 `by_cluster_type` / `by_status` 为 `null`，有该列但单元格为空时计入 `-`；
- 输入、输出、`.tmp`、报告 4 个路径中任意两个相同时报错。

**导入风险提示**：

- 以默认 `v2` + `enabled` 导入后，这些集群由 v2 切换，**v1 会立即停止对它们的切换**；其他取值的记录不会被白名单查询命中，v1 继续切换。
- `add` 行在不带 `--upsert` 时导入不需要确认，请务必先 `--dry-run`，并核对报告中的 `output_lines` 与 DBM 页面上的集群数一致。

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
| `--create-template-from-xlsx cannot be used with ...` | xlsx 生成与另外两个模板参数不可同时使用 |
| `--xlsx-* flags require --create-template-from-xlsx` | 传了 `--xlsx-*` 但没有指定输出路径 |
| `xlsx has no data rows` | xlsx 只有表头 |
| `xlsx has hidden rows, ...` | 存在隐藏的非空行，删除后再生成 |
| `xlsx must contain exactly one sheet, ...` | 工作簿含多个 sheet（含隐藏 sheet） |
| `cannot parse bk_biz_id from xlsx file name` | 文件名不符合 DBM 导出格式，需传 `--xlsx-bk-biz-id` |
| `xlsx verify failed, report: <path>` | 生成后校验未通过，查看报告中的 `[FAIL]` 明细 |

---

## 参考

命令行参数的权威说明以运行时 help 为准：

```bash
dbha-bwmgr --help
dbha-bwmgr <command> --help
```
