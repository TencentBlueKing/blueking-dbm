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
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	glogger "gorm.io/gorm/logger"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"

	"golang.org/x/exp/slog"
)

// GetPartitionsConfig TODO
func (m *QueryParititionsInput) GetPartitionsConfig() ([]*PartitionConfigWithLog, int64, error) {
	allResults := []*PartitionConfigWithLog{}
	var configTb, logTb, orderBy string
	var desc bool
	// Cnt 用于返回匹配到的行数
	type Cnt struct {
		Count int64 `gorm:"column:cnt"`
	}
	// 判断是mysql集群还是spider集群
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		configTb = MysqlPartitionConfig
		logTb = MysqlPartitionCronLogTable
	case Tendbcluster:
		configTb = SpiderPartitionConfig
		logTb = SpiderPartitionCronLogTable
	default:
		return nil, 0, errors.New("不支持的db类型")
	}
	tx := model.DB.Self.Table(configTb).Session(&gorm.Session{}).Where("1=1")
	//where := " 1=1 "
	if m.BkBizId > 0 {
		tx.Where("bk_biz_id=?", m.BkBizId)
	}
	if len(m.Ids) != 0 {
		tx.Where("id in ?", m.Ids)
	}
	if len(m.ImmuteDomains) != 0 {
		tx.Where("immute_domain in ?", m.ImmuteDomains)
	}
	if len(m.DbLikes) != 0 {
		tx.Where("dblike in ?", m.DbLikes)
	}
	if len(m.TbLikes) != 0 {
		tx.Where("tblike in ?", m.TbLikes)
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
	if m.OrderBy == "" {
		orderBy = "id"
		desc = true
	} else {
		orderBy = m.OrderBy
		switch m.AscDesc {
		case "desc":
			desc = true
		default:
			desc = false
		}
	}

	//order := fmt.Sprintf("%s %s", orderBy, ascDesc)
	// 先在partition_config中查出分区配置的相关信息
	//Logger: glogger.Default.LogMode(glogger.Info)
	order := clause.OrderByColumn{
		Column: clause.Column{
			Name: orderBy,
		},
		Desc: desc,
	}
	result := tx.Session(&gorm.Session{Logger: glogger.Default.LogMode(glogger.Info)}).
		Order(order).Limit(int(m.Limit)).Offset(m.Offset).Find(&allResults)
	if result.Error != nil {
		slog.Error("sql execute error", result.Error)
		return nil, 0, result.Error
	}

	logTx := model.DB.Self.Table(logTb)
	for _, configResult := range allResults {
		logInfo := struct {
			ExecuteTime string `gorm:"execute_time"`
			Status      string `gorm:"status"`
			CheckInfo   string `gorm:"check_info"`
		}{}
		logResult := logTx.Session(&gorm.Session{}).
			Select("create_time as execute_time,check_info as check_info,status as status").
			Where("config_id = ?", configResult.ID).
			Where("create_time > DATE_SUB(now(),interval 100 day)").
			Order("id desc").Limit(1).Find(&logInfo)
		if logResult.Error != nil {
			slog.Error("sql execute err.", logResult.Error)
			return nil, 0, logResult.Error
		}
		configResult.ExecuteTime = logInfo.ExecuteTime
		configResult.Status = logInfo.Status
		configResult.CheckInfo = logInfo.CheckInfo
	}

	return allResults, cnt.Count, nil
}

// GetPartitionLog TODO
func (m *QueryLogInput) GetPartitionLog() ([]*PartitionLog, int64, error) {
	allResults := make([]*PartitionLog, 0)
	var logTb string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		logTb = MysqlPartitionCronLogTable
	case Tendbcluster:
		logTb = SpiderPartitionCronLogTable
	default:
		return nil, 0, errors.New("不支持的db类型")
	}

	tx := model.DB.Self.Session(&gorm.Session{}).Table(logTb).Where("config_id=?", m.ConfigId)
	if m.StartTime != "" && m.EndTime != "" {
		tx.Where("create_time>? and create_time<?", m.StartTime, m.EndTime)
	} else {
		// 查询近100天的日志
		tx.Where("create_time> DATE_SUB(now(),interval 100 day)")
	}

	// Cnt 用于返回匹配到的行数
	type Cnt struct {
		Count int64 `gorm:"column:cnt"`
	}
	cnt := Cnt{}
	// 使用session函数，开启新的会话查询
	cntResult := tx.Session(&gorm.Session{}).Select("count(*) as cnt").Find(&cnt)
	if cntResult.Error != nil {
		slog.Error("cnt sql execute error", cntResult.Error)
		return nil, 0, cntResult.Error
	}

	order := clause.OrderByColumn{
		Column: clause.Column{
			Name: "create_time",
		},
		Desc: true,
	}

	// 使用session函数，开启新的会话查询，避免和上面的查询重复（条件，返回字段）
	result := tx.Session(&gorm.Session{}).
		Select("id,create_time as execute_time,check_info,status").Order(order).
		Limit(m.Limit).Offset(m.Offset).Find(&allResults)
	if result.Error != nil {
		slog.Error("sql execute error", result.Error)
		return nil, 0, result.Error
	}
	return allResults, cnt.Count, nil
}

// DeletePartitionsConfig TODO
func (m *DeletePartitionConfigByIds) DeletePartitionsConfig() error {
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if len(m.Ids) == 0 {
		return errno.ConfigIdIsEmpty
	}
	var tbName string
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("不支持的db类型")
	}

	// 操作行为记录到日志
	for _, configID := range m.Ids {
		CreateManageLog(tbName, logTbName, configID, "Delete", m.Operator)
	}

	result := model.DB.Self.Table(tbName).Where("bk_biz_id=?", m.BkBizId).Delete(&PartitionConfig{}, m.Ids)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.PartitionConfigNotExisted
	}

	return nil
}

// DeletePartitionsConfigByCluster TODO
func (m *DeletePartitionConfigByClusterIds) DeletePartitionsConfigByCluster() (err error, info string) {
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty, ""
	}
	if len(m.ClusterIds) == 0 {
		return errno.ConfigIdIsEmpty, ""
	}
	var tbName string
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("不支持的db类型"), ""
	}

	// 以集群维度记录日志
	CreateManageLogByCluster(m.BkBizId, m.ClusterIds, tbName, logTbName,
		"Delete by cluster", m.Operator)

	result := model.DB.Self.Session(&gorm.Session{}).Table(tbName).
		Where("cluster_id in ? and bk_biz_id=?", m.ClusterIds, m.BkBizId).
		Delete(&PartitionConfig{})
	if result.Error != nil {
		return result.Error, ""
	}
	if result.RowsAffected == 0 {
		info = "该集群无分区配置，无需清理分区策略。"
		return nil, info
	}
	return nil, "分区配置信息删除成功！"
}

// CreatePartitionsConfig TODO
func (m *CreatePartitionsInput) CreatePartitionsConfig() (error, []int) {
	var tbName string
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("不支持的db类型"), []int{}
	}

	if len(m.PartitionColumn) == 0 {
		return errors.New("请输入分区字段！"), []int{}
	}

	if len(m.DbLikes) == 0 || len(m.TbLikes) == 0 {
		return errors.New("库表名不能为空！"), []int{}
	}

	if m.PartitionTimeInterval < 1 {
		return errors.New("分区间隔不能小于1"), []int{}
	}

	if m.ExpireTime < m.PartitionTimeInterval {
		return errors.New("过期时间必须不小于分区间隔"), []int{}
	}
	if m.ExpireTime%m.PartitionTimeInterval != 0 {
		return errors.New("过期时间必须是分区间隔的整数倍"), []int{}
	}
	reservedPartition := m.ExpireTime / m.PartitionTimeInterval
	partitionType := 0
	// 普通分区类型0 5 101
	switch m.PartitionColumnType {
	case "datetime", "date":
		if strings.EqualFold(m.RemoteHashAlgorithm, "range") {
			partitionType = 4
		} else {
			partitionType = 0
		}
	case "timestamp":
		partitionType = 5
	case "int", "bigint":
		if strings.EqualFold(m.RemoteHashAlgorithm, "list") {
			partitionType = 3
		} else {
			partitionType = 101
		}
	default:
		return errors.New("请选择分区字段类型：datetime、date、timestamp、int、bigint"), []int{}
	}
	var errs []string
	warnings1, err := m.compareWithSameArray()
	if err != nil {
		return err, []int{}
	}
	warnings2, err := m.CompareWithExistDB(tbName)
	if err != nil {
		return err, []int{}
	}

	warnings := append(warnings1, warnings2...)
	if len(warnings) > 0 {
		return errors.New(strings.Join(warnings, "\n")), []int{}
	}
	var configIDs []int
	for _, dblike := range m.DbLikes {
		for _, tblike := range m.TbLikes {
			partitionConfig := PartitionConfig{
				BkBizId:               m.BkBizId,
				DbAppAbbr:             m.DbAppAbbr,
				BkBizName:             m.BkBizName,
				ImmuteDomain:          m.ImmuteDomain,
				Port:                  m.Port,
				BkCloudId:             m.BkCloudId,
				ClusterId:             m.ClusterId,
				DbLike:                dblike,
				TbLike:                tblike,
				PartitionColumn:       m.PartitionColumn,
				PartitionColumnType:   m.PartitionColumnType,
				ReservedPartition:     reservedPartition,
				ExtraPartition:        extraTime,
				PartitionTimeInterval: m.PartitionTimeInterval,
				PartitionType:         partitionType,
				ExpireTime:            m.ExpireTime,
				TimeZone:              m.TimeZone,
				Creator:               m.Creator,
				Updator:               m.Updator,
				Phase:                 online,
				CreateTime:            time.Now(),
				UpdateTime:            time.Now(),
			}
			// gorm插入数据后，会返回插入数据的主键、错误、行数
			result := model.DB.Self.Table(tbName).Create(&partitionConfig)
			if result.Error != nil {
				errs = append(errs, result.Error.Error())
			} else {
				configIDs = append(configIDs, partitionConfig.ID)
				CreateManageLog(tbName, logTbName, partitionConfig.ID, "Insert", m.Creator)
			}
		}
	}
	if len(errs) > 0 {
		return fmt.Errorf("errors: %s", strings.Join(errs, "\n")), []int{}
	}
	return nil, configIDs
}

// UpdatePartitionsConfig TODO
func (m *CreatePartitionsInput) UpdatePartitionsConfig() error {
	var tbName string
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("错误的db类型")
	}

	if len(m.PartitionColumn) == 0 {
		return errors.New("请输入分区字段！")
	}

	if len(m.DbLikes) == 0 || len(m.TbLikes) == 0 {
		return errors.New("库表名不能为空！")
	}

	if m.PartitionTimeInterval < 1 {
		return errors.New("分区间隔不能小于1")
	}

	if m.ExpireTime < m.PartitionTimeInterval {
		return errors.New("过期时间必须不小于分区间隔")
	}
	if m.ExpireTime%m.PartitionTimeInterval != 0 {
		return errors.New("过期时间必须是分区间隔的整数倍")
	}

	reservedPartition := m.ExpireTime / m.PartitionTimeInterval
	partitionType := 0

	switch m.PartitionColumnType {
	case "datetime", "date":
		partitionType = 0
	case "timestamp":
		partitionType = 5
	case "int", "bigint":
		partitionType = 101
	default:
		return errors.New("请选择分区字段类型：datetime、date、timestamp、int、bigint")
	}
	var errs []string
	for _, dblike := range m.DbLikes {
		for _, tblike := range m.TbLikes {
			var partitionConfig PartitionConfig
			query := struct {
				BkBizId      int64  `gorm:"column:bk_biz_id"`
				ImmuteDomain string `gorm:"column:immute_domain"`
				DbLike       string `gorm:"column:dblike"`
				TbLike       string `gorm:"column:tblike"`
			}{m.BkBizId, m.ImmuteDomain, dblike, tblike}
			// 更新分区会先查到现有配置做字段对比
			nowConfigResult := model.DB.Self.Table(tbName).Where(&query).First(&partitionConfig)
			if nowConfigResult.Error != nil {
				errResult := fmt.Sprintf("query:%+v err:%s", query, nowConfigResult.Error)
				slog.Error(errResult)
				errs = append(errs, errResult)
				continue
			} else {
				CreateManageLog(tbName, logTbName, partitionConfig.ID, "Update", m.Updator)
			}
			// 对于不在页面的几种分区类型(1,3,4)，不允许修改字段值、字段类型和分区类型，只能改保留时间、分区间隔
			if ContainsMap(Slice2Map([]int{1, 3, 4}), partitionConfig.PartitionType) {
				if m.PartitionColumn != partitionConfig.PartitionColumn || m.PartitionColumnType !=
					partitionConfig.PartitionColumnType {
					return errors.New("非标准分区类型，不可修改分区字段和分区字段类型！")
				}
				// 分区类型不变，按照原配置
				partitionType = partitionConfig.PartitionType
			}
			// 分区配置更新字段兼容普通分区与特殊分区
			update_column_map := map[string]interface{}{
				"partition_column":        m.PartitionColumn,
				"partition_column_type":   m.PartitionColumnType,
				"reserved_partition":      reservedPartition,
				"extra_partition":         extraTime,
				"partition_time_interval": m.PartitionTimeInterval,
				"partition_type":          partitionType,
				"expire_time":             m.ExpireTime,
				"updator":                 m.Updator,
				"update_time":             time.Now(),
			}
			result := model.DB.Self.Table(tbName).
				Where(
					"bk_biz_id=? and immute_domain=? and dblike=? and tblike=?",
					m.BkBizId, m.ImmuteDomain, dblike, tblike).
				Updates(update_column_map)
			if result.Error != nil {
				errs = append(errs, result.Error.Error())
			}
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
	}

	return nil
}

// DisablePartitionConfig TODO
func (m *DisablePartitionInput) DisablePartitionConfig() error {
	if len(m.Ids) == 0 {
		return errno.ConfigIdIsEmpty
	}
	var tbName string
	// 判断是mysql集群还是spider集群
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("不支持的db类型")
	}

	db := model.DB.Self.Table(tbName)
	result := db.Where("id in ?", m.Ids).Update("phase", offline)
	if result.Error != nil {
		return result.Error
	}

	for _, id := range m.Ids {
		CreateManageLog(tbName, logTbName, id, "Disable", m.Operator)
	}
	return nil
}

// DisablePartitionConfigByCluster TODO
func (m *DisablePartitionInput) DisablePartitionConfigByCluster() error {
	if len(m.ClusterIds) == 0 {
		return errno.ConfigIdIsEmpty
	}
	var tbName string
	// 判断是mysql集群还是spider集群
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("不支持的db类型")
	}

	db := model.DB.Self.Table(tbName)
	result := db.
		Where("cluster_id in ?", m.ClusterIds).Update("phase", offlinewithclu)
	if result.Error != nil {
		return result.Error
	}
	for _, id := range m.Ids {
		CreateManageLog(tbName, logTbName, id, "DisableByCluster", m.Operator)
	}
	return nil
}

// EnablePartitionConfig TODO
func (m *EnablePartitionInput) EnablePartitionConfig() error {
	if len(m.Ids) == 0 {
		return errno.ConfigIdIsEmpty
	}
	var tbName string
	// 判断是mysql集群还是spider集群
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("不支持的db类型")
	}

	db := model.DB.Self.Table(tbName)
	result := db.
		Where("id in ?", m.Ids).Update("phase", online)
	if result.Error != nil {
		return result.Error
	}
	for _, id := range m.Ids {
		CreateManageLog(tbName, logTbName, id, "Enable", m.Operator)
	}
	return nil
}

// EnablePartitionByCluster TODO
func (m *EnablePartitionInput) EnablePartitionByCluster() error {
	if len(m.ClusterIds) == 0 {
		return errno.ConfigIdIsEmpty
	}
	var tbName string
	// 判断是mysql集群还是spider集群
	var logTbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
		logTbName = MysqlManageLogsTable
	case Tendbcluster:
		tbName = SpiderPartitionConfig
		logTbName = SpiderManageLogsTable
	default:
		return errors.New("不支持的db类型")
	}
	db := model.DB.Self.Table(tbName)
	result := db.Where("cluster_id in ?", m.ClusterIds).Update("phase", online)
	if result.Error != nil {
		return result.Error
	}
	for _, id := range m.Ids {
		CreateManageLog(tbName, logTbName, id, "EnableByCluster", m.Operator)
	}
	return nil
}

func (m *CreatePartitionsInput) compareWithSameArray() (warnings []string, err error) {
	l := len(m.DbLikes)
	for i := 0; i < l; i++ {
		dbi := m.DbLikes[i]
		for j := i + 1; j < l; j++ {
			dbj := m.DbLikes[j]
			dbiReg, err := regexp.Compile(strings.Replace(dbi+"$", "%", ".*", -1))
			if err != nil {
				return warnings, err
			}
			dbjReg, err := regexp.Compile(strings.Replace(dbj+"$", "%", ".*", -1))
			if err != nil {
				return warnings, err
			}
			if dbiReg.MatchString(dbj) || dbjReg.MatchString(dbi) {
				waring := fmt.Sprintf("本次提交中，规则%s与规则%s存在冲突，请修改后再次提交！", dbi, dbj)
				warnings = append(warnings, waring)
			}
		}

	}
	return warnings, nil
}

// CompareWithExistDB 检查重复库表
func (m *CreatePartitionsInput) CompareWithExistDB(tbName string) (warnings []string, err error) {
	l := len(m.DbLikes)
	for i := 0; i < l; i++ {
		db := m.DbLikes[i]
		existRules, err := m.checkExistRules(tbName)
		if err != nil {
			return warnings, err
		}
		for _, existRule := range existRules {
			dbReg, err := regexp.Compile(strings.Replace(db+"$", "%", ".*", -1))
			if err != nil {
				return warnings, err
			}
			dbExistReg, err := regexp.Compile(strings.Replace(existRule.DbLike+"$", "%", ".*", -1))
			if err != nil {
				return warnings, err
			}
			if dbReg.MatchString(existRule.DbLike) || dbExistReg.MatchString(db) {
				for _, tb := range m.TbLikes {
					if tb == existRule.TbLike {
						waring := fmt.Sprintf("本次提交中，规则%s.%s与已有规则%s.%s存在冲突，请修改后再次提交！", db, tb, existRule.DbLike, existRule.TbLike)
						warnings = append(warnings, waring)
					}
				}
			}
		}
	}
	return warnings, nil
}

func (m *CreatePartitionsInput) checkExistRules(tbName string) (existRules []ExistRule, err error) {
	condition := fmt.Sprintf("bk_biz_id=%d and immute_domain='%s' and bk_cloud_id=%d", m.BkBizId, m.ImmuteDomain,
		m.BkCloudId)
	err = model.DB.Self.Table(tbName).Select("dblike", "tblike").Where(condition).Find(&existRules).Error
	if err != nil {
		return existRules, err
	}
	return existRules, nil
}

// CreateManageLog 记录操作日志，日志不对外
func CreateManageLog(dbName string, logTbName string, id int, operate string, operator string) {
	/*
		1、根据config_id去配置表中查到相关配置信息 此处id指的是config_id
		2、写入日志表
	*/
	var partitionConfig PartitionConfig
	partitionConfig.ID = id
	// 注意
	model.DB.Self.Session(&gorm.Session{}).Table(dbName).First(&partitionConfig)
	jstring, jerr := json.Marshal(partitionConfig)
	if jerr != nil {
		slog.Error("create manage log err", jerr)
	}
	manageLogs := ManageLogs{
		ConfigId:    id,
		BkBizId:     partitionConfig.BkBizId,
		Operate:     operate,
		Operator:    operator,
		Para:        string(jstring),
		ExecuteTime: time.Now(),
	}
	logResult := model.DB.Self.Table(logTbName).Create(&manageLogs)
	if logResult.Error != nil {
		slog.Error("create manage log err", logResult.Error)
	}
}

// CreateManageLogByCluster 以集群维度记录日志
func CreateManageLogByCluster(bkBizId int64, clusterIds []int, tbName string, logTbName string,
	operate string, operator string) {
	/*
		需要在删除操作之前记录日志，不然查不到元数据信息
		不是关键日志，故不在意记录后，后续操作做是否执行
	*/
	for _, clusterId := range clusterIds {
		// var partitionConfigIds []struct{ID int}
		// 这里直接声明加初始化，避免为nil 不过实际也可以只声明，后面赋值使用，个人习惯
		partitionConfigIds := []struct{ ID int }{}
		query := PartitionConfig{
			BkBizId:   bkBizId,
			ClusterId: clusterId,
		}
		selectResult := model.DB.Self.Table(tbName).Where(&query).Find(&partitionConfigIds)
		if selectResult.Error != nil {
			slog.Error("create manage log err.", selectResult.Error)
		} else {
			if selectResult.RowsAffected > 0 {
				for _, id := range partitionConfigIds {
					CreateManageLog(tbName, logTbName, id.ID,
						operate, operator)
				}
			}
		}
	}
}

// Slice2Map TODO
func Slice2Map(s []int) map[int]struct{} {
	m := make(map[int]struct{})
	for _, v := range s {
		m[v] = struct{}{}
	}
	return m
}

// ContainsMap TODO
func ContainsMap(m map[int]struct{}, i int) bool {
	_, ok := m[i]
	return ok
}
