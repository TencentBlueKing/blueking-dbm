package tendisplus

import (
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
)

// WatchSyncTask 很多时候tendisplus redis-sync 已经拉起,状态为runnig(taskrow.status==1 taskrow.taskType="tendisplusSendBulk/tendisplusSendIncr")
// 而此时我们需要暂停 dbm-services/redis/redis-dts 重新替换 dbm-services/redis/redis-dts的介质
// 再次拉起后, 以前(taskrow.status==1 taskrow.taskType="makeSync")的task其相关状态依然需要我们不断更新
// 注意: 该任务只在 dbm-services/redis/redis-dts 被拉起一瞬间创建,只监听 以往 (taskrow.status==1 taskrow.taskType="makeSync")的task
// 对于新增的 (taskrow.status==1 taskrow.taskType="makeSync")的task 不做任何处理
type WatchSyncTask struct {
	MakeSyncTask
}

// TaskType task类型
func (task *WatchSyncTask) TaskType() string {
	return constvar.WatchOldSyncTaskType
}

// NextTask 下一个task类型
func (task *WatchSyncTask) NextTask() string {
	return ""
}

// NewWatchSyncTask 新建任务
func NewWatchSyncTask(row *tendisdb.TbTendisDTSTask) *WatchSyncTask {
	ret := &WatchSyncTask{
		MakeSyncTask: *NewMakeSyncTask(row),
	}
	return ret
}

// Execute 程序重新拉起后监听以往处于taskType='makeSync',status=1状态的redis-sync
func (task *WatchSyncTask) Execute() {
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

	task.GetMyRedisCliTool()
	if task.Err != nil {
		return
	}
	task.GetMyRedisSyncTool()
	if task.Err != nil {
		return
	}

	task.WatchSync()
	return
}
