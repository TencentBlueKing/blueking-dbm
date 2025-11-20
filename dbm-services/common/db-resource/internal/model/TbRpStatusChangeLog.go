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

// 状态变更原因类型
const (
	// ReasonCCModuleNotAllow CC模块不在允许范围内
	ReasonCCModuleNotAllow = "cc_module_not_allow"
	// ReasonHostNotFoundInCC 在CC中查询不到主机信息
	ReasonHostNotFoundInCC = "host_not_found_in_cc"
	// ReasonAgentStatusAbnormal Agent状态异常
	ReasonAgentStatusAbnormal = "agent_status_abnormal"
	// ReasonManualUpdate 手动更新
	ReasonManualUpdate = "manual_update"
	// ReasonSystemError 系统错误
	ReasonSystemError = "system_error"
)

// TbRpStatusChangeLog 资源状态变更日志表
type TbRpStatusChangeLog struct {
	ID            int             `gorm:"primary_key;auto_increment;not_null" json:"id"`
	BkHostID      int             `gorm:"index:idx_host_id;column:bk_host_id;type:int(11);not null;comment:'bk主机ID'" json:"bk_host_id"`
	IP            string          `gorm:"index:idx_ip;column:ip;type:varchar(20);not null;comment:'IP地址'" json:"ip"`
	BkCloudID     int             `gorm:"column:bk_cloud_id;type:int(11);not null;comment:'云区域ID'" json:"bk_cloud_id"`
	OldStatus     string          `gorm:"column:old_status;type:varchar(20);not null;comment:'原状态'" json:"old_status"`
	NewStatus     string          `gorm:"column:new_status;type:varchar(20);not null;comment:'新状态'" json:"new_status"`
	ChangeReason  string          `gorm:"column:change_reason;type:varchar(50);not null;comment:'变更原因类型'" json:"change_reason"`
	ReasonDetail  string          `gorm:"column:reason_detail;type:text;comment:'详细原因描述'" json:"reason_detail"`
	ReasonContext json.RawMessage `gorm:"column:reason_context;type:json;comment:'变更上下文信息'" json:"reason_context"`
	Operator      string          `gorm:"column:operator;type:varchar(64);not null;default:'system';comment:'操作者'" json:"operator"`
	CreateTime    time.Time       `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP();comment:'创建时间'" json:"create_time"`
}

// TableName 表名
func (TbRpStatusChangeLog) TableName() string {
	return TbRpStatusChangeLogName()
}

// TbRpStatusChangeLogName 表名函数
func TbRpStatusChangeLogName() string {
	return "tb_rp_status_change_log"
}

// StatusChangeContext 状态变更上下文
type StatusChangeContext struct {
	// 主机业务信息
	BKBizID          *int    `json:"bk_biz_id,omitempty"`          // 主机当前所属业务ID
	BKBizName        *string `json:"bk_biz_name,omitempty"`        // 主机当前所属业务名称
	DedicatedBiz     *int    `json:"dedicated_biz,omitempty"`      // 专属业务ID
	DedicatedBizName *string `json:"dedicated_biz_name,omitempty"` // 专属业务名称

	// CC拓扑信息
	BKSetID            *int     `json:"bk_set_id,omitempty"`            // 主机所在集合ID
	BKSetName          *string  `json:"bk_set_name,omitempty"`          // 主机所在集合名称
	BKModuleID         *int     `json:"bk_module_id,omitempty"`         // 主机所在模块ID
	BKModuleName       *string  `json:"bk_module_name,omitempty"`       // 主机所在模块名称
	AllowedModules     []int    `json:"allowed_modules,omitempty"`      // 允许的模块ID列表
	AllowedModuleNames []string `json:"allowed_module_names,omitempty"` // 允许的模块名称列表

	// 资源信息
	SubZone     *string `json:"sub_zone,omitempty"`     // 园区
	SubZoneID   *string `json:"sub_zone_id,omitempty"`  // 园区ID
	City        *string `json:"city,omitempty"`         // 城市
	CityID      *string `json:"city_id,omitempty"`      // 城市ID
	DeviceClass *string `json:"device_class,omitempty"` // 设备类型

	// Agent状态信息 (当reason为agent_status_abnormal时使用)
	AgentStatusCode *int `json:"agent_status_code,omitempty"`

	// 错误信息 (当reason为system_error时使用)
	ErrorMessage *string `json:"error_message,omitempty"`

	// 其他通用信息
	RequestID      *string `json:"request_id,omitempty"`
	BatchSize      *int    `json:"batch_size,omitempty"`
	InspectionType *string `json:"inspection_type,omitempty"` // 检查类型
}

// LogStatusChange 记录状态变更日志
func LogStatusChange(bkHostID int, ip string, bkCloudID int, oldStatus, newStatus, reason, reasonDetail string, context *StatusChangeContext, operator string) error {
	var contextJSON json.RawMessage
	if context != nil {
		if data, err := json.Marshal(context); err != nil {
			logger.Warn("marshal status change context failed: %s", err.Error())
		} else {
			contextJSON = data
		}
	}

	log := TbRpStatusChangeLog{
		BkHostID:      bkHostID,
		IP:            ip,
		BkCloudID:     bkCloudID,
		OldStatus:     oldStatus,
		NewStatus:     newStatus,
		ChangeReason:  reason,
		ReasonDetail:  reasonDetail,
		ReasonContext: contextJSON,
		Operator:      operator,
		CreateTime:    time.Now(),
	}

	if err := DB.Self.Table(TbRpStatusChangeLogName()).Create(&log).Error; err != nil {
		logger.Error("create status change log failed: %s", err.Error())
		return err
	}

	logger.Info("status change logged: host=%d ip=%s old=%s new=%s reason=%s",
		bkHostID, ip, oldStatus, newStatus, reason)
	return nil
}

// BatchLogStatusChange 批量记录状态变更日志
func BatchLogStatusChange(logs []TbRpStatusChangeLog) error {
	if len(logs) == 0 {
		return nil
	}

	// 设置创建时间
	now := time.Now()
	for i := range logs {
		logs[i].CreateTime = now
	}

	if err := DB.Self.Table(TbRpStatusChangeLogName()).Create(&logs).Error; err != nil {
		logger.Error("batch create status change logs failed: %s", err.Error())
		return err
	}

	logger.Info("batch status change logged: count=%d", len(logs))
	return nil
}

// GetStatusChangeHistory 获取主机状态变更历史
func GetStatusChangeHistory(bkHostID int, limit int) ([]TbRpStatusChangeLog, error) {
	var logs []TbRpStatusChangeLog
	query := DB.Self.Table(TbRpStatusChangeLogName()).Where("bk_host_id = ?", bkHostID).
		Order("create_time DESC")

	if limit > 0 {
		query = query.Limit(limit)
	}

	if err := query.Find(&logs).Error; err != nil {
		logger.Error("get status change history failed: %s", err.Error())
		return nil, err
	}

	return logs, nil
}

// GetStatusChangesByTimeRange 根据时间范围获取状态变更记录
func GetStatusChangesByTimeRange(startTime, endTime time.Time, changeReason string, limit int) ([]TbRpStatusChangeLog, error) {
	var logs []TbRpStatusChangeLog
	query := DB.Self.Table(TbRpStatusChangeLogName()).
		Where("create_time BETWEEN ? AND ?", startTime, endTime)

	if changeReason != "" {
		query = query.Where("change_reason = ?", changeReason)
	}

	if limit > 0 {
		query = query.Limit(limit)
	}

	query = query.Order("create_time DESC")

	if err := query.Find(&logs).Error; err != nil {
		logger.Error("get status changes by time range failed: %s", err.Error())
		return nil, err
	}

	return logs, nil
}
