# 故障自愈

### 两种方案
1. 秒级自愈：时效性要求较高，由 「DBHA」中心化进行探测并触发自愈过程，快速进行切换
2. 分钟级自愈：由各个 DB 主机的 exporter/监控程序 进行「指标上报/事件上报」，通过「蓝鲸监控」触发事件进行自愈

### 蓝鲸监控告警自愈原理
1. 配置采集，下发 exporter 到对应机器上进行指标上报（或自行进行事件上报）
2. 在蓝鲸监控中配置对应的告警策略，并配置告警处理套餐
3. 当达到阈值触发监控告警时，将触发处理套餐，调用 DBM 的回调接口创建自愈单据
4. 监控回调的参数为 `backend.db_monitor.mock_data.CALLBACK_REQUEST`，其中包含告警通知人、策略、标签、维度等信息
5. 通过序列化器 `AlarmCallBackDataSerializer` 对回调参数进行清洗，得到通用的单据创建参数
6. 调用 `Ticket.create_ticket_from_bk_monitor` 创建单据，其中会使用单据定义的 `alarm_transform_serializer` 将回调参数转化为单据执行所需的参数
7. 接下来则是执行 DBM 的单据流程

### 开发流程（这里以 redis 的自愈为例子）
1. 首先完成自愈的 flow 和 ticket 开发，详见 `backend/flow` 和 `backend/ticket` 两个目录。
如：`backend/ticket/builders/redis/redis_maxmemory_set.py`
2. 实现告警转换序列化器 `alarm_transform_serializer`，如 `alarm_transform_serializer = RedisClusterMaxmemorySetAlarmTransformSerializer`
3. 给对应的监控策略添加「单据类型标签」，`backend/db_monitor/tpls/alarm/redis/Redis(TendisCache)主机内存使用率.json` 

### 注意
1. 单个监控策略可以配置多个「单据类型标签」，多个单据将同时被触发（无顺序），如果有顺序要求，请再封装一个单据类型，串联两个 flow
2. [不推荐] 若多个策略配置了同一个「单据类型标签」，多告警策略同时触发时将会触发两次自愈单据，请确认是否符合预期