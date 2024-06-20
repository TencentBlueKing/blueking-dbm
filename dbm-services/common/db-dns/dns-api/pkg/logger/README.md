

# logger

### 日志管理模块。

* 可选：需使用 Init 初始化指定日志实现（默认为zap）。设置来自配置文件。


	如果没有初始化，则使用默认设置，即：输出到stdout，日志格式为logfmt，日志等级为info。

* 支持输出格式有2种：


	1. JSON: 建议在生产环境使用，便于日志系统正确解析并采集到日志查询数据库。
	2. logfmt: 可以在开发环境使用，输出结构化的日志。


配置文件格式：



	  log:
	    # 可选: stdout, stderr, /path/to/log/file
	    output: /data/logs/myapp/myapp.log
	    # 可选: logfmt, json
	    formater: logfmt
	    # 可选: debug, info, warn, error, fatal, panic
	    level: info
	    # 100M
	    # 时间格式
	    timeformat: 2006-01-02T15:04:05.000Z07:00
	    maxsize: 100
	    # 保留备份日志文件数
	    maxbackups: 3
	    # 保留天数
	    maxage: 30
	    # 启动 level server
	    levelserver: false


