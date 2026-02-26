// Package v2 分区服务 v2，model 与 service 共用
package v2

import (
	"errors"
	"fmt"
	"strings"

	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/service"

	"golang.org/x/exp/slog"
	"gorm.io/gorm"
	glogger "gorm.io/gorm/logger"
)

// GetPartitionsConfig v2 根据条件查询分区配置（不联表日志表）
func GetPartitionsConfig(input *service.QueryParititionsInput) ([]*service.PartitionConfig, int64, error) {
	allResults := []*service.PartitionConfig{}
	var configTb string

	switch strings.ToLower(input.ClusterType) {
	case service.Tendbha, service.Tendbsingle:
		configTb = service.MysqlPartitionConfigV2
	case service.Tendbcluster:
		configTb = service.SpiderPartitionConfigV2
	default:
		return nil, 0, errors.New("不支持的db类型")
	}
	// 构造基础查询：只针对配置表本身
	tx := model.DB.Self.Session(&gorm.Session{}).Table(configTb)

	// 用一个切片描述所有可选条件，args 用 []interface{} 方便以后扩展（如 BETWEEN ? AND ? 等多占位符）
	type condition struct {
		enabled bool
		query   string
		args    []interface{}
	}

	conds := []condition{
		{input.BkBizId > 0, "bk_biz_id = ?", []interface{}{input.BkBizId}},
		{len(input.Ids) != 0, "id IN ?", []interface{}{input.Ids}},
		{len(input.ImmuteDomains) != 0, "immute_domain IN ?", []interface{}{input.ImmuteDomains}},
		{len(input.DbLikes) != 0, "dblike IN ?", []interface{}{input.DbLikes}},
		{len(input.TbLikes) != 0, "tblike IN ?", []interface{}{input.TbLikes}},
		{input.DomainName != "", "immute_domain LIKE ?", []interface{}{fmt.Sprintf("%%%s%%", input.DomainName)}},
	}

	for _, c := range conds {
		if c.enabled {
			tx = tx.Where(c.query, c.args...)
		}
	}

	// 统计总数
	var total int64
	if err := tx.Session(&gorm.Session{}).Count(&total).Error; err != nil {
		slog.Error("sql count error", err)
		return nil, 0, err
	}

	if input.Limit <= 0 {
		input.Limit = total
	}

	// 分页查询配置列表
	result := tx.Session(&gorm.Session{Logger: glogger.Default.LogMode(glogger.Info)}).
		Order("id DESC").
		Limit(int(input.Limit)).
		Offset(input.Offset).
		Find(&allResults)

	if result.Error != nil {
		slog.Error("sql execute error", result.Error)
		return nil, 0, result.Error
	}
	return allResults, total, nil
}
