### Functional Description

Query detailed information of clusters under a business based on filter conditions. Supports multi-dimensional filtering by business, cluster ID, cluster type, DB type, etc., and can append exclusive query parameters for each database type (such as domain, version, status, etc.).

> **Note**: This interface requires the Cluster List View (`ClusterListPermission`) permission.

---

### Request Parameters

#### Basic Filtering Parameters

| Field         | Type   | Required | Description                                                         |
| ------------ | ------ | -------- | ------------------------------------------------------------ |
| bk_biz_id    | int    | No       | Business ID; if not provided, all businesses will be queried |
| cluster_ids  | string | No       | List of cluster IDs, multiple values separated by commas, e.g., `1,2,3` |
| cluster_type | string | No       | Cluster type, multiple values separated by commas, e.g., `tendbha,tendbsingle` |
| db_type      | string | No       | DB type, e.g., `mysql`, `redis`, `mongodb`; can be used together with `cluster_type` for intersection filtering |
| limit        | int    | No       | Pagination limit, default `-1` (no pagination, return all) |
| offset       | int    | No       | Pagination start index, default `0` |

#### General Query Parameters (Supported by All Cluster Types)

| Field                   | Type   | Required | Description                                   |
| ---------------------- | ------ | -------- | -------------------------------------------- |
| id                     | string | No       | Cluster ID filter, supports comma-separated multiple IDs (e.g., `1,2,3`) |
| name                   | string | No       | Fuzzy search by cluster name/alias           |
| instance               | string | No       | Instance address (ip:port)                   |
| domain                 | string | No       | Fuzzy search by domain                       |
| exact_domain           | string | No       | Exact search by domain                       |
| creator                | string | No       | Creator                                      |
| major_version          | string | No       | Major version number                         |
| region                 | string | No       | Region                                       |
| city                   | string | No       | City                                         |
| disaster_tolerance_level | string | No       | Disaster tolerance level                     |
| status                 | string | No       | Cluster status                               |
| db_module_id           | string | No       | Associated DB module                         |
| bk_cloud_id            | string | No       | Control region                               |
| ordering               | string | No       | Ordering field                               |
| tag_ids                | string | No       | Tag IDs (comma-separated)                    |
| tag_keys               | string | No       | Tag keys (comma-separated)                   |
| create_at__gte         | string | No       | Creation time start (ISO 8601 format)        |
| create_at__lte         | string | No       | Creation time end (ISO 8601 format)          |

#### MySQL/TenDB Exclusive Query Parameters

| Field          | Type   | Required | Description         |
| ------------- | ------ | -------- | ------------------- |
| master_domain | string | No       | Master domain query |
| slave_domain  | string | No       | Slave domain query  |

#### SQLServer Exclusive Query Parameters

| Field     | Type   | Required | Description                                                         |
| -------- | ------ | -------- | ------------------------------------------------------------ |
| sys_mode | string | No       | Synchronization mode, optional values: `mirroring` (Mirror), `always_on` (AlwaysOn) |

#### MongoDB Exclusive Query Parameters

| Field    | Type   | Required | Description                           |
| ------- | ------ | -------- | ------------------------------ |
| domains | string | No       | Batch domain query, multiple values separated by commas |

---

### Request Parameter Example

```
GET /dbbase/filter_clusters/?bk_biz_id=27&cluster_type=tendbha,tendbsingle&name=test&limit=20&offset=0
```

---

### Response Example

```json
[
    {
        "id": 100,
        "db_type": "mysql",
        "phase": "online",
        "phase_name": "Normal",
        "status": "normal",
        "operations": [],
        "dns_to_clb": false,
        "cluster_time_zone": "+08:00",
        "cluster_name": "test-cluster",
        "cluster_alias": "",
        "cluster_access_port": 20000,
        "cluster_stats": {},
        "cluster_type": "tendbha",
        "cluster_type_name": "MySQL High Availability",
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
        "bk_biz_name": "DBA Test Business",
        "bk_cloud_id": 0,
        "bk_cloud_name": "Direct Access Region",
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

### Response Parameter Description

> The return value is an **array of cluster objects**, without the `code/result/message/data` wrapper layer.

#### List Element Field Description

> The following are common fields. Different cluster types (different resource queryers) may return additional fields; please refer to the actual fields used in the frontend.

| Field                     | Type         | Description                                                         |
| ------------------------ | ------------ | ------------------------------------------------------------ |
| id                       | int          | Cluster ID                                                       |
| db_type                  | string       | DB type (e.g., `mysql`, `redis`, `mongodb`)                     |
| phase                    | string       | Cluster phase, e.g., `online`, `offline`                        |
| phase_name               | string       | Display name of cluster phase                                    |
| status                   | string       | Cluster status, e.g., `normal`, `abnormal`                       |
| operations               | list         | Operation records associated with the cluster                   |
| dns_to_clb               | bool         | Whether the primary domain is forwarded from DNS to CLB          |
| cluster_time_zone        | string       | Cluster time zone                                                |
| cluster_name             | string       | Cluster name                                                     |
| cluster_alias            | string       | Cluster alias                                                    |
| cluster_access_port      | int          | Cluster access port                                              |
| cluster_stats            | dict         | Cluster statistics (structure may vary by DB type)              |
| cluster_type             | string       | Cluster type, e.g., `tendbha`, `tendbsingle`, `MongoReplicaSet`, etc. |
| cluster_type_name        | string       | Display name of cluster type                                     |
| cluster_subzones         | list         | List of cluster zone names                                       |
| cluster_subzone_ids      | list         | List of cluster zone IDs                                         |
| disaster_tolerance_level | string       | Disaster tolerance level, e.g., `NONE`, `SAME_SUBZONE`, `SAME_CITY`, `CROSS_CITY` |
| master_domain            | string       | Primary domain                                                   |
| slave_domain             | string       | Secondary domain (empty if none)                                 |
| cluster_entry            | list         | List of cluster access entries (elements contain `cluster_entry_type`/`entry`/`role`) |
| bk_biz_id                | int          | Business ID                                                      |
| bk_biz_name              | string       | Business name                                                    |
| bk_cloud_id              | int          | Control region ID                                                |
| bk_cloud_name            | string       | Control region name                                              |
| major_version            | string       | Major version number                                             |
| region                   | string       | Region                                                           |
| city                     | string       | City (currently same as `region`)                                |
| db_module_id             | int          | Associated DB module ID                                          |
| db_module_name           | string       | Associated DB module name                                        |
| creator                  | string       | Creator                                                          |
| updater                  | string       | Updater                                                          |
| create_at                | string       | Creation time                                                    |
| update_at                | string       | Update time                                                      |
| cluster_spec             | dict/null    | Cluster specification info, may be `null`                        |
| tags                     | list         | List of cluster tags                                            |
| zone_list                | list         | List of zone IDs                                                 |