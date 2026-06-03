package v2

import (
	"errors"
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/service"

	"golang.org/x/exp/slog"
	"gorm.io/gorm"
)

const (
	defaultCheckBizLimit     int64 = 100
	defaultCheckConfIDsLimit int64 = 2000
)

var checkPhases = []string{phaseOnline, phaseOffline}

// ListCheckBiz 按 cluster_type 分页返回待检业务列表（phase IN online/offline）
func ListCheckBiz(input *ListCheckBizInput) (*ListCheckBizOutput, error) {
	if err := validateCheckOffset(input.Offset); err != nil {
		return nil, err
	}
	if input.Limit <= 0 {
		input.Limit = defaultCheckBizLimit
	}

	configTb, err := resolveCheckConfigTable(input.ClusterType)
	if err != nil {
		return nil, err
	}

	slog.Info("v2 ListCheckBiz",
		"cluster_type", input.ClusterType,
		"table", configTb,
		"limit", input.Limit,
		"offset", input.Offset)

	out := &ListCheckBizOutput{Items: []CheckBizItem{}}

	// 业务组总数：对 GROUP BY 子查询做 COUNT
	groupSubQuery := model.DB.Self.Session(&gorm.Session{}).Table(configTb).
		Select("bk_biz_id, db_app_abbr").
		Where("phase IN ?", checkPhases).
		Group("bk_biz_id, db_app_abbr")
	if err := model.DB.Self.Session(&gorm.Session{}).
		Table("(?) AS grouped", groupSubQuery).
		Count(&out.Count).Error; err != nil {
		slog.Error("v2 ListCheckBiz count error", "error", err)
		return nil, fmt.Errorf("count check biz error: %w", err)
	}
	if out.Count == 0 {
		return out, nil
	}

	if err := checkConfigQuery(configTb).Session(&gorm.Session{}).
		Select("bk_biz_id, db_app_abbr, COUNT(id) AS config_count").
		Group("bk_biz_id, db_app_abbr").
		Order("bk_biz_id ASC, db_app_abbr ASC").
		Limit(int(input.Limit)).
		Offset(input.Offset).
		Scan(&out.Items).Error; err != nil {
		slog.Error("v2 ListCheckBiz list error", "error", err)
		return nil, fmt.Errorf("list check biz error: %w", err)
	}

	return out, nil
}

// ListCheckConfIds 按 cluster_type + bk_biz_id 分页返回待检 config_id
func ListCheckConfIds(input *ListCheckConfIdsInput) (*ListCheckConfIdsOutput, error) {
	if input.BkBizId <= 0 {
		return nil, errno.BkBizIdIsEmpty
	}
	if err := validateCheckOffset(input.Offset); err != nil {
		return nil, err
	}
	if input.Limit <= 0 {
		input.Limit = defaultCheckConfIDsLimit
	}

	configTb, err := resolveCheckConfigTable(input.ClusterType)
	if err != nil {
		return nil, err
	}

	slog.Info("v2 ListCheckConfIds",
		"cluster_type", input.ClusterType,
		"table", configTb,
		"bk_biz_id", input.BkBizId,
		"limit", input.Limit,
		"offset", input.Offset)

	out := &ListCheckConfIdsOutput{ConfigIds: []int64{}}
	tx := checkConfigQuery(configTb).Where("bk_biz_id = ?", input.BkBizId)

	if err := tx.Session(&gorm.Session{}).Count(&out.Count).Error; err != nil {
		slog.Error("v2 ListCheckConfIds count error", "error", err)
		return nil, fmt.Errorf("count check conf ids error: %w", err)
	}
	if out.Count == 0 {
		return out, nil
	}

	var rows []struct {
		ID int64 `gorm:"column:id"`
	}
	if err := tx.Session(&gorm.Session{}).
		Select("id").
		Order("id ASC").
		Limit(int(input.Limit)).
		Offset(input.Offset).
		Find(&rows).Error; err != nil {
		slog.Error("v2 ListCheckConfIds list error", "error", err)
		return nil, fmt.Errorf("list check conf ids error: %w", err)
	}
	for _, row := range rows {
		out.ConfigIds = append(out.ConfigIds, row.ID)
	}
	return out, nil
}

// checkConfigQuery 待检配置基础条件：phase IN (online, offline)
func checkConfigQuery(configTb string) *gorm.DB {
	return model.DB.Self.Session(&gorm.Session{}).Table(configTb).Where("phase IN ?", checkPhases)
}

func resolveCheckConfigTable(clusterType string) (string, error) {
	switch strings.ToLower(clusterType) {
	case service.Tendbha, service.Tendbsingle:
		return service.MysqlPartitionConfigV2, nil
	case service.Tendbcluster:
		return service.SpiderPartitionConfigV2, nil
	default:
		return "", errno.NotSupportedClusterType
	}
}

func validateCheckOffset(offset int) error {
	if offset < 0 {
		return errors.New("offset 不能小于 0")
	}
	return nil
}
