/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import (
	"dbm-services/mysql/db-partition/model"
	"errors"
	"fmt"
	"strings"

	glogger "gorm.io/gorm/logger"

	"golang.org/x/exp/slog"
	"gorm.io/gorm"
)

func (m *QueryParititionsInput) GetPartitionsConfigV2() ([]*PartitionConfigWithLog, int64, error) {
	allResults := []*PartitionConfigWithLog{}
	var configTb, logTb string
	// Cnt 用于返回匹配到的行数
	type Cnt struct {
		Count int64 `gorm:"column:cnt"`
	}
	// 判断是mysql集群还是spider集群
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		configTb = MysqlPartitionConfigV2
	case Tendbcluster:
		configTb = SpiderPartitionConfigV2
	default:
		return nil, 0, errors.New("不支持的db类型")
	}
	tx := model.DB.Self.Table(configTb + " as pc").Session(&gorm.Session{}).Where("1=1")
	//where := " 1=1 "
	if m.BkBizId > 0 {
		tx.Where("pc.bk_biz_id=?", m.BkBizId)
	}
	// 使用分区配置的策略id进行查询
	if len(m.Ids) != 0 {
		tx.Where("pc.id in ?", m.Ids)
	}
	if len(m.ImmuteDomains) != 0 {
		tx.Where("pc.immute_domain in ?", m.ImmuteDomains)
	}
	if len(m.DbLikes) != 0 {
		tx.Where("pc.dblike in ?", m.DbLikes)
	}
	if len(m.TbLikes) != 0 {
		tx.Where("pc.tblike in ?", m.TbLikes)
	}
	if m.DomainName != "" {
		tx.Where("pc.immute_domain like ?", fmt.Sprintf("%%%s%%", m.DomainName))
	}

	cnt := Cnt{}
	cntResult := tx.Session(&gorm.Session{}).Select("count(*) as cnt").Find(&cnt)
	if cntResult.Error != nil {
		slog.Error("sql execute error", cntResult.Error)
		return nil, 0, cntResult.Error
	}

	if m.Limit == -1 {
		m.Limit = cnt.Count
	}
	subQuery := model.DB.Self.Table(logTb).Session(&gorm.Session{}).
		Select("config_id,MAX(id) as max_id").Group("config_id")
	//joinSql := fmt.Sprintf("left join s%")
	result := tx.Session(&gorm.Session{Logger: glogger.Default.LogMode(glogger.Info)}).
		Select("pc.*,pcl.create_time as execute_time,pcl.check_info as check_info,pcl.status as status ").
		Joins("left join (?) as pclm on pc.id=pclm.config_id", subQuery).
		Joins("left join " + logTb + " as pcl on pcl.config_id=pclm.config_id and pcl.id=pclm.max_id").
		Order("pcl.status,pc.id desc").Limit(int(m.Limit)).Offset(m.Offset).Find(&allResults)

	if result.Error != nil {
		slog.Error("sql execute error", result.Error)
		return nil, 0, result.Error
	}

	return allResults, cnt.Count, nil
}
