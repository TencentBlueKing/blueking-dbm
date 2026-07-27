# MongoDB 介质版本选择规则

V1 / V2 共用 `Package` 表。运营侧只在 V2（`/version-files`）维护；流程侧取包走 V2 API 或 `lookup_mongodb_package`。

实现入口：

- 周边：`get_mongodb_package_v2_release` → `Package.get_latest_package_v2_release`
- 主介质：`lookup_mongodb_package`

---

## 1. V2 上传约定

| 介质 `pkg_type` | `version_series.name`（series） | 版本形态 |
|-----------------|----------------------------------|----------|
| `mongodb` | `mongodb-x.y`（如 `mongodb-7.0`） | 具体版本为 `x.y.z`（流程常用 `mongodb-x.y.z`） |
| `actuator` / `dbmon` / `dbtools` / `mongo-toolkit` | **`latest`** | 挂在 `latest` 系列下 |

V2 取包还会过滤：

- `db_version.phase = release`
- `permit_os_type = Linux`
- 周边包：`Package.enable = True`（见下）

---

## 2. 周边介质（actuator / dbmon / dbtools / mongo-toolkit）

- series **必须**为 `latest`（代码默认 `PkgSeries.LATEST`）。
- 调用：`get_mongodb_package_v2_release(pkg_type)`（不读 `REPO_VERSION_FOR_DEV`）。

同一 series 下多条候选时，优先级从高到低：

1. `db_version.full_version_n` 更大
2. 相同则 `db_version.recommend=True` 优先
3. 再相同则 `Package.priority` 更大

实现：`Package.get_package_v2_by_phase`。

---

## 3. 主介质（mongodb）

入口：`lookup_mongodb_package(raw_version)`。

| 输入 | 规则 |
|------|------|
| `mongodb-x.y`（仅主次版本，如 `mongodb-7.0`） | 只在 **`enable=True`** 的候选中，取 **patch（z）最大** 的包 |
| `mongodb-x.y.z`（完整版本，如 `mongodb-7.0.28`） | 按解析后的完整版本 **完全匹配**；**不考虑 `enable`**；匹配不到返回 `None`（不回退到同主次最高 patch） |

完整版本匹配依据 `_resolve_package_full_version(package)`（`package.version` 或挂载的 `db_version` patch）与规范化后的 `mongodb-x.y.z` 相等。

**注意**：V2 的 `Package.version` 常存系列名 `mongodb-x.y`。凡需要完整版本的展示/回写路径，必须走 `_resolve_package_full_version`（读 `db_version`），**禁止**对 series-only 的 `Package.version` 直接 `normalize_mongodb_full_version`（会合成错误的 `mongodb-x.y.0`）。

涉及：`list_available_versions`、`query_mongodb_versions`（Package 兜底）、升级 `_resolve_persist_version` 兜底。

---

## 4. 相关调用点

- `mongodb_install_dbmon.get_pkg_info`：周边四类
- `GetFileList`（`db_type=MongoDB`）：actuator；`mongodb_pkg` → `lookup_mongodb_package`
- `ActKwargs.get_pkg` / 升级流程：`lookup_mongodb_package`
