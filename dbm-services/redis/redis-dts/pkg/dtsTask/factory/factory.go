// Package factory TODO
package factory

import (
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask/rediscache"
	"dbm-services/redis/redis-dts/pkg/dtsTask/tendisplus"
	"dbm-services/redis/redis-dts/pkg/dtsTask/tendispluslightning"
	"dbm-services/redis/redis-dts/pkg/dtsTask/tendisssd"
)

// MyTasker task接口
type MyTasker interface {
	TaskType() string
	NextTask() string
	Init()
	Execute()
}

// MyTendisDtsTaskFactory task工厂
func MyTendisDtsTaskFactory(taskRow *tendisdb.TbTendisDTSTask) MyTasker {
	if taskRow.TaskType == (&tendisssd.TendisBackupTask{}).TaskType() {
		// tendis-ssd
		return tendisssd.NewTendisBackupTask(taskRow)
	} else if taskRow.TaskType == (&tendisssd.BakcupFileFetchTask{}).TaskType() {
		return tendisssd.NewBakcupFileFetchTask(taskRow)
	} else if taskRow.TaskType == (&tendisssd.TredisdumpTask{}).TaskType() {
		return tendisssd.NewTredisdumpTask(taskRow)
	} else if taskRow.TaskType == (&tendisssd.CmdsImporterTask{}).TaskType() {
		return tendisssd.NewCmdsImporterTask(taskRow)
	} else if taskRow.TaskType == (&tendisssd.MakeSyncTask{}).TaskType() {
		return tendisssd.NewMakeSyncTask(taskRow)
	} else if taskRow.TaskType == (&rediscache.MakeCacheSyncTask{}).TaskType() {
		// redis-cache
		return rediscache.NewMakeCacheSyncTask(taskRow)
	} else if taskRow.TaskType == (&rediscache.WatchCacheSyncTask{}).TaskType() {
		return rediscache.NewWatchCacheSyncTask(taskRow)
	} else if taskRow.TaskType == (&tendisplus.MakeSyncTask{}).TaskType() {
		// tendisplus
		return tendisplus.NewMakeSyncTask(taskRow)
	} else if taskRow.TaskType == constvar.TendisplusSendBulkTaskType ||
		taskRow.TaskType == constvar.TendisplusSendIncrTaskType {
		return tendisplus.NewWatchSyncTask(taskRow)
	}
	return nil
}

// MyTendisplusLightningTaskFactory task工厂
func MyTendisplusLightningTaskFactory(taskRow *tendisdb.TbTendisplusLightningTask) MyTasker {
	if taskRow.TaskType == (&tendispluslightning.CosFileDownloadTask{}).TaskType() {
		return tendispluslightning.NewCosFileDownloadTask(taskRow)
	} else if taskRow.TaskType == (&tendispluslightning.FileSplitTask{}).TaskType() {
		return tendispluslightning.NewFileSplitTask(taskRow)
	} else if taskRow.TaskType == (&tendispluslightning.GenerateSstTask{}).TaskType() {
		return tendispluslightning.NewGenerateSstTask(taskRow)
	} else if taskRow.TaskType == (&tendispluslightning.ScpSstTask{}).TaskType() {
		return tendispluslightning.NewScpSstTask(taskRow)
	} else if taskRow.TaskType == (&tendispluslightning.SlaveLoadSstTask{}).TaskType() {
		return tendispluslightning.NewSlaveLoadSstTask(taskRow)
	}
	return nil
}
