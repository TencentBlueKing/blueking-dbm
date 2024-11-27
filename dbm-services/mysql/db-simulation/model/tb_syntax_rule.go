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

	"gorm.io/gorm/clause"

	"dbm-services/common/go-pubpkg/logger"
)

const (
	// StringItem string
	StringItem = "string"
	// ArryItem arry
	ArryItem = "arry"
	// IntItem int
	IntItem = "int"
	// BoolItem bool
	BoolItem = "bool"
)

// TbSyntaxRule [...]
type TbSyntaxRule struct {
	ID int `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	// 数据库类型
	DbType string `gorm:"uniqueIndex:group;column:db_type;type:varchar(32);not null" json:"db_type"`
	// 规则组名称
	GroupName string `gorm:"uniqueIndex:group;column:group_name;type:varchar(64);not null" json:"group_name"`
	// 子规则项，一个规则可能包括过个子规则
	RuleName string          `gorm:"uniqueIndex:group;column:rule_name;type:varchar(64);not null" json:"rule_name"`
	Item     json.RawMessage `gorm:"column:item;type:varchar(1024);not null" json:"item"`
	ItemType string          `gorm:"column:item_type;type:varchar(128);not null" json:"item_type"`
	// 规则表达式
	Expr string `gorm:"column:expr;type:varchar(128);not null" json:"expr"`
	// 规则提示信息
	Desc string `gorm:"column:desc;type:varchar(512);not null" json:"desc"`
	// 0:作为普通检查项,1:禁用命中该规则的行为
	WarnLevel int16 `gorm:"column:warn_level;type:smallint(2);not null" json:"warn_level"`
	// 1：启用，0:禁用
	Status bool `gorm:"column:status;type:tinyint(1);not null" json:"status"`
}

// GetTableName get sql table name.获取数据库名字
func (obj *TbSyntaxRule) GetTableName() string {
	return "tb_syntax_rules"
}

// CreateRule create rule
func CreateRule(m *TbSyntaxRule) (err error) {
	return DB.Clauses(clause.OnConflict{
		DoNothing: true,
	}).Create(m).Error
}

// GetAllRule get all rules
func GetAllRule() (rs []TbSyntaxRule, err error) {
	err = DB.Find(&rs).Error
	return
}

// GetRuleByName get rules group by group name
func GetRuleByName(group, dbtype, rulename string) (rs TbSyntaxRule, err error) {
	err = DB.Where("group_name = ? and db_type =  ? and rule_name = ? and status = 1", group, dbtype, rulename).
		First(&rs).Error
	return
}

// GetItemVal get item val
func GetItemVal(rule TbSyntaxRule) (val interface{}, err error) {
	switch rule.ItemType {
	case ArryItem:
		var d []string
		if err = json.Unmarshal(rule.Item, &d); err != nil {
			logger.Error("umarshal failed %s", err.Error())
			return nil, err
		}
		val = d
	case StringItem:
		var d string
		if err = json.Unmarshal(rule.Item, &d); err != nil {
			logger.Error("umarshal failed %s", err.Error())
			return nil, err
		}
		val = d
	case IntItem:
		var d int
		if err = json.Unmarshal(rule.Item, &d); err != nil {
			logger.Error("umarshal failed %s", err.Error())
			return nil, err
		}
		val = d
	case BoolItem:
		var d bool
		if err = json.Unmarshal(rule.Item, &d); err != nil {
			logger.Error("umarshal failed %s", err.Error())
			return nil, err
		}
		val = d
	default:
		return nil, fmt.Errorf("unrecognizable type:%s", rule.ItemType)
	}
	return val, err
}
