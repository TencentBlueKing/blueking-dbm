### 功能描述

根据过滤条件查询业务下集群详细信息。支持按业务、集群ID、集群类型、DB类型等多维度过滤，并可附加各数据库类型专属的查询参数（如域名、版本、状态等）。

> **注意**：该接口需要具备集群列表查看（`ClusterListPermission`）权限。

---

### 请求参数

#### 基础过滤参数

| 字段         | 类型   | 必选 | 描述                                                         |
| ------------ | ------ | ---- | ------------------------------------------------------------ |
| bk_biz_id    | int    | 否   | 业务ID，不传则查询所有业务                                   |
| cluster_ids  | string | 否   | 集群ID列表，多个以逗号分隔，如 `1,2,3`                       |
| cluster_type | string | 否   | 集群类型，多个以逗号分隔，如 `tendbha,tendbsingle`           |
| db_type      | string | 否   | DB类型，如 `mysql`、`redis`、`mongodb`；可与 `cluster_type` 同时传入，按交集过滤 |
| limit        | int    | 否   | 分页限制，默认 `-1`（不分页，返回全部）                      |
| offset       | int    | 否   | 分页起始，默认 `0`                                           |

#### 通用查询参数（所有集群类型均支持）

| 字段                   | 类型   | 必选 | 描述                                   |
| ---------------------- | ------ | ---- | -------------------------------------- |
| id                     | string | 否   | 集群ID过滤，支持逗号分隔多个ID（如 `1,2,3`） |
| name                   | string | 否   | 集群名称/别名模糊查询                   |
| instance               | string | 否   | 实例地址（ip:port）                    |
| domain                 | string | 否   | 域名模糊查询                           |
| exact_domain           | string | 否   | 域名精确查询                           |
| creator                | string | 否   | 创建者                                 |
| major_version          | string | 否   | 主版本号                               |
| region                 | string | 否   | 区域                                   |
| city                   | string | 否   | 城市                                   |
| disaster_tolerance_level | string | 否 | 容灾级别                               |
| status                 | string | 否   | 集群状态                               |
| db_module_id           | string | 否   | 所属DB模块                             |
| bk_cloud_id            | string | 否   | 管控区域                               |
| ordering               | string | 否   | 排序字段                               |
| tag_ids                | string | 否   | 标签ID（逗号分隔）                     |
| tag_keys               | string | 否   | 标签键（逗号分隔）                     |
| create_at__gte         | string | 否   | 创建时间起始（ISO 8601 格式）          |
| create_at__lte         | string | 否   | 创建时间截止（ISO 8601 格式）          |

#### MySQL/TenDB 专属查询参数

| 字段          | 类型   | 必选 | 描述         |
| ------------- | ------ | ---- | ------------ |
| master_domain | string | 否   | 主域名查询   |
| slave_domain  | string | 否   | 从域名查询   |

#### SQLServer 专属查询参数

| 字段     | 类型   | 必选 | 描述                                                         |
| -------- | ------ | ---- | ------------------------------------------------------------ |
| sys_mode | string | 否   | 同步模式，可选值：`mirroring`（镜像）、`always_on`（AlwaysOn） |

#### MongoDB 专属查询参数

| 字段    | 类型   | 必选 | 描述                           |
| ------- | ------ | ---- | ------------------------------ |
| domains | string | 否   | 批量域名查询，多个以逗号分隔   |

---

### 请求参数示例

```
GET /dbbase/filter_clusters/?bk_biz_id=27&cluster_type=tendbha,tendbsingle&name=test&limit=20&offset=0
```

---

### 返回结果示例

```json
[
    {
        "id": 100,
        "db_type": "mysql",
        "phase": "online",
        "phase_name": "正常",
        "status": "normal",
        "operations": [],
        "dns_to_clb": false,
        "cluster_time_zone": "+08:00",
        "cluster_name": "test-cluster",
        "cluster_alias": "",
        "cluster_access_port": 20000,
        "cluster_stats": {},
        "cluster_type": "tendbha",
        "cluster_type_name": "MySQL高可用",
        "cluster_subzones": [],
        "cluster_subzone_ids": [],
        "disaster_tolerance_level": "NONE",
        "master_domain": "mysql.test-cluster.dba.db",
        "slave_domain": "mysql-slave.test-cluster.dba.db",
        "cluster_entry": [
            {
                "cluster_entry_type": "dns",
                "entry": "mysql.test-cluster.dba.db",
                "role": "master"
            }
        ],
        "bk_biz_id": 27,
        "bk_biz_name": "DBA测试业务",
        "bk_cloud_id": 0,
        "bk_cloud_name": "直连区域",
        "major_version": "MySQL-5.7",
        "region": "default",
        "city": "default",
        "db_module_name": "",
        "db_module_id": 0,
        "creator": "admin",
        "updater": "admin",
        "create_at": "2024-01-01 00:00:00",
        "update_at": "2024-01-01 00:00:00",
        "cluster_spec": null,
        "tags": [],
        "zone_list": []
    }
]
```

---

### 返回结果参数说明

> 返回值是**集群对象数组**，不包含 `code/result/message/data` 包裹层。

#### 列表元素字段说明

> 以下为通用字段。不同集群类型（不同资源查询器）可能返回额外字段，请以前端实际使用字段为准。

| 字段                     | 类型         | 描述                                                         |
| ------------------------ | ------------ | ------------------------------------------------------------ |
| id                       | int          | 集群ID                                                       |
| db_type                  | string       | DB类型（如 `mysql`、`redis`、`mongodb`）                     |
| phase                    | string       | 集群阶段，如 `online`、`offline`                             |
| phase_name               | string       | 集群阶段展示名                                               |
| status                   | string       | 集群状态，如 `normal`、`abnormal`                            |
| operations               | list         | 集群关联操作记录                                             |
| dns_to_clb               | bool         | 主域名是否由 DNS 转发到 CLB                                  |
| cluster_time_zone        | string       | 集群时区                                                     |
| cluster_name             | string       | 集群名称                                                     |
| cluster_alias            | string       | 集群别名                                                     |
| cluster_access_port      | int          | 集群访问端口                                                 |
| cluster_stats            | dict         | 集群统计信息（不同DB类型结构可能不同）                       |
| cluster_type             | string       | 集群类型，如 `tendbha`、`tendbsingle`、`MongoReplicaSet` 等  |
| cluster_type_name        | string       | 集群类型展示名                                               |
| cluster_subzones         | list         | 集群园区名称列表                                             |
| cluster_subzone_ids      | list         | 集群园区ID列表                                               |
| disaster_tolerance_level | string       | 容灾级别，如 `NONE`、`SAME_SUBZONE`、`SAME_CITY`、`CROSS_CITY` |
| master_domain            | string       | 主域名                                                       |
| slave_domain             | string       | 从域名（无从域名时为空）                                     |
| cluster_entry            | list         | 集群访问入口列表（元素包含 `cluster_entry_type`/`entry`/`role`） |
| bk_biz_id                | int          | 业务ID                                                       |
| bk_biz_name              | string       | 业务名称                                                     |
| bk_cloud_id              | int          | 管控区域ID                                                   |
| bk_cloud_name            | string       | 管控区域名称                                                 |
| major_version            | string       | 主版本号                                                     |
| region                   | string       | 区域                                                         |
| city                     | string       | 城市（当前与 `region` 一致）                                 |
| db_module_id             | int          | 所属DB模块ID                                                 |
| db_module_name           | string       | 所属DB模块名称                                               |
| creator                  | string       | 创建者                                                       |
| updater                  | string       | 更新者                                                       |
| create_at                | string       | 创建时间                                                     |
| update_at                | string       | 更新时间                                                     |
| cluster_spec             | dict/null    | 集群规格信息，可能为 `null`                                  |
| tags                     | list         | 集群标签列表                                                 |
| zone_list                | list         | 园区ID列表                                                   |