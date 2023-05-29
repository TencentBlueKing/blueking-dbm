// Package task TODO
package task

import (
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"runtime/debug"
	"time"
)

// ApplyResponeLogItem TODO
type ApplyResponeLogItem struct {
	RequestId string
	Data      []model.BatchGetTbDetailResult
}

// ApplyResponeLogChan TODO
var ApplyResponeLogChan chan ApplyResponeLogItem

// ArchiverResourceChan TODO
var ArchiverResourceChan chan int

// RecordRsOperatorInfoChan TODO
var RecordRsOperatorInfoChan chan model.TbRpOperationInfo

// RuningTask TODO
// RuningApplyTask
var RuningTask chan struct{}

func init() {
	ApplyResponeLogChan = make(chan ApplyResponeLogItem, 100)
	ArchiverResourceChan = make(chan int, 200)
	RecordRsOperatorInfoChan = make(chan model.TbRpOperationInfo, 20)
	RuningTask = make(chan struct{}, 100)
}

// init TODO
// StartTask 异步写日志
func init() {
	defer func() {
		if r := recover(); r != nil {
			logger.Error("panic error:%v,stack:%s", r, string(debug.Stack()))
			return
		}
	}()
	go func() {
		var archIds []int
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case d := <-ApplyResponeLogChan:
				err := recordTask(d)
				if err != nil {
					logger.Error("record log failed, %s", err.Error())
				}
			case id := <-ArchiverResourceChan:
				if len(RuningTask) > 0 {
					archIds = append(archIds, id)
				} else {
					archIds = append(archIds, id)
					if err := archiverResource(archIds); err != nil {
						logger.Warn("archiver resouce failed %s", err.Error())
					}
					archIds = []int{}
				}
			case <-ticker.C:
				if len(RuningTask) <= 0 && len(archIds) > 0 {
					if err := archiverResource(archIds); err != nil {
						logger.Warn("archiver resouce failed %s", err.Error())
					}
					archIds = []int{}
				}
			case info := <-RecordRsOperatorInfoChan:
				if err := recordRsOperationInfo(info); err != nil {
					logger.Error("failed to record resource operation log %s", err.Error())
				}
			}

		}
	}()
}

// archiverResource 异步归档资源
func archiverResource(ids []int) (err error) {
	return model.ArchiverResouce(ids)
}

func recordTask(data ApplyResponeLogItem) error {
	if data.Data == nil {
		return fmt.Errorf("data is nill")
	}
	m := []model.TbRpApplyDetailLog{}
	for _, v := range data.Data {
		for _, vv := range v.Data {
			m = append(m, model.TbRpApplyDetailLog{
				RequestID:  data.RequestId,
				IP:         vv.IP,
				BkCloudID:  vv.BkCloudID,
				Item:       v.Item,
				BkHostID:   vv.BkHostID,
				UpdateTime: time.Now(),
				CreateTime: time.Now(),
			})
			logger.Debug("%s -- %s -- %s -- %s", v.Item, vv.IP, vv.RackID, vv.NetDeviceID)
		}
	}
	return model.CreateBatchTbRpOpsAPIDetailLog(m)
}

func recordRsOperationInfo(data model.TbRpOperationInfo) (err error) {
	return model.DB.Self.Table(model.TbRpOperationInfoTableName()).Create(&data).Error
}
