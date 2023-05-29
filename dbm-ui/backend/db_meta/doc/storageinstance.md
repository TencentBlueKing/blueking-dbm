# 结构
```python
class StorageInstance(models.Model):
    port = models.PositiveIntegerField(default=0)
    machine = models.ForeignKey(
        Machine,
        to_field='ip',
        db_column='machine',
        on_delete=models.PROTECT,
    )
    app = models.ForeignKey(
        App,
        to_field='name',
        db_column='app',
        on_delete=models.PROTECT,
    )
    cluster = models.ManyToManyField(Cluster, blank=True)
    meta_role = models.ForeignKey(
        MetaRole,
        to_field='name',
        db_column='meta_role',
        on_delete=models.PROTECT)
    class Meta:
        unique_together = ('machine', 'port')
```

| 属性          | 说明                        |
|-------------|---------------------------|
| _port_      | 实例端口                      |
| _machine_   | 实例所在的机器, 关联到 _machine.ip_ |
| _app_       | 业务简称                      |
| _cluster_   | 实例所属集群, 多对多关系             |
| _meta_role_ | 实例的角色, 枚举 `MetaRole`      |

* _app_ 信息是冗余的, 纯粹是为了方便查询. 需要代码保证一致性
* `MetaRole` 由于关联了 `MetaType`, 所以 `MetaType` 实际也冗余了. 需要代码保证一致性
* 理论上实例可以属于多个集群

# _api_
_backend/cmdb/api/storage_instance/apis.py_
## _create_
* 添加实例
* 可以批量添加
* 目前并没有禁止追加

### 参数
如下的 _List_ 作为输入
```json
[
  {
    'ip': string,
    'port': int,
    'meta_role': string
  }
]
```

| 属性          | 类型  | 必要  | 说明                                |
|-------------|-----|-----|-----------------------------------|
| _ip_        | 字符串 | 是   | 实例 _ip_                           |
| _port_      | 整型  | 是   | 实例端口                              |
| _meta_role_ | 字符串 | 是   | 实例角色, 枚举 [MetaRole](meta_role.md) |

* 实例自动继承机器的 _app_ 信息

## _query_
实例查询的输入参数比较特别, 需要专门说下
### 参数
| 参数名          | 类型    | 必要  | 说明                 |
|--------------|-------|-----|--------------------|
| _address_    | 字符串数组 | 否   | _ip, ip#port_ , 域名 |
| _apps_       | 字符串数组 | 否   | 业务简称               |
| _meta_roles_ | 字符串数组 | 否   | `MetaRole`         |

_address_ 是一个数组, 元素可以是
  * _ip_ 地址
  * _ip#port_ 格式的实例地址
  * 域名

## _update_
由于 _status_ 相关的属性还没设计, 所以目前只提供了修改 _meta_role_ 的功能
* 新老 _meta_role_ 对应的 `MetaType` 必须相同
### 参数
如下的 _List_ 作为输入
```json
[
  {
    'ip': string,
    'port': int,
    'meta_role': string
  }
]
```

| 属性          | 类型  | 必要  | 说明             |
|-------------|-----|-----|----------------|
| _ip_        | 字符串 | 是   | 实例 _ip_        |
| _port_      | 整型  | 是   | 实例端口           |
| _meta_role_ | 字符串 | 否   | 实例新 `MetaRole` |

* 如果缺失非必要参数的话, 这接口啥也不干

## _delete_
未实现