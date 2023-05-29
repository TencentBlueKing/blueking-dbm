package apply

import (
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"sort"
	"strings"

	mapset "github.com/deckarep/golang-set/v2"
)

const (
	// MINDISTRUTE TODO
	MINDISTRUTE = 20
)

type subzone = string

// PickerObject TODO
type PickerObject struct {
	Item          string
	Count         int
	PickDistrbute map[string]int
	ExistSubZone  []subzone // 已存在的园区
	// SatisfiedAssetIds []string                     // 已选择 满足的实例
	SatisfiedHostIds []int
	PickeElements    map[subzone][]InstanceObject // 待选择实例

	// 资源请求在同园区的时候才生效
	ExistEquipmentIds     []string // 已存在的设备Id
	ExistLinkNetdeviceIds []string // 已存在的网卡Id
}

// LockReturnPickers TODO
// GetDetailInfoFromPickers 将匹配好的机器资源,查询出详情结果返回
//
//	@param elements
//	@return []model.BatchGetTbDetailResult
//	@return error
func LockReturnPickers(elements []*PickerObject, mode string) ([]model.BatchGetTbDetailResult, error) {
	var getter []model.BatchGetTbDetail
	for _, v := range elements {
		getter = append(getter, model.BatchGetTbDetail{
			Item:      v.Item,
			BkHostIds: v.SatisfiedHostIds,
		})
	}
	data, err := model.BatchGetSatisfiedByAssetIds(getter, mode)
	if err != nil {
		logger.Error(fmt.Sprintf("选择到合适的实例，获取实例详情失败%s", err.Error()))
	}
	if mode == model.Used {
		sendArchiverTask(data)
	}
	return data, err
}

// sendArchiverTask 归档
//
//	@param data
func sendArchiverTask(data []model.BatchGetTbDetailResult) {
	for _, v := range data {
		for _, l := range v.Data {
			task.ArchiverResourceChan <- l.ID
		}
	}
}

// createNice 创建Nice值
//
//	@param cpu
//	@param mem
//	@param sdd
//	@param hdd
//	@return rs
func createNice(cpu int, mem, sdd, hdd int) (rs int64) {
	rs = int64(cpu*1000000000000 + mem*100000 + sdd + hdd)
	return
}

// AnalysisResource 待选取资源排序
//
//	@param ins
//	@return map
func AnalysisResource(ins []model.TbRpDetail, israndom bool) map[string][]InstanceObject {
	result := make(map[string][]InstanceObject)
	for _, v := range ins {
		linkids := strings.Split(v.NetDeviceID, ",")
		t := InstanceObject{
			BkHostId:        v.BkHostID,
			Equipment:       v.RackID,
			LinkNetdeviceId: linkids,
			Nice:            createNice(int(v.CPUNum), v.DramCap, 0, 0),
		}
		if israndom {
			result["RANDOM"] = append(result["RANDOM"], t)
		} else {
			result[v.SubZone] = append(result[v.SubZone], t)
		}
	}

	// 对个每个camp里面机器按照规则排序，便于后续picker的时候取最优的
	for key := range result {
		sort.Sort(Wrapper{result[key], func(p, q *InstanceObject) bool {
			return q.Nice > p.Nice // Nice 递减排序
		}})
	}
	return result
}

// NewPicker 初始化资源选择器
//
//	@param count
//	@param item
//	@return *PickerObject
func NewPicker(count int, item string) *PickerObject {
	return &PickerObject{
		Item:                  item,
		Count:                 count,
		ExistEquipmentIds:     make([]string, 0),
		ExistLinkNetdeviceIds: make([]string, 0),
		SatisfiedHostIds:      make([]int, 0),
		PickDistrbute:         make(map[string]int),
	}
}

// PickerSameSubZone TODO
func (c *PickerObject) PickerSameSubZone(cross_switch bool) {
	sortSubZones := c.sortSubZone(false)
	if len(sortSubZones) <= 0 {
		return
	}
	for _, subzone := range sortSubZones {
		logger.Info("PickerSameSubZone:PickeElements: %v", c.PickeElements[subzone])
		if len(c.PickeElements[subzone]) < c.Count || len(c.PickeElements[subzone]) <= 0 {
			continue
		}
		logger.Info("dbeug %v", subzone)
		logger.Info("dbeug %v", c.PickeElements[subzone])
		c.SatisfiedHostIds = []int{}
		c.ExistEquipmentIds = []string{}
		c.ExistLinkNetdeviceIds = []string{}
		for idx := range c.PickeElements[subzone] {
			logger.Info("loop %d", idx)
			c.pickerOne(subzone, cross_switch)
			// 匹配资源完成
			logger.Info(fmt.Sprintf("surplus %s,%d", subzone, len(c.PickeElements[subzone])))
			logger.Info(fmt.Sprintf("%s,%d,%d", subzone, c.Count, len(c.SatisfiedHostIds)))
			if c.PickerDone() {
				return
			}
		}
	}
}

// Picker 筛选，匹配资源
//
//	@receiver c
//	@param cross_campus 是否跨园区
func (c *PickerObject) Picker(cross_subzone bool) {
	campKeys := c.sortSubZone(cross_subzone)
	if len(campKeys) <= 0 {
		return
	}
	subzoneChan := make(chan subzone, len(campKeys))
	for _, v := range campKeys {
		subzoneChan <- v
	}
	for {
		select {
		case subzone := <-subzoneChan:
			if len(c.PickeElements[subzone]) == 0 {
				delete(c.PickeElements, subzone)
			}
			if len(c.sortSubZone(cross_subzone)) == 0 {
				logger.Info("go out here")
				return
			}
			logger.Info(fmt.Sprintf("surplus %s,%d", subzone, len(c.PickeElements[subzone])))
			logger.Info(fmt.Sprintf("%s,%d,%d", subzone, c.Count, len(c.SatisfiedHostIds)))
			if c.pickerOne(subzone, false) {
				delete(c.PickeElements, subzone)
			}
			// 匹配资源完成
			if c.PickerDone() {
				return
			}
			// 非跨园区循环读取
			if !cross_subzone {
				subzoneChan <- subzone
				continue
			}
			// 跨园区
			if len(subzoneChan) <= 0 {
				return
			}
		}
	}
}

func (c *PickerObject) pickerOne(key string, cross_switch bool) bool {
	c.ExistSubZone = append(c.ExistSubZone, key)
	for _, v := range c.PickeElements[key] {
		if cross_switch {
			if !c.CrossRackCheck(v) || !c.CrossSwitchCheck(v) {
				// 如果存在交集,则删除该元素
				c.deleteElement(key, v.BkHostId)
				continue
			}
		}
		c.ExistEquipmentIds = append(c.ExistEquipmentIds, v.Equipment)
		c.SatisfiedHostIds = append(c.SatisfiedHostIds, v.BkHostId)
		c.ExistLinkNetdeviceIds = append(c.ExistLinkNetdeviceIds, v.LinkNetdeviceId...)
		c.PickDistrbute[key]++
		c.deleteElement(key, v.BkHostId)
		return true
	}
	return len(c.PickeElements) <= 0
}

// CrossSwitchCheck 跨交换机检查
func (c *PickerObject) CrossSwitchCheck(v InstanceObject) bool {
	if len(v.LinkNetdeviceId) <= 0 {
		return false
	}
	return c.InterSectForLinkNetDevice(v.LinkNetdeviceId) == 0
}

// CrossRackCheck 跨机架检查
func (c *PickerObject) CrossRackCheck(v InstanceObject) bool {
	if cmutil.IsEmpty(v.Equipment) {
		return false
	}
	return c.InterSectForEquipment(v.Equipment) == 0
}

// DebugDistrubuteLog TODO
func (o *PickerObject) DebugDistrubuteLog() {
	for key, v := range o.PickDistrbute {
		logger.Debug(fmt.Sprintf("Zone:%s,PickCount:%d", key, v))
	}
}

func (c *PickerObject) deleteElement(key string, bkhostId int) {
	var k []InstanceObject
	for _, v := range c.PickeElements[key] {
		if v.BkHostId != bkhostId {
			k = append(k, v)
		}
	}
	c.PickeElements[key] = k
}

// PreselectedSatisfiedInstance TODO
func (c *PickerObject) PreselectedSatisfiedInstance() error {
	affectRows, err := model.UpdateTbRpDetail(c.SatisfiedHostIds, model.Preselected)
	if err != nil {
		return err
	}
	if int(affectRows) != len(c.SatisfiedHostIds) {
		return fmt.Errorf("update %d qualified resouece to preselectd,only %d real update status", len(c.SatisfiedHostIds),
			affectRows)
	}
	return nil
}

// RollbackSatisfiedInstanceStatusUnused TODO
func (c *PickerObject) RollbackSatisfiedInstanceStatusUnused() error {
	return model.UpdateTbRpDetailStatusAtSelling(c.SatisfiedHostIds, model.Unused)
}

// CampusNice TODO
type CampusNice struct {
	Campus string `json:"campus"`
	Count  int    `json:"count"`
}

// CampusWrapper TODO
type CampusWrapper struct {
	Campus []CampusNice
	by     func(p, q *CampusNice) bool
}

// Len 用于排序
func (pw CampusWrapper) Len() int {
	return len(pw.Campus)
}

// Swap 用于排序
func (pw CampusWrapper) Swap(i, j int) {
	pw.Campus[i], pw.Campus[j] = pw.Campus[j], pw.Campus[i]
}

// Less 用于排序
func (pw CampusWrapper) Less(i, j int) bool {
	return pw.by(&pw.Campus[i], &pw.Campus[j])
}

// sortSubZone 根据排序剩下有效的园区
func (c *PickerObject) sortSubZone(cross_subzone bool) []string {
	var keys []string
	var campusNice []CampusNice
	for key, campusIntances := range c.PickeElements {
		//	keys = append(keys, key)
		if !cross_subzone || cmutil.ElementNotInArry(key, c.ExistSubZone) {
			campusNice = append(campusNice, CampusNice{
				Campus: key,
				Count:  len(campusIntances),
			})
		}
	}
	// 按照每个园区的数量从大到小排序
	sort.Sort(CampusWrapper{campusNice, func(p, q *CampusNice) bool {
		return q.Count < p.Count
	}})
	for _, capmus := range campusNice {
		keys = append(keys, capmus.Campus)
	}
	return keys
}

// PickerDone TODO
func (c *PickerObject) PickerDone() bool {
	return len(c.SatisfiedHostIds) == c.Count
}

// InterSectForEquipment 求交集 EquipmentID
func (c *PickerObject) InterSectForEquipment(equipmentId string) int {
	baseSet := mapset.NewSet[string]()
	for _, v := range cmutil.RemoveDuplicate(c.ExistEquipmentIds) {
		baseSet.Add(v)
	}
	myset := mapset.NewSet[string]()
	myset.Add(equipmentId)
	return baseSet.Intersect(myset).Cardinality()
}

// InterSectForLinkNetDevice 求交集 LinkNetDeviceIds
func (c *PickerObject) InterSectForLinkNetDevice(linkDeviceIds []string) int {
	baseSet := mapset.NewSet[string]()
	for _, v := range cmutil.RemoveDuplicate(c.ExistLinkNetdeviceIds) {
		baseSet.Add(v)
	}
	myset := mapset.NewSet[string]()
	for _, linkId := range linkDeviceIds {
		if cmutil.IsNotEmpty(linkId) {
			myset.Add(linkId)
		}
	}
	return baseSet.Intersect(myset).Cardinality()
}
