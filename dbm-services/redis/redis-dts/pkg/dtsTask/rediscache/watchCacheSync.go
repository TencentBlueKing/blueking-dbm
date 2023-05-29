package rediscache

import (
	"encoding/base64"
	"fmt"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
)

// WatchCacheSyncTask ..
type WatchCacheSyncTask struct {
	MakeCacheSyncTask
}

// TaskType task类型
func (task *WatchCacheSyncTask) TaskType() string {
	return constvar.WatchCacheSyncTaskType
}

// NextTask 下一个task类型
func (task *WatchCacheSyncTask) NextTask() string {
	return ""
}

// NewWatchCacheSyncTask 新建任务
func NewWatchCacheSyncTask(row *tendisdb.TbTendisDTSTask) *WatchCacheSyncTask {
	ret := &WatchCacheSyncTask{
		MakeCacheSyncTask: *NewMakeCacheSyncTask(row),
	}
	return ret
}

// Execute 程序重新拉起后监听以往处于taskType='makeShake',status=1状态的redis-shake
func (task *WatchCacheSyncTask) Execute() {
	if task.Err != nil {
		return
	}

	defer func() {
		if task.Err != nil {
			task.SetStatus(-1)
			task.SetMessage(task.Err.Error())
			task.UpdateRow()
		}
	}()
	defer task.Logger.Info(fmt.Sprintf("end WatchCacheSyncTask"))

	task.SetStatus(1)
	task.UpdateDbAndLogLocal("开始watch redis-shake port:%d", task.RowData.SyncerPort)

	task.GetMyRedisShakeTool(false)
	if task.Err != nil {
		return
	}

	srcPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.SrcPassword)
	dstPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.DstPassword)

	task.SrcADDR = fmt.Sprintf("%s:%d", task.RowData.SrcIP, task.RowData.SrcPort)
	task.SrcPassword = string(srcPasswd)
	task.DstADDR = task.RowData.DstCluster
	task.DstPassword = string(dstPasswd)

	task.HTTPProfile = task.RowData.SyncerPort
	task.SystemProfile = task.HTTPProfile + 1

	task.Logger.Info(fmt.Sprintf("WatchCacheSyncTask 开始处理,srcTendis:%s srcAddr:%s",
		task.RowData.SrcCluster, task.SrcADDR))

	task.WatchShake()
	return
}
