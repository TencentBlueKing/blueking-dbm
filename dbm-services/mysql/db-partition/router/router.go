// Package router TODO
package router

import (
	"dbm-services/mysql/db-partition/handler"
	v2 "dbm-services/mysql/db-partition/handler/v2"

	"github.com/gin-gonic/gin"
)

// RegisterRouter TODO
func RegisterRouter(engine *gin.Engine) {
	p := engine.Group("/partition")
	// 配置查询
	p.POST("/query_conf", handler.GetPartitionsConfig)
	p.POST("/query_log", handler.GetPartitionLog)
	// 创建分区配置
	p.POST("/create_conf", handler.CreatePartitionsConfig)
	// 删除分区配置
	p.POST("/del_conf", handler.DeletePartitionsConfig)
	p.POST("/cluster_del_conf", handler.DeletePartitionsConfigByCluster)
	p.POST("/dry_run", handler.DryRun)
	p.POST("/disable_partition", handler.DisablePartition)
	p.POST("/enable_partition", handler.EnablePartition)
	p.POST("/disable_partition_cluster", handler.DisablePartitionByCluster)
	p.POST("/enable_partition_cluster", handler.EnablePartitionByCluster)
	// 更新分区配置
	p.POST("/update_conf", handler.UpdatePartitionsConfig)
	p.POST("/create_log", handler.CreatePartitionLog)
	p.POST("/cron_start", handler.CronStart)
	p.POST("/cron_entries", handler.CronEntries)
	p.POST("/cron_stop", handler.CronStop)
	p.POST("/run_once", handler.RunOnce)
	p.POST("/init_monitor", handler.InitMonitor)
	// 迁移分区配置
	p.POST("/migrate_config", handler.MigrateConfig)
	// 巡检
	p.POST("/check_log", handler.CheckLog)
	p.POST("/partition_conf_query", handler.PartitionConfQuery)

	// v2 版本路由组 /partition/v2
	p2 := engine.Group("/partition/v2")
	p2.POST("/query_conf", v2.QueryConf)
	p2.POST("/create_conf", v2.CreateConf)
	p2.POST("/clone_conf", v2.CloneConf)
	p2.POST("/update_conf", v2.UpdateConf)
	p2.POST("/del_conf", v2.DelConf)
	p2.POST("/disable_partition", v2.DisablePartition)
	p2.POST("/enable_partition", v2.EnablePartition)
	p2.POST("/disable_partition_cluster", v2.DisablePartitionByCluster)
	p2.POST("/enable_partition_cluster", v2.EnablePartitionByCluster)
	p2.POST("/cluster_del_conf", v2.DeletePartitionByCluster)
	// v2 巡检：配置侧枚举（执行结果由 Django 查 report 库）
	p2.POST("/check/list_biz", v2.ListCheckBiz)
	p2.POST("/check/list_conf_ids", v2.ListCheckConfIds)

}
