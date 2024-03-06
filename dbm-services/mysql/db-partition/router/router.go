// Package router TODO
package router

import (
	"dbm-services/mysql/db-partition/handler"

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
	p.POST("/init_monitor", handler.InitMonitor)
	// 迁移分区配置
	p.POST("/migrate_config", handler.MigrateConfig)
}
