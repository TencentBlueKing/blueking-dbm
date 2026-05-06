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
	"time"
)

const (
	// SpiderPefWhitelistStatusEnabled 白名单启用
	SpiderPefWhitelistStatusEnabled = 1
	// SpiderPefWhitelistStatusDisabled 白名单禁用
	SpiderPefWhitelistStatusDisabled = 0
)

// TbSpiderPefWhitelist Spider 存储过程/Event/Function/Trigger/View 白名单
// 当语法检查集群类型为 TendbCluster/Spider 时，若请求的 bk_biz_id 在此表且 status=1，则对上述类型相关语句不做禁用/高危拦截
type TbSpiderPefWhitelist struct {
	ID          int       `gorm:"primaryKey;column:id;type:int(11);not null;autoIncrement" json:"id"`
	BkBizID     int       `gorm:"uniqueIndex:uk_bk_biz_id_cluster_type;column:bk_biz_id;type:int(11);not null" json:"bk_biz_id"`
	ClusterType string    `gorm:"uniqueIndex:uk_bk_biz_id_cluster_type;column:cluster_type;type:varchar(32);not null;default:tendbcluster" json:"cluster_type"`
	Remark      string    `gorm:"column:remark;type:varchar(255)" json:"remark"`
	Status      int8      `gorm:"column:status;type:tinyint(1);not null;default:1" json:"status"`
	CreateTime  time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"`
	UpdateTime  time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"`
}

// TableName 表名
func (TbSpiderPefWhitelist) TableName() string {
	return "tb_spider_pef_whitelist"
}

// GetWhitelistBizIds 返回指定集群类型下启用状态的白名单 bk_biz_id 列表，供语法检查逻辑判断是否放行
func GetWhitelistBizIds(clusterType string) ([]int, error) {
	var bizIds []int
	err := DB.Model(&TbSpiderPefWhitelist{}).
		Where("cluster_type = ? AND status = ?", clusterType, SpiderPefWhitelistStatusEnabled).
		Pluck("bk_biz_id", &bizIds).Error
	return bizIds, err
}
