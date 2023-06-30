/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package model

import (
	"encoding/json"
	"fmt"
	"regexp"
	"time"

	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"gorm.io/gorm"
)

const (
	// Unused TODO
	Unused = "Unused"
	// Preselected 预选中
	Preselected = "Preselected"
	// Prepoccupied 已被接口申请,但不一定实际使用
	Prepoccupied = "Prepoccupied"
	// Used TODO
	Used = "Used"
)

// TbRpDetail  机器资源明细表
type TbRpDetail struct {
	ID              int                      `gorm:"primary_key;auto_increment;not_null" json:"-"`
	BkCloudID       int                      `gorm:"uniqueIndex:ip;column:bk_cloud_id;type:int(11);not null;comment:'云区域 ID'" json:"bk_cloud_id"`
	BkBizId         int                      `gorm:"column:bk_biz_id;type:int(11);not null;comment:'机器当前所属业务'" json:"bk_biz_id"`
	DedicatedBizs   json.RawMessage          `gorm:"column:dedicated_bizs;type:json;comment:'专属业务,可属于多个'" json:"for_bizs"`
	RsTypes         json.RawMessage          `gorm:"column:rs_types;type:json;comment:'资源类型标签'" json:"resource_types"`
	Bizs            map[string]string        `gorm:"-" json:"-"`
	BkHostID        int                      `gorm:"index:idx_host_id;column:bk_host_id;type:int(11);not null;comment:'bk主机ID'" json:"bk_host_id"`
	IP              string                   `gorm:"uniqueIndex:ip;column:ip;type:varchar(20);not null" json:"ip"` //  svr ip
	AssetID         string                   `gorm:"column:asset_id;type:varchar(64);not null;comment:'固定资产编号'" json:"asset_id"`
	DeviceClass     string                   `gorm:"column:device_class;type:varchar(64);not null" json:"device_class"` //  对应机型 A30,D3
	SvrTypeName     string                   `gorm:"column:svr_type_name;type:varchar(64);not null;comment:'服务器型号,判断是否是云机器'" json:"svr_type_name"`
	CPUNum          int                      `gorm:"column:cpu_num;type:int(11);not null;comment:'cpu核数'" json:"cpu_num"`
	DramCap         int                      `gorm:"column:dram_cap;type:int(11);not null;comment:'内存大小'" json:"dram_cap"`
	StorageDevice   json.RawMessage          `gorm:"column:storage_device;type:json;comment:'磁盘设备'" json:"storage_device"`
	TotalStorageCap int                      `gorm:"column:total_storage_cap;type:int(11);comment:'磁盘总容量'" json:"total_storage_cap"`
	Storages        map[string]bk.DiskDetail `gorm:"-" json:"-"`
	Raid            string                   `gorm:"column:raid;type:varchar(20);not null" json:"raid"`               //  磁盘Raid
	CityID          string                   `gorm:"column:city_id;type:varchar(64);not null" json:"city_id"`         //  实际城市ID
	City            string                   `gorm:"column:city;type:varchar(128);not null" json:"city"`              //  实际城市名称
	SubZone         string                   `gorm:"column:sub_zone;type:varchar(32);not null" json:"sub_zone"`       //  园区, 例如光明 cc_device_szone
	SubZoneID       string                   `gorm:"column:sub_zone_id;type:varchar(64);not null" json:"sub_zone_id"` //  园区ID cc_device_szone_id
	RackID          string                   `gorm:"column:rack_id;type:varchar(64);not null" json:"rack_id"`         //  存放机架ID,判断是否是同机架
	NetDeviceID     string                   `gorm:"column:net_device_id;type:varchar(128)" json:"net_device_id"`     //  网络设备ID, 判断是同交换机
	Label           json.RawMessage          `gorm:"column:label;type:json" json:"label"`                             //  标签
	LabelMap        map[string]string        `gorm:"-" json:"-"`
	IsInit          int                      `gorm:"column:is_init;type:int(11);comment:'是否初始化过'" json:"-"`  // 是否初始化过
	IsIdle          int                      `gorm:"column:is_idle;type:int(11);comment:'是否空闲检查过'" json:"-"` // 是否空闲检查过
	Status          string                   `gorm:"column:status;type:varchar(20);not null" json:"status"`  //  Unused: 未使用 Used: 已经售卖被使用: Preselected:预占用
	BkAgentId       string                   `gorm:"index:idx_bk_agent_id;column:bk_agent_id;type:varchar(64);not null" json:"bk_agent_id"`
	// gse Agent当前运行状态码, -1:未知 0:初始安装 1:启动中 2:运行中 3:有损状态 4:繁忙状态 5:升级中 6:停止中 7:解除安装
	AgentStatusCode int `gorm:"column:gse_agent_status_code;type:int(11);not null" json:"gse_agent_status_code"`
	// agent status 最后一次更新时间
	AgentStatusUpdateTime time.Time `gorm:"column:agent_status_update_time;type:timestamp;default:1970-01-01 08:00:01" json:"agent_status_update_time"`
	ConsumeTime           time.Time `gorm:"column:consume_time;type:timestamp;default:1970-01-01 08:00:01" json:"consume_time"` // 消费时间
	UpdateTime            time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"`   // 最后修改时间
	CreateTime            time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"`   // 创建时间
}

// TableName TODO
func (TbRpDetail) TableName() string {
	return TbRpDetailName()
}

// TbRpDetailName TODO
func TbRpDetailName() string {
	return "tb_rp_detail"
}

// DeviceClassIsLocalSSD TODO
func (t TbRpDetail) DeviceClassIsLocalSSD() bool {
	if cmutil.IsEmpty(t.DeviceClass) {
		return false
	}
	r := regexp.MustCompile("^IT")
	return r.MatchString(t.DeviceClass)
}

// UnmarshalDiskInfo TODO
func (t *TbRpDetail) UnmarshalDiskInfo() (err error) {
	t.Storages = make(map[string]bk.DiskDetail)
	err = json.Unmarshal(t.StorageDevice, &t.Storages)
	return
}

// GetTbRpDetailAll TODO
func GetTbRpDetailAll(sqlstr string) ([]TbRpDetail, error) {
	var m []TbRpDetail
	err := DB.Self.Table(TbRpDetailName()).Raw(sqlstr).Scan(&m).Error
	if err != nil {
		return nil, err
	}
	return m, nil
}

// SetMore TODO
func (t *TbRpDetail) SetMore(ip string, diskMap map[string]*bk.ShellResCollection) {
	if disk, ok := diskMap[ip]; ok {
		if t.CPUNum <= 0 {
			t.CPUNum = disk.Cpu
		}
		if t.DramCap <= 0 {
			t.DramCap = disk.Mem
		}
		dks := disk.Disk
		if t.DeviceClassIsLocalSSD() {
			dks = bk.SetDiskType(disk.Disk, bk.SSD)
		}
		if r, err := bk.MarshalDisk(dks); err != nil {
			logger.Warn("disk marshal failed %s", err.Error())
		} else {
			t.StorageDevice = []byte(r)
		}
	}
}

// TbRpDetailGetter TODO
func TbRpDetailGetter() ([]TbRpDetail, error) {
	return nil, nil
}

// UpdateTbRpDetail TODO
func UpdateTbRpDetail(ids []int, status string) (int64, error) {
	db := DB.Self.Table(TbRpDetailName()).Where("bk_host_id in (?)", ids).Update("status", status)
	return db.RowsAffected, db.Error
}

// UpdateTbRpDetailStatusAtSelling TODO
func UpdateTbRpDetailStatusAtSelling(ids []int, status string) error {
	return DB.Self.Table(TbRpDetailName()).Where("bk_host_id in (?) and status = ? ", ids, Preselected).
		Update("status", status).Error
}

// DeleteTbRpDetail TODO
func DeleteTbRpDetail(ids []int) (int64, error) {
	db := DB.Self.Table(TbRpDetailName()).Where("bk_host_id in (?)", ids).Delete(&TbRpDetail{})
	return db.RowsAffected, db.Error
}

// BatchGetTbDetail TODO
type BatchGetTbDetail struct {
	Item      string `json:"item"`
	BkHostIds []int  `json:"bk_host_ids"`
}

// BatchGetTbDetailResult TODO
type BatchGetTbDetailResult struct {
	Item string       `json:"item"`
	Data []TbRpDetail `json:"data"`
}

// BatchGetSatisfiedByAssetIds TODO
func BatchGetSatisfiedByAssetIds(elements []BatchGetTbDetail, mode string) (result []BatchGetTbDetailResult,
	err error) {
	db := DB.Self.Begin()
	defer func() {
		if err != nil {
			db.Rollback()
		}
	}()
	for _, v := range elements {
		d, err := SetSatisfiedStatus(db, v.BkHostIds, mode)
		if err != nil {
			logger.Error(fmt.Sprintf("Item:%s,failed to obtain resource details!,Error is %s", v.Item, err.Error()))
			return nil, err
		}
		result = append(result, BatchGetTbDetailResult{Item: v.Item, Data: d})
	}
	err = db.Commit().Error
	if err != nil {
		logger.Error(fmt.Sprintf("transaction commit failed: %s", err.Error()))
		return nil, err
	}
	return
}

// SetSatisfiedStatus TODO
func SetSatisfiedStatus(tx *gorm.DB, bkhostIds []int, status string) (result []TbRpDetail, err error) {
	err = tx.Exec("select * from tb_rp_detail where bk_host_id in (?) for update", bkhostIds).Error
	if err != nil {
		return nil, err
	}
	err = tx.Raw("select * from tb_rp_detail where  bk_host_id in ? ", bkhostIds).Scan(&result).Error
	if err != nil {
		return nil, err
	}
	if len(bkhostIds) != len(result) {
		logger.Error(fmt.Sprintf("Get TbRpDetail is %v", result))
		return nil, fmt.Errorf("requried count is %d,But Only Get %d", len(bkhostIds), len(result))
	}
	rdb := tx.Exec("update tb_rp_detail set status=?,consume_time=now() where bk_host_id in ?", status, bkhostIds)
	if rdb.Error != nil {
		logger.Error(fmt.Sprintf("update status Failed,Error %s", err.Error()))
		return nil, err
	}
	if int(rdb.RowsAffected) != len(bkhostIds) {
		return nil, fmt.Errorf("requried Update Instance count is %d,But Affected Rows Count Only %d", len(bkhostIds),
			rdb.RowsAffected)
	}
	return result, nil
}

// GetLabels TODO
func GetLabels(applyfor string) (data []map[string]string, err error) {
	var ls []string
	db := DB.Self.Table(TbRpDetailName())
	if cmutil.IsNotEmpty(applyfor) {
		db.Where("apply_for = ? and label is not null ", applyfor)
	}
	if err = db.Select("label").Scan(&ls).Error; err != nil {
		logger.Error(fmt.Sprintf("Get Labels Failes %s", err.Error()))
		return
	}
	checkExist := make(map[string]struct{})
	for _, v := range ls {
		var ldata map[string]string
		if err = json.Unmarshal([]byte(v), &ldata); err != nil {
			logger.Error(fmt.Sprintf("Json Unmarshal Failed %s", err.Error()))
			continue
		}
		for key, value := range ldata {
			exkey := fmt.Sprintf("%s:%s", key, value)
			if _, ok := checkExist[exkey]; !ok {
				checkExist[exkey] = struct{}{}
				data = append(data, map[string]string{key: value})
			}
		}
	}
	return
}
