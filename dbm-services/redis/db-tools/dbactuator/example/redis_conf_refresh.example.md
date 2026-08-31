### redis conf refresh
把下发的配置模板 refresh & apply 到本机实例.

`./dbactuator_redis --uid={{uid}} --root_id={{root_id}} --node_id={{node_id}} --version_id={{version_id}} --atom-job-list="redis_conf_refresh" --payload='{{payload_base64}}'`

`--data_dir`、`--backup_dir` 可以留空.

配置项归属 (谁说了算):

- 不许被下发值改动, 冲突即失败: `dir`、`port`、`bind`(只许新增地址, 不许丢)、`replicaof`
- 机器为准, 但可被显式下发覆盖: `requirepass` —— 只在 `port_target_passwords` 给了该端口时才改
- 渲染结果优先, 缺失才抄本机: `masterauth`、`loadmodule`. 改密码时已有的 `masterauth` 挪不挪, 由探测主库的结果决定
- 模板为准: 其余配置项; 目标版本已经删掉的指令随之消失
- 不由模板做主: `maxmemory`(dbmon 动态设置, 取磁盘值)、`databases`(payload)、`cluster-enabled`(由 cluster_type 推导)、tendisplus `rocks.*`(按本机内存与实例数算)

`apply_mode`:

- `conf_file`: 只把渲染结果写到 redis.conf, 不碰运行态
- `config_set`: 只对运行态可改的项 CONFIG SET, 不写文件. 启动项 (dir / port / bind / loadmodule / rename-command 等) 有差异时失败, 改用 `restart`; 密码 / 主从 / maxmemory 这类项只 warn 不 SET. 改密码是唯一例外: CONFIG SET 后必须 CONFIG REWRITE 落盘, 再用新密码重连
- `restart`: 写文件并重启. 文件和运行态都已经到位时只再钉一次复制, 不会无谓重启. 新配置起不来就失败, 把新文件留在原地, 不回滚旧配置

三个模式都幂等: 文件和运行态已经是目标状态时直接成功.

#### 改密码

`config_set` 与 `restart` 都支持, `conf_file` 拒绝 (只写文件不碰运行态, 会留下"文件新密码 / 进程旧密码"的窗口, 而 dbmon、proxy、dbha 都从文件读密码). 两个模式的暴露面不一样, 按场景选:

- `config_set` 不打断已建立的复制链路 (链路早认证过了, `masterauth` 只在下次重连时才用到), 所以能对 master / slave 并行改. 代价是 `masterauth` 判断错了当场看不出来, 要等到未来某次重连才爆
- `restart` 一定会重连, `masterauth` 错了 `settleReplication` 当场等不到链路, 任务直接失败. 暴露得早, 但破坏性大, 而且"探测 → 实例起来"这段窗口比 `config_set` 长得多, **期间上游不能动主库**

`masterauth` 不跟着 `requirepass` 走, 而是探过主库之后再决定. 改错了任一个方向都会让从库在重连时 AUTH 失败 —— 主库还没改就跟过去, 或主库已经改了却不跟 —— 而光看本机分不出这两种. 所以渲染之前先用目标密码实拨一次主库:

| 探测结果 | 处置 |
|---|---|
| 连得上 | `masterauth` 跟到新密码 |
| 认证被拒 | 主库还没改, 原样留着 |
| 探不动 (网络不通、主库挂了) | 同样留着不动, 现存链路还活着, 保持现状不会更糟 |

结论由两个模式共用: `config_set` 拿它决定要不要 `CONFIG SET masterauth`, `restart` 拿它决定渲染进配置文件的 `masterauth` 是哪个. 校验按结论两头都拦: 该跟没跟、不该跟却跟了, 都算渲染错误.

留着不动的从库就欠了一次修复. 按"先改从库 → 切换 → 再改新从库"滚动改密码时必然走到这里: **主库改完之后要对从库再跑一次本 act**, 那一趟探测才会通过. 重跑是安全的 —— `masterauth` 与 `requirepass` 各自判断该不该动, 不会因为 `requirepass` 已经到位就把 `masterauth` 一起跳过.

cluster 架构不参与探测: 它的凭据由 `redis_switch` / `redis_cluster_failover` 统一管.

原始 payload

```json
{
    "ip": "1.1.1.1",
    "ports": [30000, 30001],
    "role": "redis_slave",
    "cluster_type": "TwemproxyRedisInstance",
    "apply_mode": "restart",
    "sync_wait_timeout_seconds": 1800,
    "port_conf_configs": {
        "30000": {
            "conf_configs": {
                "bind": "{{address}}",
                "port": "{{port}}",
                "maxmemory": "{{maxmemory}}",
                "replica-lazy-flush": "yes"
                ...
            },
            "databases": 2,
            "load_modules_detail": []
        },
        "30001": {
            "conf_configs": {
                "bind": "{{address}}",
                "port": "{{port}}",
                "requirepass": "{{password}}",
                "replica-lazy-flush": "yes"
                ...
            },
            "databases": 2
        }
    },
    "port_target_passwords": {
        "30001": "newpasswd"
    }
}
```

`port_target_passwords` 可以整个不传 (不改密码), 或只给需要改的端口, 此时 `apply_mode` 不能是 `conf_file`. 空串是合法目标, 表示改成无密码 —— 所以"要不要改密码"看的是端口在不在这个 map 里, 不是值是否为空.
