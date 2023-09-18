package model

import (
	flag "github.com/spf13/pflag"
	"github.com/spf13/viper"
)

// InitEnv 环境变量初始化
func InitEnv() {
	// meta DB参数
	viper.BindEnv("db.user", "DB_USER")
	viper.BindEnv("db.password", "DB_PASSWORD")
	viper.BindEnv("db.name", "DB_NAME")
	viper.BindEnv("db.host", "DB_HOST")
	viper.BindEnv("db.port", "DB_PORT")

	viper.BindEnv("redis.password", "REDIS_PASSWORD")
	viper.BindEnv("redis.host", "REDIS_HOST")
	viper.BindEnv("redis.port", "REDIS_PORT")

	// 分区服务
	viper.BindEnv("listen_address", "LISTEN_ADDRESS")
	viper.BindEnv("cron.timing_hour", "CRON_TIMING_HOUR")
	viper.BindEnv("cron.retry_hour", "CRON_RETRY_HOUR")

	viper.BindEnv("dbm_db_name", "DBM_DB_NAME")
	viper.BindEnv("db_remote_service", "DB_REMOTE_SERVICE")
	viper.BindEnv("db_meta_service", "DB_META_SERVICE")
	viper.BindEnv("dbm_ticket_service", "DBM_TICKET_SERVICE")
	viper.BindEnv("bk_app_code", "BK_APP_CODE")
	viper.BindEnv("bk_app_secret", "BK_APP_SECRET")

	// pt-osc参数
	viper.BindEnv("pt.max_load.threads_running", "PT_MAX_LOAD_THREADS_RUNNING")
	viper.BindEnv("pt.critical_load.threads_running", "PT_CRITICAL_LOAD_THREADs_RUNNING")
	viper.BindEnv("pt.lock_wait_timeout", "PT_LOCK_WAIT_TIMEOUT")
	viper.BindEnv("pt.max_size", "PT_MAX_SIZE")
	viper.BindEnv("pt.max_rows", "PT_MAX_ROWS")

	viper.BindEnv("monitor.service", "MONITOR_SERVICE")
	// 蓝鲸监控自定义事件
	viper.BindEnv("monitor.event.data_id", "MONITOR_EVENT_DATA_ID")
	viper.BindEnv("monitor.event.access_token", "MONITOR_EVENT_ACCESS_TOKEN")
	// 蓝鲸监控自定义指标
	viper.BindEnv("monitor.metric.data_id", "MONITOR_METRIC_DATA_ID")
	viper.BindEnv("monitor.metric.access_token", "MONITOR_METRIC_ACCESS_TOKEN")

	viper.BindEnv("dba.bk_biz_id", "DBA_BK_BIZ_ID")

	// 程序日志参数, 可选参数
	viper.BindEnv("log.path", "LOG_PATH")
	viper.BindEnv("log.level", "LOG_LEVEL")
	viper.BindEnv("log.max_size", "LOG_MAX_SIZE")
	viper.BindEnv("log.max_age", "LOG_MAX_AGE")
	viper.BindEnv("log.max_backups", "LOG_MAX_BACKUPS")

	flag.Bool("migrate", false,
		"run migrate to databases, not exit.")
	viper.BindPFlags(flag.CommandLine)
}
