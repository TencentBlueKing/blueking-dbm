# start and stop 
# 启动服务（后台模式）
sh start.sh

# 停止服务（优雅退出）
sh stop.sh


# meta operation
# 查看全部实例
bk-dbmon meta list --port all
# 查看指定实例
bk-dbmon meta list --port 27017,27018
# 清理无效实例信息
bk-dbmon meta delete --port 27017,27018

# 事件告警操作
> 用于控制事件告警的屏蔽和解除
- bk-dbmon alarm shield --port all   ## 屏蔽告警
- bk-dbmon alarm unblock  --port 27017,27018  # 解除屏蔽
- bk-dbmon alarm list   --port 27017,27018 # 查看当前屏蔽列表

# config operation
> 配置修改后无需重启服务，会自动生效
- bk-dbmon config get-all --port all # 列出所有配置
- bk-dbmon config set --port all -s $seg -k $k -$v $v
- bk-dbmon config get --port all -s $seg -k $k -V|--value $v  # get-one
## 配置列表:
- 备份启停：-s backup -k enable -V true or false 
- parselog启停: -s parselog -k enable -V true or false


# --port参数说明
--port 27017 # 指定单个实例
--port 27017,27018 # 指定多个实例
--port all # 所有实例
--port 0 # 所有实例


# conn.sh
```bash
# 进入指定实例的 mongo shell（退出后自动断开）
sh conn.sh <端口号>
# 示例：
sh conn.sh 27017

# 执行单个命令（非交互模式）
sh conn.sh <端口号> "<MongoDB命令>"
# 示例：
sh conn.sh 27017 "db.serverStatus().ok"

# 批量执行命令（支持特殊参数）
sh conn.sh all "<MongoDB命令>"    # 所有实例执行
sh conn.sh 0 "<MongoDB命令>"      # 等效于 all
```