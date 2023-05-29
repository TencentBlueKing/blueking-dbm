package tendisssd

import (
	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/util"
	"encoding/base64"
	"fmt"
)

// WatchOldSyncTask 很多时候 redis-sync 已经拉起,状态为runnig(taskrow.status==1 taskrow.taskType="makeSync")
// 而此时我们需要暂停 dbm-services/redis/redis-dts 重新替换 dbm-services/redis/redis-dts的介质
// 再次拉起后, 以前(taskrow.status==1 taskrow.taskType="makeSync")的task其相关状态依然需要我们不断更新
// 注意: 该任务只在 dbm-services/redis/redis-dts 被拉起一瞬间创建,只监听 以往 (taskrow.status==1 taskrow.taskType="makeSync")的task
// 对于新增的 (taskrow.status==1 taskrow.taskType="makeSync")的task 不做任何处理
type WatchOldSyncTask struct {
	MakeSyncTask
}

// TaskType task类型
func (task *WatchOldSyncTask) TaskType() string {
	return constvar.WatchOldSyncTaskType
}

// NextTask 下一个task类型
func (task *WatchOldSyncTask) NextTask() string {
	return ""
}

// NewWatchOldSync 新建任务
func NewWatchOldSync(row *tendisdb.TbTendisDTSTask) *WatchOldSyncTask {
	ret := &WatchOldSyncTask{
		MakeSyncTask: *NewMakeSyncTask(row),
	}
	return ret
}

// Execute 程序重新拉起后监听以往处于taskType='makeSync',status=1状态的redis-sync
func (task *WatchOldSyncTask) Execute() {
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

	if (task.RowData.TaskType != constvar.MakeSyncTaskType) || (task.RowData.Status != 1) {
		return
	}
	redisClient, err := util.IsToolExecutableInCurrDir("redis-cli")
	if err != nil {
		task.Err = err
		return
	}
	task.SetSyncSeqSaveInterface()
	if task.Err != nil {
		return
	}

	srcPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.SrcPassword)
	dstPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.DstPassword)

	task.RedisCliTool = redisClient
	task.SrcADDR = fmt.Sprintf("%s:%d", task.RowData.SrcIP, task.RowData.SrcPort)
	task.SrcPassword = string(srcPasswd)
	task.DstADDR = task.RowData.DstCluster
	task.DstPassword = string(dstPasswd)

	task.WatchSync()
	return
}
