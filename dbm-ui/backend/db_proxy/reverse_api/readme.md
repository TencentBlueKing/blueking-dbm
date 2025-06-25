# 用途
* _dbm_ 提供客户端来源受管控的读/写 _api_
* _db_ 机器查询必要的信息
* _db_ 机器以同步方式上报关键信息

# 限制
1. _api_ 只有一个可选参数 _port: int | [int]_

# 实现

```python
class MySQLReverseApiView(BaseReverseApiView):
    @common_swagger_auto_schema(operation_summary=_("获取实例基本信息"))
    @reverse_api(url_path="list_instance_info")
    def list_instance_info(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")

        m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
        q = Q()
        q |= Q(**{"machine": m})

        if port_list:
            q &= Q(**{"port__in": port_list})

        res = []
        if m.access_layer == AccessLayer.PROXY:
            for i in ProxyInstance.objects.filter(q):
                res.append({"ip": i.machine.ip, "port": i.port, "phase": i.phase, "status": i.status})
        else:
            for i in StorageInstance.objects.filter(q):
                res.append({"ip": i.machine.ip, "port": i.port, "phase": i.phase, "status": i.status})

        logger.info(f"instance info: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )
```

1. 继承 `BaseReverseApiView`
2. 使用装饰器 `reverse_api` 实现服务方法
3. 注册 _urls_: `routers.register("mysql", MySQLReverseApiView, basename="")`

## 参数
会的到这样一个 _api_

`/mysql/list_instance_info/?port=10000&port=20000`

* _port_ 可以多次输入, 也可以不输入
* _api_ 并不阻止传入如 `ip=127.1.1.1&role=slave` 这样的参数, 但毫无作用
* 调用框架会传递 `bk_cloud_id, ip, port` 三个参数给服务方法, 其中 `bk_cloud_id, ip` 是框架自动合成的

# 安全
## 框架限制
1. _api_ 服务方法的 `bk_cloud_id, ip` 参数由框架自动生成
2. _ip_ 必须已注册在 _dbm_ 中才允许调用

## 开发规则
1. 不要故意违反 `bk_cloud_id, ip` 的数据可见性限制
2. 尽可能减少每一个 _api_ 返回的数据, 多实现专用 _api_
