package myredis

import (
	"context"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// ClusterSetSlotInfo 命令:cluster setslot info信息
type ClusterSetSlotInfo struct {
	// dst Node命令cluster setslot info结果
	ImportingTaskIDs      []string
	ImportingSlotList     []int
	ImportingSlotMap      map[int]bool `json:"-"`
	SuccessImportSlotList []int
	SuccessImportSlotMap  map[int]bool `json:"-"`
	FailImportSlotList    []int
	FailImportSlotMap     map[int]bool `json:"-"`
	RunningRcvTaskNum     int
	SuccessRcvTaskNum     int
	FailRcvTaskNum        int

	// src Node命令cluster setslot info结果
	MigratingTaskIDs       []string
	MigratingSlotList      []int
	MigratingSlotMap       map[int]bool `json:"-"`
	SuccessMigrateSlotList []int
	SuccessMigrateSlotMap  map[int]bool `json:"-"`
	FailMigrateSlotList    []int
	FailMigrateSlotMap     map[int]bool `json:"-"`
	RunningSendTaskNum     int
	SuccessSendTaskNum     int
	FailSendTaskNum        int
}

// ToString ..
func (info *ClusterSetSlotInfo) ToString() string {
	ret, _ := json.Marshal(info)
	return string(ret)
}

// IsImportingSlot 是否是import中的slots
func (info *ClusterSetSlotInfo) IsImportingSlot(slotid int) bool {
	_, ok := info.ImportingSlotMap[slotid]
	return ok
}

// IsSuccessImportSlot 是否是成功import的slots
func (info *ClusterSetSlotInfo) IsSuccessImportSlot(slotid int) bool {
	_, ok := info.SuccessImportSlotMap[slotid]
	return ok
}

// IsFailImportSlot 是否是import失败的slot
func (info *ClusterSetSlotInfo) IsFailImportSlot(slotid int) bool {
	_, ok := info.FailImportSlotMap[slotid]
	return ok
}

// GetDstRedisSlotsStatus 获取目标slots的状态
func (info *ClusterSetSlotInfo) GetDstRedisSlotsStatus(slotList []int) (
	importing, successImport, failImport, unknow []int,
) {
	for _, slotItem := range slotList {
		if info.IsImportingSlot(slotItem) {
			importing = append(importing, slotItem)
		} else if info.IsSuccessImportSlot(slotItem) {
			successImport = append(successImport, slotItem)
		} else if info.IsFailImportSlot(slotItem) {
			failImport = append(failImport, slotItem)
		} else {
			unknow = append(unknow, slotItem)
		}
	}
	return
}

// IsMigratingSlot 是否是migrate中的slot
func (info *ClusterSetSlotInfo) IsMigratingSlot(slotid int) bool {
	_, ok := info.MigratingSlotMap[slotid]
	return ok
}

// IsSuccessMigrateSlot 是否是成功migrate的slot
func (info *ClusterSetSlotInfo) IsSuccessMigrateSlot(slotid int) bool {
	_, ok := info.SuccessMigrateSlotMap[slotid]
	return ok
}

// IsFailMigrateSlot 是否是migrate失败的slot
func (info *ClusterSetSlotInfo) IsFailMigrateSlot(slotid int) bool {
	_, ok := info.FailMigrateSlotMap[slotid]
	return ok
}

// GetSrcSlotsStatus 获取迁移任务中src节点上的slots状态
func (info *ClusterSetSlotInfo) GetSrcSlotsStatus(slotList []int) (
	migrating, successMigrate, failMigrate, unknow []int) {
	for _, slotItem := range slotList {
		if info.IsMigratingSlot(slotItem) {
			migrating = append(migrating, slotItem)
		} else if info.IsSuccessMigrateSlot(slotItem) {
			successMigrate = append(successMigrate, slotItem)
		} else if info.IsFailMigrateSlot(slotItem) {
			failMigrate = append(failMigrate, slotItem)
		} else {
			unknow = append(unknow, slotItem)
		}
	}
	return
}

// GetClusterSetSlotInfo 获取'cluster setslot info'的结果并解析
func GetClusterSetSlotInfo(nodeAddr, nodePassword string) (
	setSlotInfo *ClusterSetSlotInfo, err error) {
	// 测试nodeAddr的连通性
	cli01, err := NewRedisClient(nodeAddr, nodePassword, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return nil, err
	}
	defer cli01.Close()

	cmd := []interface{}{"cluster", "setslot", "info"}
	ret, err := cli01.InstanceClient.Do(context.TODO(), cmd...).Result()
	setSlotsInfo := &ClusterSetSlotInfo{}
	setSlotsInfo.ImportingSlotMap = make(map[int]bool)
	setSlotsInfo.SuccessImportSlotMap = make(map[int]bool)
	setSlotsInfo.FailImportSlotMap = make(map[int]bool)
	setSlotsInfo.MigratingSlotMap = make(map[int]bool)
	setSlotsInfo.SuccessMigrateSlotMap = make(map[int]bool)
	setSlotsInfo.FailMigrateSlotMap = make(map[int]bool)

	taskTimePattern := regexp.MustCompile(`\[.*?\]`)

	importInfos, ok := ret.([]interface{})
	if ok == false {
		err = fmt.Errorf(
			`GetClusterSetSlotInfo cmd:'cluster setslot info' result not []interface{},nodeAddr:%s.cmd:%v`,
			nodeAddr, cmd)
		mylog.Logger.Error(err.Error())
		return nil, err
	}
	for _, info01 := range importInfos {
		infoItem := info01.(string)
		infoItem = strings.TrimSpace(infoItem)
		if infoItem == "" {
			continue
		}
		list01 := strings.SplitN(infoItem, ":", 2)
		if len(list01) < 2 {
			continue
		}
		list01[1] = strings.TrimSpace(list01[1])
		if list01[0] == "importing taskid" {
			list01[1] = strings.TrimSpace(list01[1])
			if list01[1] == "" {
				continue
			}
			list01[1] = taskTimePattern.ReplaceAllString(list01[1], "") // 将task 时间替换掉
			setSlotsInfo.ImportingTaskIDs = strings.Fields(list01[1])
		} else if list01[0] == "importing slots" {
			setSlotsInfo.ImportingSlotList, setSlotsInfo.ImportingSlotMap, _, _, _ = DecodeSlotsFromStr(list01[1], " ")
		} else if list01[0] == "success import slots" {
			setSlotsInfo.SuccessImportSlotList, setSlotsInfo.SuccessImportSlotMap, _, _, _ = DecodeSlotsFromStr(list01[1], " ")
		} else if list01[0] == "fail import slots" {
			setSlotsInfo.FailImportSlotList, setSlotsInfo.FailImportSlotMap, _, _, _ = DecodeSlotsFromStr(list01[1], " ")
		} else if list01[0] == "running receiver task num" {
			setSlotsInfo.RunningRcvTaskNum, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "success receiver task num" {
			setSlotsInfo.SuccessRcvTaskNum, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "fail receiver task num" {
			setSlotsInfo.FailRcvTaskNum, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "migrating taskid" {
			if infoItem == "" {
				continue
			}
			list01[1] = taskTimePattern.ReplaceAllString(list01[1], "") // 将task 时间替换掉
			setSlotsInfo.MigratingTaskIDs = strings.Fields(list01[1])
		} else if list01[0] == "migrating slots" {
			setSlotsInfo.MigratingSlotList, setSlotsInfo.MigratingSlotMap, _, _, _ = DecodeSlotsFromStr(list01[1], " ")
		} else if list01[0] == "success migrate slots" {
			setSlotsInfo.SuccessMigrateSlotList, setSlotsInfo.SuccessMigrateSlotMap, _, _, _ = DecodeSlotsFromStr(list01[1], " ")
		} else if list01[0] == "fail migrate slots" {
			setSlotsInfo.FailMigrateSlotList, setSlotsInfo.FailMigrateSlotMap, _, _, _ = DecodeSlotsFromStr(list01[1], " ")
		} else if list01[0] == "running sender task num" {
			list01[1] = strings.TrimSpace(list01[1])
			setSlotsInfo.RunningSendTaskNum, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "success sender task num" {
			list01[1] = strings.TrimSpace(list01[1])
			setSlotsInfo.SuccessSendTaskNum, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "fail sender task num" {
			list01[1] = strings.TrimSpace(list01[1])
			setSlotsInfo.FailSendTaskNum, _ = strconv.Atoi(list01[1])
		}
	}
	return setSlotsInfo, nil
}
