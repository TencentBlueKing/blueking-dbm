package consts

// twemproxy monitor event categories
const (
	EventTwemproxyRestart = "twemproxy_restart"
	EventTwemproxyLogin   = "twemproxy_login"
)

// predixy monitor event categories
const (
	EventPredixyRestart = "predixy_restart"
	EventPredixyLogin   = "predixy_login"
)

// redis monitor event categories
const (
	EventRedisLogin        = "redis_login"
	EventRedisSync         = "redis_sync"
	EventRedisPersist      = "redis_persist"
	EventRedisMaxmemory    = "redis_maxmemory"
	EventTendisBinlogLen   = "tendis_binlog_len"
	EventRedisClusterState = "redis_cluster_state"
	EventRedisLog          = "redis_log"

	EventTimeDiffWarning = 120
	EventTimeDiffError   = 300

	EventMasterLastIOSecWarning = 600
	EventMasterLastIOSecError   = 1200

	EventSSDBinlogLenWarnning = 20000000
	EventSSDBinlogLenError    = 50000000

	EventMemoryUsedPercentWarnning = 80 // 80%
	EventMemoryUsedPercentError    = 90 // 90%
)

// warn level
const (
	WarnLevelError   = "error"
	WarnLevelWarning = "warning"
	WarnLevelSuccess = "success"
	WarnLevelMessage = "message"
)
