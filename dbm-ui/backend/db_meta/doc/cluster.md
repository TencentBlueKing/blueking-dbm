# 结构

```python
class Cluster(models.Model):
    name = models.CharField(max_length=64, primary_key=True, default='')
    app = models.ForeignKey(
        App,
        to_field='name',
        db_column='app',
        on_delete=models.PROTECT,
    )
    meta_cluster_type = models.ForeignKey(
        MetaClusterType,
        to_field='name',
        on_delete=models.PROTECT
    )
```

| 属性                  | 说明                         |
|---------------------|----------------------------|
| _name_              | 集群名, 大部分时候都是 `Domain` 中的域名 |
| _app_               | 业务简称                       |
| _meta_cluster_type_ | 集群类型, 枚举 `MetaClusterType` |

## 和 `Domain` 关系

1. 理论上一个集群可以有多个域名. 如果要做关联关系则应该在 `Domain` 加 _foreign key_. 这会导致新增的 `Domain` 必须绑定到某一个 `Cluster`
2. 参考 _gcs_ 的经验, _dns_ 系统会注册很多非 _db_ 类的域名, 上面的限制会导致无法实现
3. 用 _many to many_ 来模拟实现上非常麻烦

所以干脆 `Cluster` 和 `Domain` 不做关联关系, 一致性用代码来保证

# _api_

_backend/cmdb/api/cluster/apis.py_

## _create_

建立一个集群

### 参数

| 参数名                 | 类型    | 必要  | 说明                         |
|---------------------|-------|-----|----------------------------|
| _app_               | 字符串   | 是   | 业务简称                       |
| _name_              | 字符串   | 是   | 集群名                        |
| _instances_         | 对象    | 是   | 实例信息                       |
| _binds_             | 字符串列表 | 否   | 需要做域名绑定的 _ip_ 列表           |
| _meta_cluster_type_ | 字符串   | 是   | 集群类型, 枚举 `MetaClusterType` |

_instances_ 的元素是一个如下的对象, _2_ 个子项都不是必须的, 即可以传入一个 _'instances': {}_ 这样的空对象进来

```json
{
  'proxy': [
    {
      'ip': string,
      'port': int
    }
  ],
  'storage': [
    {
      'ip': string,
      'port': int
    }
  ]
}
```

1. [Domain](domain.md) 和 `Cluster` 的 _name_ 共享一个命名空间 . 无论是在 `Domain` 还是 `Cluster` 中, 新增对象时都需要检查 _name_ 是不是在对方已经被使用
2. 如果输入的实例已经属于某个集群, 则这个集群的所有实例都必须在输入的实例中
3. 与输入集群有关联的所有实例都必须在输入实例中

> `关联实例`
> 1. `存储层` 实例的关联实例是有同步关系的 `存储层` 实例 和对应的 `接入层` 实例
> 2. `接入层` 实例的关联实例是对应的 `存储层` 实例
> 
> `所有关联实例`
> 依照上述关系链定义递归的查询出整个关系网