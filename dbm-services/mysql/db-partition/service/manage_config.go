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
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"

	"golang.org/x/exp/slog"
)

// GetPartitionsConfig TODO
func (m *QueryParititionsInput) GetPartitionsConfig() ([]*PartitionConfigWithLog, int64, error) {
	allResults := make([]*PartitionConfigWithLog, 0)
	var configTb, logTb string
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
	where := " 1=1 "
	if m.BkBizId > 0 {
		where = fmt.Sprintf("%s and config.bk_biz_id=%d", where, m.BkBizId)
	}
	if len(m.Ids) != 0 {
		var temp = make([]string, len(m.Ids))
		for k, id := range m.Ids {
			temp[k] = strconv.FormatInt(id, 10)
		}
		ids := " and config.id in (" + strings.Join(temp, ",") + ") "
		where = where + ids
	}
	if len(m.ImmuteDomains) != 0 {
		dns := " and config.immute_domain in ('" + strings.Join(m.ImmuteDomains, "','") + "') "
		where = where + dns
	}
	if len(m.DbLikes) != 0 {
		dblike := " and config.dblike in ('" + strings.Join(m.DbLikes, "','") + "') "
		where = where + dblike
	}
	if len(m.TbLikes) != 0 {
		tblike := " and config.tblike in ('" + strings.Join(m.TbLikes, "','") + "') "
		where = where + tblike
	}
	cnt := Cnt{}
	vsql := fmt.Sprintf("select count(*) as cnt from `%s` as config where %s", configTb, where)
	err := model.DB.Self.Raw(vsql).Scan(&cnt).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}

	limitCondition := fmt.Sprintf("limit %d offset %d", m.Limit, m.Offset)
	condition := fmt.Sprintf("%s order by config.id desc %s", where, limitCondition)
	/*
		一、ticket_id是非0的整数，则表示，最近一次任务生成了分区单据，单据执行状态就是最近这次任务的状态，需要从dbm ticket_ticket表中获取状态。
		二、ticket_id是0，表示最近一次任务没有生成分区单据，status状态表示最近这次任务的状态，FAILED或者SUCCEEDED。
				（1）FAILED: 可能因为dry_run获取分区语句失败等，check_info显示错误信息；
			     （2）SUCCEEDED: 表示dry_run成功，并且没有需要实施的分区操作，无需创建单据。
		三、ticket_id是NULL，status是NULL，分区规则还没有执行过
	*/
	vsql = fmt.Sprintf("SELECT config.*, logs.create_time as execute_time, "+
		"logs.ticket_id as ticket_id, logs.check_info as check_info, "+
		"logs.status as status FROM "+
		"%s AS config LEFT JOIN "+
		"(SELECT log.* FROM %s AS log, "+
		"(SELECT inner_config.id AS config_id, MAX(inner_log.id) AS log_id FROM "+
		"%s AS inner_config LEFT JOIN "+
		"%s AS inner_log ON inner_config.id = inner_log.config_id where "+
		"inner_log.create_time > DATE_SUB(now(),interval 100 day) GROUP BY inner_config.id) "+
		"AS latest_log WHERE log.id = latest_log.log_id) AS logs ON config.id = logs.config_id where %s ",
		configTb, logTb, configTb, logTb, condition)
	err = model.DB.Self.Raw(vsql).Scan(&allResults).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
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
	// Cnt 用于返回匹配到的行数
	type Cnt struct {
		Count int64 `gorm:"column:cnt"`
	}
	where := fmt.Sprintf(` config_id=%d and create_time> DATE_SUB(now(),interval 100 day) `, m.ConfigId)
	if m.StartTime != "" && m.EndTime != "" {
		where = fmt.Sprintf(` config_id=%d and create_time>'%s' and create_time<'%s' `, m.ConfigId, m.StartTime, m.EndTime)
	}
	limitCondition := fmt.Sprintf(" limit %d offset %d ", m.Limit, m.Offset)
	cnt := Cnt{}
	vsql := fmt.Sprintf("select count(*) as cnt from `%s` where %s", logTb, where)
	err := model.DB.Self.Raw(vsql).Scan(&cnt).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}

	vsql = fmt.Sprintf("select id, ticket_id, create_time as execute_time, "+
		"check_info, status from %s where %s order by execute_time desc %s",
		logTb, where, limitCondition)
	err = model.DB.Self.Raw(vsql).Scan(&allResults).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
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

	for _, configID := range m.Ids {
		CreateManageLog(tbName, logTbName, configID, "Delete", m.Operator)
	}

	var list []string
	for _, item := range m.Ids {
		list = append(list, strconv.FormatInt(int64(item), 10))
	}
	sql := fmt.Sprintf("delete from `%s` where id in  (%s) and bk_biz_id = %d", tbName, strings.Join(list, ","),
		m.BkBizId)
	result := model.DB.Self.Exec(sql)
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

	for _, clusterId := range m.ClusterIds {
		var partitionConfig PartitionConfig
		query := PartitionConfig{
			BkBizId:   m.BkBizId,
			ClusterId: clusterId,
		}
		result2 := model.DB.Self.Table(tbName).Where(&query).First(&partitionConfig)
		if result2.Error != nil {
			slog.Error("create manage log err", result2.Error)
		} else {
			CreateManageLog(tbName, logTbName, partitionConfig.ID,
				"Delete by cluster", "uninstall_cluster")
		}
	}

	var list []string
	for _, item := range m.ClusterIds {
		list = append(list, strconv.FormatInt(int64(item), 10))
	}
	sql := fmt.Sprintf("delete from `%s` where cluster_id in  (%s) and bk_biz_id = %d", tbName, strings.Join(list, ","),
		m.BkBizId)
	result := model.DB.Self.Exec(sql)
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
	case "datetime":
		if strings.EqualFold(m.RemoteHashAlgorithm, "range") {
			partitionType = 4
		} else {
			partitionType = 0
		}
	case "timestamp":
		partitionType = 5
	case "int":
		if strings.EqualFold(m.RemoteHashAlgorithm, "list") {
			partitionType = 3
		} else {
			partitionType = 101
		}
	default:
		return errors.New("请选择分区字段类型：datetime、timestamp或int"), []int{}
	}
	var errs []string
	warnings1, err := m.compareWithSameArray()
	if err != nil {
		return err, []int{}
	}
	warnings2, err := m.compareWithExistDB(tbName)
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
	case "datetime":
		partitionType = 0
	case "timestamp":
		partitionType = 5
	case "int":
		partitionType = 101
	default:
		return errors.New("请选择分区字段类型：datetime、timestamp或int")
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
	var list []string
	for _, item := range m.Ids {
		list = append(list, strconv.FormatInt(int64(item), 10))

	}
	db := model.DB.Self.Table(tbName)
	result := db.
		Where(fmt.Sprintf("id in (%s)", strings.Join(list, ","))).
		Update("phase", offline)
	if result.Error != nil {
		return result.Error
	}
	for _, id := range m.Ids {
		CreateManageLog(tbName, logTbName, id, "Disable", m.Operator)
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
	var list []string
	for _, item := range m.Ids {
		list = append(list, strconv.FormatInt(int64(item), 10))

	}
	db := model.DB.Self.Table(tbName)
	result := db.
		Where(fmt.Sprintf("id in (%s)", strings.Join(list, ","))).
		Update("phase", online)
	if result.Error != nil {
		return result.Error
	}
	for _, id := range m.Ids {
		CreateManageLog(tbName, logTbName, id, "Enable", m.Operator)
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

// compareWithExistDB 检查重复库表
func (m *CreatePartitionsInput) compareWithExistDB(tbName string) (warnings []string, err error) {
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
		1、根据config_id去配置表中查到相关配置信息
		2、写入日志表
	*/
	var partitionConfig PartitionConfig
	partitionConfig.ID = id
	model.DB.Self.Table(dbName).First(&partitionConfig)
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
