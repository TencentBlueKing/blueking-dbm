整体分为两个部分
* 提供 _mcp_ 协议服务, 用 _mcp-go_ 实现的 _mcp_server_
* 作为 _mcp_server_ 后端, 提供真实逻辑功能, 集成在 _DBM_ 中的 _mcp_backend_

效果是
1. 所有 _mcp_ 相关功能只需要在 _DBM django_ 工程中开发
2. _go_ 实现的 _mcp-server_ 理论上部署后无需管理

这样的好处是
1. _DBM django_ 可以用 _django db model_ 访问元数据
2. 默认已有所有相关周边系统的权限
3. 方便操作单据相关数据

# _MCP_SERVER_
以 _bcs_ 容器方式部署, 在同一工程内访问 _dbm service api_

```shell
db-mcp-server

Usage:
  db-mcp-server [flags]

Flags:
      --bind-address string           The IP address on which to listen for the --port port. (default "0.0.0.0:80")
      --bk-app-code string            
      --bk-app-secret string          
  -h, --help                          help for db-mcp-server
      --mcp-backend-base-url string   
  -s, --skip-auth-check
```

```shell
./db-mcp-server --bind-address 0.0.0.0:9191 --skip-auth-check --mcp-backend-base-url http://localhost:8080/mcp
```

1. 周期性自动调用 _${base_url}/list_handlers/_ 注册新 _handler_ , 每 _1_ 分钟更新一次
2. 只支持 _sse_ 方式工作
3. 所有对 _mcp_backend_ 的调用都实现了自动重试, 其中
  * _mcp tool_ 调用 _4_ 次重试, 间隔 _2s_
  * _list handlers_ _4_ 次重试, 间隔 _5s_

# _MCP_BACKEND_

`dbm-ui/backend/db_mcp_backends`

```python
class MCPToolDemoViewSet(BaseMCPView):
    @mcp_api(
        scope="demo",
        name="add",
        description="add",
        request_schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "a": openapi.Schema(type=openapi.TYPE_INTEGER, description=""),
                "b": openapi.Schema(type=openapi.TYPE_INTEGER, description=""),
            },
            required=["a", "b"],
        ),
        response_schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"result": openapi.Schema(type=openapi.TYPE_INTEGER, description="")},
            required=["result"],
        ),
    )
    def add(self, request: Request, *args, **kwargs):
        body = json.loads(request.body.decode("utf-8"))
        a = body.get("a")
        b = body.get("b")
        return JsonResponse({"code": 0, "data": {"result": a + b}, "message": ""})
```

1. 装饰器中的 _scope + name_ 必须全局唯一, 决定 _tools_ 的调用路径
2. _description_ 非常重要, 认真写好功能描述
3. 两个 _schema_ 非常重要, 认真写好说明和类型
4. _response_ 必须是个 _object_, 比如上面例子的 `{"result": 100}`