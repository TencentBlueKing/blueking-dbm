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
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// TbRpDailySnapShot 机器资源快照表
type TbRpDailySnapShot struct {
	ID              int             `gorm:"primary_key;auto_increment;not_null" json:"-"`
	ReportDay       string          `gorm:"column:report_day;type:varchar(32);not null;comment:'上报日期'" json:"report_day"`
	BkCloudID       int             `gorm:"uniqueIndex:ip;column:bk_cloud_id;type:int(11);not null;comment:'云区域 ID'"`
	BkBizId         int             `gorm:"column:bk_biz_id;type:int(11);not null;comment:机器当前所属业务" json:"bk_biz_id"`
	DedicatedBiz    int             `gorm:"column:dedicated_biz;type:int(11);default:0;comment:专属业务" json:"dedicated_biz"`
	RsType          string          `gorm:"column:rs_type;type:varchar(64);default:'PUBLIC';comment:资源专用组件类型"`
	BkHostID        int             `gorm:"index:idx_host_id;column:bk_host_id;type:int(11);not null;comment:'bk主机ID'"`
	IP              string          `gorm:"uniqueIndex:ip;column:ip;type:varchar(20);not null" json:"ip"`
	DeviceClass     string          `gorm:"column:device_class;type:varchar(64);not null" json:"device_class"`
	CPUNum          int             `gorm:"column:cpu_num;type:int(11);not null;comment:'cpu核数'" json:"cpu_num"`
	DramCap         int             `gorm:"column:dram_cap;type:int(11);not null;comment:'内存大小'" json:"dram_cap"`
	StorageDevice   json.RawMessage `gorm:"column:storage_device;type:json;comment:'磁盘设备'" json:"storage_device"`
	TotalStorageCap int             `gorm:"column:total_storage_cap;type:int(11);comment:'磁盘总容量'" json:"total_storage_cap"`
	//  操作系统类型 Liunx,Windows
	/*Linux(1) Windows(2) AIX(3) Unix(4) Solaris(5) FreeBSD(7)*/
	OsType string `gorm:"column:os_type;type:varchar(32);not null;comment:'操作系统类型'" json:"os_type"`
	OsBit  string `gorm:"column:os_bit;type:varchar(32);not null;comment:'操作系统位数'" json:"os_bit"`
	//  操作系统版本
	OsVerion string `gorm:"column:os_version;type:varchar(64);not null;comment:'操作系统版本'" json:"os_version"`
	//  操作系统名称
	OsName string `gorm:"column:os_name;type:varchar(64);not null;comment:'操作系统名称'" json:"os_name"`
	//  实际城市ID
	CityID string `gorm:"column:city_id;type:varchar(64);not null" json:"city_id"`
	//  实际城市名称
	City string `gorm:"column:city;type:varchar(128);not null" json:"city"`
	//  园区, 例如光明 cc_device_szone
	SubZone string `gorm:"column:sub_zone;type:varchar(32);not null" json:"sub_zone"`
	//  园区ID cc_device_szone_id
	SubZoneID string `gorm:"column:sub_zone_id;type:varchar(64);not null" json:"sub_zone_id"`
	//  标签
	Label json.RawMessage `gorm:"column:label;type:json" json:"label"`
	//  Unused: 未使用 Used: 已经售卖被使用: Preselected:预占用
	Status string `gorm:"column:status;type:varchar(20);not null" json:"status"`
	// 最后修改时间
	UpdateTime time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"`
	// 创建时间
	CreateTime time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"`
}

// SyncDbRpDailySnapShot TODO
func SyncDbRpDailySnapShot() (err error) {
	ql := `
		insert into tb_rp_daily_snap_shot
		select null,
			date_format(now(), '%Y-%m-%d'),
			bk_cloud_id,
			bk_biz_id,
			dedicated_biz,
			rs_type,
			bk_host_id,
			ip,
			device_class,
			cpu_num,
			dram_cap,
			storage_device,
			total_storage_cap,
			os_type,
			os_bit,
			os_version,
			os_name,
			city_id,
			city,
			sub_zone,
			sub_zone_id,
			label,
			status,
			update_time,
			create_time
		from tb_rp_detail
		where status = 'Unused';
	`
	res, err := DB.SelfSqlDB.Exec(ql)
	if err != nil {
		logger.Error("SyncDbRpDailySnapShot failed: %v", err)
		return err
	}
	count, err := res.RowsAffected()
	if err != nil {
		logger.Error("SyncDbRpDailySnapShot failed: %v", err)
		return err
	}
	logger.Info("SyncDbRpDailySnapShot affected rows: %d", count)
	return err
}
