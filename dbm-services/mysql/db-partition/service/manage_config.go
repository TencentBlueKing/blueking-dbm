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
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"

	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// GetPartitionsConfig TODO
func (m *QueryParititionsInput) GetPartitionsConfig() ([]*PartitionConfigWithLog, int64, error) {
	allResults := make([]*PartitionConfigWithLog, 0)
	var tbName string
	// Cnt 用于返回匹配到的行数
	type Cnt struct {
		Count int64 `gorm:"column:cnt"`
	}
	// 判断是mysql集群还是spider集群
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
	default:
		return nil, 0, errors.New("不支持的db类型")
	}
	where := " 1=1 "
	if m.BkBizId > 0 {
		where = fmt.Sprintf("%s and config.bk_biz_id=%d", where, m.BkBizId)
	}
	if len(m.ImmuteDomains) != 0 {
		dns := " and config.immute_domain in ('" + strings.Join(m.ImmuteDomains, "','") + "') "
		where = where + dns
	}
	if len(m.DbLikes) != 0 {
		dblike := "and config.dblike in ('" + strings.Join(m.DbLikes, "','") + "') "
		where = where + dblike
	}
	if len(m.TbLikes) != 0 {
		tblike := "and config.tblike in ('" + strings.Join(m.TbLikes, "','") + "') "
		where = where + tblike
	}
	cnt := Cnt{}
	vsql := fmt.Sprintf("select count(*) as cnt from `%s`", tbName)
	err := model.DB.Self.Debug().Table(tbName).Raw(vsql).Scan(&cnt).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}
	limitCondition := fmt.Sprintf("limit %d offset %d", m.Limit, m.Offset)
	condition := fmt.Sprintf("%s %s", where, limitCondition)
	// ticket_id NULL，规则没有被执行过
	vsql = fmt.Sprintf("SELECT config.*, d.create_time as execute_time, "+
		"d.ticket_id as ticket_id, d.ticket_status as ticket_status, d.check_info as check_info, "+
		"d.status as status FROM "+
		"%s AS config LEFT JOIN (SELECT c.*, ticket.status as ticket_status  FROM "+
		"(SELECT a.* FROM partition_cron_log AS a, "+
		"(SELECT inner_config.id AS config_id, MAX(inner_log.id) AS log_id FROM "+
		"%s AS inner_config LEFT JOIN "+
		"partition_cron_log AS inner_log ON inner_config.id = inner_log.config_id where "+
		"inner_log.create_time > DATE_SUB(now(),interval 100 day) GROUP BY inner_config.id) "+
		"AS b WHERE a.id = b.log_id) AS c LEFT JOIN `%s`.ticket_ticket AS ticket "+
		"ON ticket.id = c.ticket_id) AS d ON config.id = d.config_id where %s;", tbName, tbName,
		viper.GetString("dbm_db_name"), condition)
	err = model.DB.Self.Debug().Table(tbName).Raw(vsql).Scan(&allResults).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}
	return allResults, cnt.Count, nil
}

// GetPartitionLog TODO
func (m *QueryLogInput) GetPartitionLog() ([]*PartitionLog, int64, error) {
	allResults := make([]*PartitionLog, 0)
	var tbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
	default:
		return nil, 0, errors.New("不支持的db类型")
	}
	// Cnt 用于返回匹配到的行数
	type Cnt struct {
		Count int64 `gorm:"column:cnt"`
	}
	vsql := fmt.Sprintf("select logs.*,ticket.status as ticket_status from "+
		"(select config.id as id, log.ticket_id as ticket_id, log.create_time as execute_time, "+
		"log.check_info as check_info, log.status as status "+
		"from %s as config join partition_cron_log as log "+
		"where log.config_id=config.id and config.id=%d and log.create_time>"+
		"DATE_SUB(now(),interval 100 day)) as logs left join "+
		"`%s`.ticket_ticket as ticket on ticket.id=logs.ticket_id where "+
		"ticket.create_at > DATE_SUB(now(),interval 100 day)) "+
		"order by execute_time desc ", tbName, m.ConfigId, viper.GetString("dbm_db_name"))
	err := model.DB.Self.Debug().Table(tbName).Raw(vsql).Scan(&allResults).Error
	if err != nil {
		return nil, 0, err
	}
	cnt := Cnt{}
	countSQL := fmt.Sprintf("select count(*) as cnt from (%s) c", vsql)
	err = model.DB.Self.Debug().Table(tbName).Raw(countSQL).Scan(&cnt).Error
	if err != nil {
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
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
	default:
		return errors.New("不支持的db类型")
	}
	var list []string
	for _, item := range m.Ids {
		list = append(list, strconv.FormatInt(item, 10))

	}
	sql := fmt.Sprintf("delete from `%s` where id in (%s) and bk_biz_id = %d", tbName, strings.Join(list, ","),
		m.BkBizId)
	result := model.DB.Self.Debug().Exec(sql)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.PartitionConfigNotExisted
	}
	return nil
}

// CreatePartitionsConfig TODO
func (m *CreatePartitionsInput) CreatePartitionsConfig() (error, []int) {
	var tbName string
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
	default:
		return errors.New("错误的db类型"), []int{}
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
	switch m.PartitionColumnType {
	case "datetime":
		partitionType = 0
	case "timestamp":
		partitionType = 5
	case "int":
		partitionType = 101
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
				Creator:               m.Creator,
				Updator:               m.Updator,
				Phase:                 online,
				CreateTime:            time.Now(),
				UpdateTime:            time.Now(),
			}
			result := model.DB.Self.Debug().Table(tbName).Create(&partitionConfig)
			configIDs = append(configIDs, partitionConfig.ID)
			if result.Error != nil {
				errs = append(errs, result.Error.Error())
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
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
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
			update_condition := fmt.Sprintf("bk_biz_id=%d and immute_domain='%s' and dblike='%s' and tblike='%s'",
				m.BkBizId, m.ImmuteDomain, dblike, tblike)
			var update_column struct {
				PartitionColumn       string
				PartitionColumnType   string
				ReservedPartition     int
				ExtraPartition        int
				PartitionTimeInterval int
				PartitionType         int
				ExpireTime            int
				Creator               string
				Updator               string
			}
			update_column.PartitionColumn = m.PartitionColumn
			update_column.PartitionColumnType = m.PartitionColumnType
			update_column.ReservedPartition = reservedPartition
			update_column.ExtraPartition = extraTime
			update_column.PartitionTimeInterval = m.PartitionTimeInterval
			update_column.PartitionType = partitionType
			update_column.ExpireTime = m.ExpireTime
			update_column.Creator = m.Creator
			update_column.Updator = m.Updator
			result := model.DB.Self.Debug().Table(tbName).Where(update_condition).Updates(&update_column)
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
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
	default:
		return errors.New("不支持的db类型")
	}
	var list []string
	for _, item := range m.Ids {
		list = append(list, strconv.FormatInt(item, 10))

	}
	db := model.DB.Self.Debug().Table(tbName)
	result := db.
		Where(fmt.Sprintf("id in (%s)", strings.Join(list, ","))).
		Update("phase", offline)
	if result.Error != nil {
		return result.Error
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
	switch strings.ToLower(m.ClusterType) {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
	default:
		return errors.New("不支持的db类型")
	}
	var list []string
	for _, item := range m.Ids {
		list = append(list, strconv.FormatInt(item, 10))

	}
	db := model.DB.Self.Debug().Table(tbName)
	result := db.
		Where(fmt.Sprintf("id in (%s)", strings.Join(list, ","))).
		Update("phase", online)
	if result.Error != nil {
		return result.Error
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
	err = model.DB.Self.Debug().Table(tbName).Select("dblike", "tblike").Where(condition).Find(&existRules).Error
	if err != nil {
		return existRules, err
	}
	return existRules, nil
}
