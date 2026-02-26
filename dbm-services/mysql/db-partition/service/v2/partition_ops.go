// Package v2 分区服务 v2：使用 v1 相同的入参结构，但在 v2 下实现独立逻辑
package v2

import (
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/service"

	"golang.org/x/exp/slog"
)

// CreatePartitionsConfig v2 创建分区配置（逻辑独立实现），返回完整配置列表（包含 config_id）
func CreatePartitionsConfig(input *service.CreatePartitionsInput) (error, []service.PartitionConfig) {
	// 1. 解析分区配置表与审计表
	tbName, logTbName, err := resolvePartitionTablesV2(input.ClusterType)
	if err != nil {
		return err, nil
	}

	// 2. 校验入参
	if err := validatePartitionCreateInputV2(input); err != nil {
		return err, nil
	}

	// 3. 计算通用分区元信息
	reservedPartition, partitionType, err := calcPartitionMetaV2(input)
	if err != nil {
		return err, nil
	}

	// 4. 规则冲突与已存在检查
	warnings, err := gatherCreateWarningsV2(input, tbName)
	if err != nil {
		return err, nil
	}
	if len(warnings) > 0 {
		return errors.New(strings.Join(warnings, "\n")), nil
	}

	// 5. 批量落库，返回完整配置
	configs, err := insertPartitionConfigsV2(input, tbName, logTbName, reservedPartition, partitionType)
	if err != nil {
		return err, nil
	}
	return nil, configs
}

// UpdatePartitionsConfig v2 更新分区配置（逻辑独立实现），返回实际更新后的配置列表
// 更新分区类型这里前端传的是完整分区参数，
func UpdatePartitionsConfig(input *service.CreatePartitionsInput) (error, []service.PartitionConfig) {
	tbName, logTbName, err := resolvePartitionTablesV2(input.ClusterType)
	if err != nil {
		return err, nil
	}
	if err := validatePartitionCreateInputV2(input); err != nil {
		return err, nil
	}

	reservedPartition, partitionType, err := calcPartitionMetaV2(input)
	if err != nil {
		return err, nil
	}

	var (
		errs           []string
		updatedConfigs []service.PartitionConfig
	)
	for _, dblike := range input.DbLikes {
		for _, tblike := range input.TbLikes {
			var partitionConfig service.PartitionConfig
			query := struct {
				BkBizId      int64  `gorm:"column:bk_biz_id"`
				ImmuteDomain string `gorm:"column:immute_domain"`
				DbLike       string `gorm:"column:dblike"`
				TbLike       string `gorm:"column:tblike"`
			}{input.BkBizId, input.ImmuteDomain, dblike, tblike}

			nowConfigResult := model.DB.Self.Table(tbName).Where(&query).First(&partitionConfig)
			if nowConfigResult.Error != nil {
				errResult := fmt.Sprintf("query:%+v err:%s", query, nowConfigResult.Error)
				slog.Error(errResult)
				errs = append(errs, errResult)
				continue
			}

			service.CreateManageLog(tbName, logTbName, partitionConfig.ID, "Update", input.Updator)

			if ContainsMapV2(Slice2MapV2([]int{1, 3, 4}), partitionConfig.PartitionType) {
				if input.PartitionColumn != partitionConfig.PartitionColumn ||
					input.PartitionColumnType != partitionConfig.PartitionColumnType {
					return errors.New("非标准分区类型，不可修改分区字段和分区字段类型！"), nil
				}
				partitionType = partitionConfig.PartitionType
			}

			now := time.Now()
			updateColumns := map[string]interface{}{
				"partition_column":        input.PartitionColumn,
				"partition_column_type":   input.PartitionColumnType,
				"reserved_partition":      reservedPartition,
				"partition_time_interval": input.PartitionTimeInterval,
				"partition_type":          partitionType,
				"expire_time":             input.ExpireTime,
				"updator":                 input.Updator,
				"update_time":             now,
			}

			result := model.DB.Self.Table(tbName).
				Where("bk_biz_id=? and immute_domain=? and dblike=? and tblike=?",
					input.BkBizId, input.ImmuteDomain, dblike, tblike).
				Updates(updateColumns)
			if result.Error != nil {
				errs = append(errs, result.Error.Error())
				continue
			}

			// 构造更新后的配置快照返回给调用方
			updated := partitionConfig
			updated.PartitionColumn = input.PartitionColumn
			updated.PartitionColumnType = input.PartitionColumnType
			updated.ReservedPartition = reservedPartition
			updated.PartitionTimeInterval = input.PartitionTimeInterval
			updated.PartitionType = partitionType
			updated.ExpireTime = input.ExpireTime
			updated.Updator = input.Updator
			updated.UpdateTime = now
			updatedConfigs = append(updatedConfigs, updated)
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("errors: %s", strings.Join(errs, "\n")), nil
	}
	return nil, updatedConfigs
}

// DeletePartitionsConfig v2 删除分区配置（逻辑独立实现）
func DeletePartitionsConfig(input *service.DeletePartitionConfigByIds) error {
	if input.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if len(input.Ids) == 0 {
		return errno.ConfigIdIsEmpty
	}

	tbName, logTbName, err := resolvePartitionTablesV2(input.ClusterType)
	if err != nil {
		return err
	}

	for _, configID := range input.Ids {
		service.CreateManageLog(tbName, logTbName, configID, "Delete", input.Operator)
	}

	result := model.DB.Self.Table(tbName).
		Where("bk_biz_id=?", input.BkBizId).
		Delete(&service.PartitionConfig{}, input.Ids)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.PartitionConfigNotExisted
	}
	return nil
}

// DisablePartition v2 禁用分区（逻辑独立实现）
func DisablePartition(input *service.DisablePartitionInput) error {
	if len(input.Ids) == 0 {
		return errno.ConfigIdIsEmpty
	}
	return updatePhaseByIDsV2(input.ClusterType, "offline", "Disable", input.Operator, input.Ids)
}

// EnablePartition v2 启用分区（逻辑独立实现）
func EnablePartition(input *service.EnablePartitionInput) error {
	if len(input.Ids) == 0 {
		return errno.ConfigIdIsEmpty
	}
	return updatePhaseByIDsV2(input.ClusterType, "online", "Enable", input.Operator, input.Ids)
}

// updatePhaseByIDsV2 根据配置 ID 批量更新 phase，并记录管理日志
func updatePhaseByIDsV2(clusterType, phase, action, operator string, ids []int) error {
	tbName, logTbName, err := resolvePartitionTablesV2(clusterType)
	if err != nil {
		return err
	}

	db := model.DB.Self.Table(tbName)
	result := db.Where("id in ?", ids).Update("phase", phase)
	if result.Error != nil {
		return result.Error
	}
	for _, id := range ids {
		service.CreateManageLog(tbName, logTbName, id, action, operator)
	}
	return nil
}

// resolvePartitionTablesV2 根据集群类型解析配置表和管理日志表
func resolvePartitionTablesV2(clusterType string) (tbName, logTbName string, err error) {
	switch strings.ToLower(clusterType) {
	case service.Tendbha, service.Tendbsingle:
		return service.MysqlPartitionConfigV2, service.MysqlManageLogsTable, nil
	case service.Tendbcluster:
		return service.SpiderPartitionConfigV2, service.SpiderManageLogsTable, nil
	default:
		return "", "", errors.New("不支持的db类型")
	}
}

// validatePartitionCreateInputV2 校验创建/更新分区配置的基础参数
func validatePartitionCreateInputV2(input *service.CreatePartitionsInput) error {
	if len(input.PartitionColumn) == 0 {
		return errors.New("请输入分区字段！")
	}
	if len(input.DbLikes) == 0 || len(input.TbLikes) == 0 {
		return errors.New("库表名不能为空！")
	}
	if input.PartitionTimeInterval < 1 {
		return errors.New("分区间隔不能小于1")
	}
	if input.ExpireTime < input.PartitionTimeInterval {
		return errors.New("过期时间必须不小于分区间隔")
	}
	if input.ExpireTime%input.PartitionTimeInterval != 0 {
		return errors.New("过期时间必须是分区间隔的整数倍")
	}
	return nil
}

// calcPartitionMetaV2 计算保留分区数和分区类型
func calcPartitionMetaV2(input *service.CreatePartitionsInput) (reservedPartition int, partitionType int, err error) {
	reservedPartition = input.ExpireTime / input.PartitionTimeInterval

	switch input.PartitionColumnType {
	case "datetime", "date":
		if strings.EqualFold(input.RemoteHashAlgorithm, "range") {
			partitionType = 4
		} else {
			partitionType = 0
		}
	case "timestamp":
		partitionType = 5
	case "int", "bigint":
		if strings.EqualFold(input.RemoteHashAlgorithm, "list") {
			partitionType = 3
		} else {
			partitionType = 101
		}
	default:
		return 0, 0, errors.New("请选择分区字段类型：datetime、date、timestamp、int、bigint")
	}

	return reservedPartition, partitionType, nil
}

// gatherCreateWarningsV2 汇总创建配置前的告警信息
func gatherCreateWarningsV2(input *service.CreatePartitionsInput, tbName string) ([]string, error) {
	warnings1, err := compareWithSameArrayV2(input)
	if err != nil {
		return nil, err
	}
	warnings2, err := compareWithExistDBV2(input, tbName)
	if err != nil {
		return nil, err
	}
	return append(warnings1, warnings2...), nil
}

// insertPartitionConfigsV2 批量插入分区配置并记录管理日志
func insertPartitionConfigsV2(
	input *service.CreatePartitionsInput,
	tbName, logTbName string,
	reservedPartition, partitionType int,
) ([]service.PartitionConfig, error) {
	var (
		configs []service.PartitionConfig
		errs    []string
	)

	// 公共字段基准配置，避免在循环中重复赋值
	base := service.PartitionConfig{
		BkBizId:               input.BkBizId,
		DbAppAbbr:             input.DbAppAbbr,
		BkBizName:             input.BkBizName,
		ImmuteDomain:          input.ImmuteDomain,
		Port:                  input.Port,
		BkCloudId:             input.BkCloudId,
		ClusterId:             input.ClusterId,
		PartitionColumn:       input.PartitionColumn,
		PartitionColumnType:   input.PartitionColumnType,
		ReservedPartition:     reservedPartition,
		ExtraPartition:        15,
		PartitionTimeInterval: input.PartitionTimeInterval,
		PartitionType:         partitionType,
		ExpireTime:            input.ExpireTime,
		TimeZone:              input.TimeZone,
		Creator:               input.Creator,
		Updator:               input.Updator,
		Phase:                 "online",
		CreateTime:            time.Now(),
		UpdateTime:            time.Now(),
	}

	for _, dblike := range input.DbLikes {
		for _, tblike := range input.TbLikes {
			cfg := base
			cfg.DbLike = dblike
			cfg.TbLike = tblike

			if err := model.DB.Self.Table(tbName).Create(&cfg).Error; err != nil {
				// 单条失败（如唯一键冲突）不影响后续插入，只收集错误
				errs = append(errs, fmt.Sprintf("dblike=%s tblike=%s err=%s", dblike, tblike, err.Error()))
				continue
			}

			configs = append(configs, cfg)
			service.CreateManageLog(tbName, logTbName, cfg.ID, "Insert", input.Creator)
		}
	}

	if len(errs) > 0 {
		return nil, fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
	}
	return configs, nil
}

// compareWithSameArrayV2 复制 v1 中的冲突检测逻辑，作用于 v2 的 CreatePartitionsInput
func compareWithSameArrayV2(m *service.CreatePartitionsInput) (warnings []string, err error) {
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
				warning := fmt.Sprintf("本次提交中，规则%s与规则%s存在冲突，请修改后再次提交！", dbi, dbj)
				warnings = append(warnings, warning)
			}
		}
	}
	return warnings, nil
}

// compareWithExistDBV2 复制 v1 中的已有库表冲突检测逻辑
func compareWithExistDBV2(m *service.CreatePartitionsInput, tbName string) (warnings []string, err error) {
	var configs []*service.PartitionConfig
	result := model.DB.Self.Table(tbName).Find(&configs)
	if result.Error != nil {
		return warnings, result.Error
	}
	for _, cfg := range configs {
		for _, dblike := range m.DbLikes {
			for _, tblike := range m.TbLikes {
				dbReg, err := regexp.Compile(strings.Replace(dblike+"$", "%", ".*", -1))
				if err != nil {
					return warnings, err
				}
				tbReg, err := regexp.Compile(strings.Replace(tblike+"$", "%", ".*", -1))
				if err != nil {
					return warnings, err
				}
				if dbReg.MatchString(cfg.DbLike) && tbReg.MatchString(cfg.TbLike) {
					warning := fmt.Sprintf("与已有规则[%s.%s]存在冲突，请修改后再次提交！", cfg.DbLike, cfg.TbLike)
					warnings = append(warnings, warning)
				}
			}
		}
	}
	return warnings, nil
}

// Slice2MapV2 / ContainsMapV2 用于更新逻辑中的分区类型判断
func Slice2MapV2(s []int) map[int]struct{} {
	m := make(map[int]struct{}, len(s))
	for _, v := range s {
		m[v] = struct{}{}
	}
	return m
}

func ContainsMapV2(m map[int]struct{}, i int) bool {
	_, ok := m[i]
	return ok
}
