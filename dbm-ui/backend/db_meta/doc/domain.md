# 结构
```python
class Domain(models.Model):
    name = models.CharField(max_length=64, primary_key=True)
    ip = models.GenericIPAddressField(default='')

    class Meta:
        unique_together = ('name', 'ip')
```

这个模块目前实际是个占位设计, 对应了 _gcs_ 和 _scr_ 中的 _dns_ 相关表, 不排除后续会改名什么的

| 属性   | 说明               |
|------|------------------|
| name | 合法的域名            |
| ip   | 域名 _bind_ 的 _ip_ |

# _api_
_backend/cmdb/api/domain/apis.py_
## _bind_
新增一个域名绑定
### 参数
| 参数名    | 类型    | 必要  | 说明            |
|--------|-------|-----|---------------|
| _name_ | 字符串   | 是   | 域名            |
| _ips_  | 字符串数组 | 是   | 需要绑定的 _ip_ 列表 |

* `Domain` 和 [Cluster](cluster.md) 的 _name_ 共享一个命名空间
* 无论是在 `Domain` 还是 `Cluster` 中, 新增对象时都需要检查 _name_ 是不是在对方已经被使用

## _query_
略

## _unbind_
* 解绑域名解析
* 如果需要完全删除域名, 则需要传入其绑定的所有 _ip_

### 参数
* 同 [_api bind_](#_bind_)
* 输入 _ip_ 和域名无绑定关系时会抛出异常