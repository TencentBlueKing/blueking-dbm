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

var ActionTypeMap = map[ActionType]ActionType{
	ActionTypeNotify: ActionTypeNotify,
	ActionTypeSwitch: ActionTypeSwitch,
}

// ActionScopeType  impact scope: cluster, host.
type ActionScopeType string

const (
	ActionScopeTypeCluster    ActionScopeType = "cluster"
	ActionScopeTypeHost       ActionScopeType = "host"
	ActionScopeTypeDbInstance ActionScopeType = "db_instance"
)

func (a ActionScopeType) String() string {
	return string(a)
}

var ActionScopeTypeMap = map[ActionScopeType]ActionScopeType{
	ActionScopeTypeCluster:    ActionScopeTypeCluster,
	ActionScopeTypeHost:       ActionScopeTypeHost,
	ActionScopeTypeDbInstance: ActionScopeTypeDbInstance,
}

// StatusType enabled, disabled, deleted.
type StatusType string

const (
	StatusTypeEnabled  StatusType = "enabled"
	StatusTypeDisabled StatusType = "disabled"
	StatusTypeDeleted  StatusType = "deleted"
)

func (s StatusType) String() string {
	return string(s)
}

var StatusTypeMap = map[StatusType]StatusType{
	StatusTypeEnabled:  StatusTypeEnabled,
	StatusTypeDisabled: StatusTypeDisabled,
}

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.

	// DbSwitchingStrategy Table
	DbSwitchingStrategyTableName                   = "t_db_switching_strategy"
	DbSwitchingStrategyFieldID                     = "id"
	DbSwitchingStrategyFieldName                   = "name"
	DbSwitchingStrategyFieldBkBizID                = "bk_biz_id"
	DbSwitchingStrategyFieldStatus                 = "status"
	DbSwitchingStrategyFieldTriggerEventName       = "trigger_event_name"
	DbSwitchingStrategyFieldTriggerEventNameReason = "trigger_event_name_reason"
	DbSwitchingStrategyFieldTriggerCount           = "trigger_count"
	DbSwitchingStrategyFieldPriority               = "priority"
	DbSwitchingStrategyFieldScope                  = "scope"
	DbSwitchingStrategyFieldAction                 = "action"
	DbSwitchingStrategyFieldDescription            = "description"
	DbSwitchingStrategyFieldCreatedAt              = "created_at"
	DbSwitchingStrategyFieldUpdatedAt              = "updated_at"
	DbSwitchingStrategyFieldDeletedAt              = "deleted_at"
)

// DbSwitchingStrategy database switching strategy
type DbSwitchingStrategy struct {
	// strategy id
	ID int `gorm:"column:id;primaryKey;autoIncrement"`

	// strategy status
	Status StatusType `gorm:"column:status"`

	// strategy name
	Name string `gorm:"column:name;uniqueIndex:idx_name"`

	// 0 is global default strategy
	BkBizID int `gorm:"column:bk_biz_id;primaryKey;uniqueIndex:idx_name"`

	// The event name that triggers the database switch.
	TriggerEventName haprobe.DbEventName `gorm:"column:trigger_event_name;primaryKey;index"`

	// The reason for the event name.
	TriggerEventNameReason haprobe.DbEventNameReason `gorm:"column:trigger_event_name_reason;primaryKey;index"`
	// This strategy will be triggered after the number of events reaches this value.
	TriggerCount int `gorm:"column:trigger_count"`

	// level: 0 > 1> 2 > 3 > ...
	Priority int             `gorm:"column:priority"`
	Scope    ActionScopeType `gorm:"column:scope"`
	Action   ActionType      `gorm:"column:action"`

	// Detailed explanation of db switching strategy.
	Description string    `gorm:"column:description;type:mediumtext;index:idx_description,length:255"`
	CreatedAt   time.Time `gorm:"column:created_at;autoCreateTime;index"`
	UpdatedAt   time.Time `gorm:"column:updated_at;autoUpdateTime;index"`
	DeletedAt   time.Time `gorm:"column:deleted_at;index;default:null"`
}

// TableName returns the name of the switching strategy table.
func (t DbSwitchingStrategy) TableName() string {
	return DbSwitchingStrategyTableName
}
