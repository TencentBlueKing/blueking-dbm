# 用途
在定义了机器的 `MetaType` 后, 某些情况下机器上的实例还会有功能上的差别. 如 `TenDBCluster` 的 `remote` 就会分为 `Master` 和 `Slave`

* `MetaRole` 用来区分同一 `MetaType` 下实例的更具体的差别
* 同时也定义了某一 `MetaType` 所能部署的实例类型

# 结构

```python
class MetaRole(models.Model):
    name = models.CharField(max_length=64, primary_key=True)
    meta_type = models.ForeignKey(
        MetaType,
        to_field='name',
        db_column='meta_type',
        on_delete=models.PROTECT
    )
```

# 静态数据

* 没有强制的命名规则, 但是不同 `MetaType` 的 `MetaRole` 最好不要重名
* 需要人工事先录入

## 示例
| name     | meta_type   |
|----------|-------------|
| master   | remote      |
| repeater | remote      |
| slave    | remote      |
| orphan   | tendbsingle |

* `TenDBCluster` 的 `存储层` ---- `remote` 可以有 _3_ 种角色的实例, 分别是 `master, slave, repeater`
* `TenDBSingle` 的 `存储层` ---- `tendbsingle` 只能部署角色为 `orphan` 的实例