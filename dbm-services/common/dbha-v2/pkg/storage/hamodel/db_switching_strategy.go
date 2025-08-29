/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hamodel

import (
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// ActionType notify, switch.
type ActionType string

const (
	ActionTypeNotify ActionType = "notify"
	ActionTypeSwitch ActionType = "switch"
)

func (a ActionType) String() string {
	return string(a)
}

// ActionScopeType  impact scope: cluster, host.
type ActionScopeType string

const (
	ActionScopeTypeCluster ActionScopeType = "cluster"
	ActionScopeTypeHost    ActionScopeType = "host"
)

func (a ActionScopeType) String() string {
	return string(a)
}

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
	// DbSwitchingLog Table
	DbSwitchingLogTableName              = "t_db_switching_log"
	DbSwitchingLogFieldID                = "id"
	DbSwitchingLogFieldBkBizID           = "bk_biz_id"
	DbSwitchingLogFieldBkCloudID         = "bk_cloud_id"
	DbSwitchingLogFieldDbIP              = "db_ip"
	DbSwitchingLogFieldDbPort            = "db_port"
	DbSwitchingLogFieldDbTypeName        = "db_type_name"
	DbSwitchingLogFieldDbEventName       = "db_event_name"
	DbSwitchingLogFieldDbEventNameReason = "db_event_name_reason"
	DbSwitchingLogFieldLevel             = "level"
	DbSwitchingLogFieldContent           = "content"
	DbSwitchingLogFieldCreatedAt         = "created_at"

	// DbSwitchingStrategy Table
	DbSwitchingStrategyTableName                   = "t_db_switching_strategy"
	DbSwitchingStrategyFieldName                   = "name"
	DbSwitchingStrategyFieldBkBizID                = "bk_biz_id"
	DbSwitchingStrategyFieldTriggerEventName       = "trigger_event_name"
	DbSwitchingStrategyFieldTriggerEventNameReason = "trigger_event_name_reason"
	DbSwitchingStrategyFieldPriority               = "priority"
	DbSwitchingStrategyFieldScope                  = "scope"
	DbSwitchingStrategyFieldAction                 = "action"
	DbSwitchingStrategyFieldDescription            = "description"
	DbSwitchingStrategyFieldCreatedAt              = "created_at"
	DbSwitchingStrategyFieldUpdatedAt              = "updated_at"
	DbSwitchingStrategyFieldDeletedAt              = "deleted_at"
)

// DbSwitchingLog defines the log of database switching.
type DbSwitchingLog struct {
	ID                uint      `gorm:"column:id;primaryKey;autoIncrement"`
	BkBizID           int       `gorm:"column:bk_biz_id"`
	BkCloudID         int       `gorm:"column:bk_cloud_id"`
	DbIP              string    `gorm:"column:db_ip"`
	DbPort            int       `gorm:"column:db_port"`
	DbTypeName        string    `gorm:"column:db_type_name"`
	DbEventName       string    `gorm:"column:db_event_name"`
	DbEventNameReason string    `gorm:"column:db_event_name_reason"`
	Level             string    `gorm:"column:level"`
	Content           string    `gorm:"column:content;mediumtext"`
	CreatedAt         time.Time `gorm:"column:created_at;autoCreateTime"`
}

func (t DbSwitchingLog) TableName() string {
	return DbSwitchingLogTableName
}

// DbSwitchingStrategy database switching strategy
type DbSwitchingStrategy struct {
	// strategy name
	Name string `gorm:"column:name"`

	// 0 is global default strategy
	BkBizID int `gorm:"column:bk_biz_id;primaryKey"`

	// The event name that triggers the database switch.
	TriggerEventName haprobe.DbEventName `gorm:"column:trigger_event_name;primaryKey"`

	// The reason for the event name.
	TriggerEventNameReason haprobe.DbEventNameReason `gorm:"trigger_event_name_reason;primaryKey"`

	// level: 0 > 1> 2 > 3 > ...
	Priority int             `gorm:"column:priority"`
	Scope    ActionScopeType `gorm:"column:scope"`
	Action   ActionType      `gorm:"column:action"`

	// Detailed explanation of db switching strategy.
	Description string    `gorm:"column:description;mediumtext"`
	CreatedAt   time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt   time.Time `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt   time.Time `gorm:"column:deleted_at"`
}

func (t DbSwitchingStrategy) TableName() string {
	return "t_db_switching_strategy"
}
