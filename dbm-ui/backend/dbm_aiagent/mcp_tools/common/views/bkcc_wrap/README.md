# BKCC Wrap MCP 工具

MCP 分组：`bkcc-wrap`

默认权限：`DBManagePermission`

敏感控制指 **Callee Plan**（`enable_callee_plan`）：写操作需先 `register_callee_plan` 登记参数，实际调用时参数必须与 plan 完全一致。

---

## bkcc_wrap_list_hosts_without_biz

| 项 | 说明 |
|---|---|
| 描述 | 没有业务信息的主机查询 |
| 读/写 | 读 |
| 敏感控制 | 否 |

**入参**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_cloud_id` | int | 是 | 云区域 ID |
| `ips` | list[str] | 是 | IP 列表 |

**返回**

`info` 为数组，元素字段如下：

| 字段 | 类型 | 说明 |
|---|---|---|
| `bk_agent_id` | str | Agent ID |
| `bk_bak_operator` | str | 备份负责人 |
| `bk_cloud_id` | int | 云区域 ID |
| `bk_cloud_inst_id` | str | 云实例 ID |
| `bk_host_id` | int | 主机 ID |
| `bk_host_innerip` | str | 内网 IP |
| `bk_idc_area` | str | IDC 区域 |
| `bk_idc_area_id` | int | IDC 区域 ID |
| `bk_os_name` | str | 操作系统 |
| `bk_svr_device_cls_name` | str | 机型 |
| `idc_city_id` | str | 城市 ID |
| `idc_city_name` | str | 城市 |
| `idc_id` | int | IDC ID |
| `idc_name` | str | IDC 名称 |
| `net_device_id` | str | 网络设备 ID |
| `operator` | str | 负责人 |
| `rack` | str | 机架 |
| `rack_id` | str | 机架 ID |
| `sub_zone` | str | 园区 |
| `sub_zone_id` | str | 园区 ID |

**校验规则**

- `bk_cloud_id`、`ips` 必填

---

## bkcc_wrap_get_biz_internal_module

| 项 | 说明 |
|---|---|
| 描述 | 查询业务的空闲机/故障机/待回收模块 |
| 读/写 | 读 |
| 敏感控制 | 否 |

**入参**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_biz_id` | int | 是 | 业务 ID |

**返回**

```json
{
  "bk_set_id": 143,
  "bk_set_name": "空闲机池",
  "module": [
    {
      "bk_module_id": 1762,
      "bk_module_name": "空闲机",
      "default": 1,
      "host_apply_enabled": false
    }
  ]
}
```

**校验规则**

- `bk_biz_id` 必填

---

## bkcc_wrap_find_host_biz_relations

| 项 | 说明 |
|---|---|
| 描述 | 查询主机业务关系信息 |
| 读/写 | 读 |
| 敏感控制 | 否 |

**入参**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_host_ids` | list[int] | 是 | 主机 ID 列表 |

**返回**

```json
{
  "info": [
    {
      "bk_biz_id": 100,
      "bk_host_id": 123,
      "bk_module_id": 456,
      "bk_set_id": 789,
      "bk_supplier_account": "0"
    }
  ]
}
```

**校验规则**

- `bk_host_ids` 必填

---

## bkcc_wrap_update_hosts_operator

| 项 | 说明 |
|---|---|
| 描述 | 修改机器负责人 |
| 读/写 | 写 |
| 敏感控制 | **是** |

**入参**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_host_ids` | list[int] | 是 | 主机 ID 列表，至少 1 个 |
| `operators` | list[str] | 否 | 主负责人，对应 CMDB `operator` |
| `bak_operators` | list[str] | 否 | 备份负责人，对应 CMDB `bk_bak_operator` |

**返回**

```json
{
  "bk_host_ids": [123, 456]
}
```

**校验规则**

- 所有主机必须存在于 DBM 纳管池
- 当前用户必须是每台机器的主负责人或备份负责人

---

## bkcc_wrap_transfer_host_to_idlemodule

| 项 | 说明 |
|---|---|
| 描述 | 主机移动到空闲机模块 |
| 读/写 | 写 |
| 敏感控制 | **是** |

**入参**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_biz_id` | int | 是 | 业务 ID |
| `bk_host_ids` | list[int] | 是 | 主机 ID 列表，至少 1 个 |

**返回**

```json
{
  "bk_biz_id": 100,
  "bk_host_ids": [123, 456]
}
```

**校验规则**

- 当前用户必须是每台机器的主负责人或备份负责人
- 主机**不能**在 DBM 纳管池中

---

## bkcc_wrap_transfer_host_across_biz

| 项 | 说明 |
|---|---|
| 描述 | 跨业务空闲机转移 |
| 读/写 | 写 |
| 敏感控制 | **是** |

**入参**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `src_bk_biz_id` | int | 是 | 源业务 ID |
| `dst_bk_biz_id` | int | 是 | 目标业务 ID |
| `bk_host_ids` | list[int] | 是 | 主机 ID 列表，至少 1 个 |

**返回**

```json
{
  "src_bk_biz_id": 100,
  "dst_bk_biz_id": 200,
  "dst_idle_module_id": 1762,
  "bk_host_ids": [123, 456]
}
```

**校验规则**

- `src_bk_biz_id` 与 `dst_bk_biz_id` 不能相同
- 当前用户必须是每台机器的主负责人或备份负责人
- 主机**不能**在 DBM 纳管池中
- 目标业务须存在空闲机模块（`default == 1` 且 `bk_module_name == "空闲机"`）
- 源业务侧主机须在空闲机池（由 CMDB API 内置校验）
