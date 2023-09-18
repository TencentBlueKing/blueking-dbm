package cron

import (
	"fmt"

	"dbm-services/mysql/db-partition/errno"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/monitor"
	"dbm-services/mysql/db-partition/service"
	"dbm-services/mysql/db-partition/util"

	"golang.org/x/exp/slog"
)

// Scheduler TODO
var Scheduler string

// Run TODO
func (m PartitionJob) Run() {
	var err error
	Scheduler, err = util.ExecShellCommand(false, "hostname -I")
	if err != nil {
		Scheduler = "0.0.0.0"
	}
	if m.CronType == Heartbeat {
		monitor.SendMetric(Scheduler)
		return
	}
	key := fmt.Sprintf("%s_%d_%s", m.CronType, m.ZoneOffset, m.CronDate)
	model.Lock(key)
	m.ExecutePartitionCron(service.Tendbha)
	m.ExecutePartitionCron(service.Tendbcluster)
	flag, err := model.Lock(key)
	if err != nil {
		dimension := monitor.NewDeveloperEventDimension(Scheduler)
		content := fmt.Sprintf("partition error. set redis mutual exclusion error: %s", err.Error())
		monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
		slog.Error("msg", "model.Lock err", err)
	} else if flag {
		m.ExecutePartitionCron(service.Tendbha)
		m.ExecutePartitionCron(service.Tendbcluster)
	} else {
		slog.Warn("set redis mutual exclusion fail, do nothing", "key", key)
	}
}

// ExecutePartitionCron 执行所有业务的分区
func (m PartitionJob) ExecutePartitionCron(clusterType string) {
	zone := fmt.Sprintf("%+03d:00", m.ZoneOffset)
	needMysql, errOuter := service.NeedPartition(m.CronType, clusterType, m.ZoneOffset, m.CronDate)
	if errOuter != nil {
		dimension := monitor.NewDeveloperEventDimension(Scheduler)
		content := fmt.Sprintf("partition error. get need partition list fail: %s", errOuter.Error())
		monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
		slog.Error("msg", "get need partition list fail", errOuter)
		return
	}
	for _, item := range needMysql {
		objects, err := (*item).DryRun()
		if err != nil {
			code, _ := errno.DecodeErr(err)
			if code == errno.NothingToDo.Code {
				service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
					item.ImmuteDomain, zone, m.CronDate, Scheduler, "{}",
					errno.NothingToDo.Message, service.CheckSucceeded, item.ClusterType)
				continue
			} else {
				dimension := monitor.NewPartitionEventDimension(item.BkBizId, *item.BkCloudId, item.ImmuteDomain)
				content := fmt.Sprintf("partition error. get partition sql fail: %s", err.Error())
				monitor.SendEvent(monitor.PartitionEvent, dimension, content, "0.0.0.0")
				service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
					item.ImmuteDomain, zone, m.CronDate, Scheduler, "{}",
					content, service.CheckFailed, item.ClusterType)
				slog.Error(fmt.Sprintf("%v", *item), "get partition sql fail", err)
				continue
			}
		}
		service.CreatePartitionTicket(*item, objects, m.ZoneOffset, m.CronDate, Scheduler)
	}
}
