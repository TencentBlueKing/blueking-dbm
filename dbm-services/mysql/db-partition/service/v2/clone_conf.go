package v2

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/service"

	"golang.org/x/exp/slog"
)

// ClonePartitionsConfig 按 infos 逐对克隆，冲突不中断整批
func ClonePartitionsConfig(input *CloneConfInput) (*CloneConfOutput, error) {
	if err := validateCloneConfInput(input); err != nil {
		return nil, err
	}

	tbName, logTbName, err := resolvePartitionTablesV2(input.ClusterType)
	if err != nil {
		return nil, err
	}

	now := time.Now()
	out := &CloneConfOutput{
		Errors: make([]string, 0),
	}
	seen := make(map[string]struct{})

	for _, pair := range input.Infos {
		sources, err := querySourceConfigs(tbName, pair.Source)
		if err != nil {
			out.Errors = append(out.Errors, fmt.Sprintf(
				"查询源配置失败 source=%s err=%s", pair.Source.ImmuteDomain, err.Error()))
			continue
		}
		if len(sources) == 0 {
			out.Errors = append(out.Errors, fmt.Sprintf(
				"源端无分区配置，跳过: source=%s dblikes=%v tblikes=%v",
				pair.Source.ImmuteDomain, pair.Source.Dblikes, pair.Source.Tblikes))
			continue
		}

		dblikeMap := zipNameMap(pair.Source.Dblikes, pair.Target.Dblikes)
		tblikeMap := zipNameMap(pair.Source.Tblikes, pair.Target.Tblikes)

		for _, src := range sources {
			cfg := rewriteCloneConfig(src, pair.Target, input.Operator, now, dblikeMap, tblikeMap)
			key := fmt.Sprintf("%d|%s|%s|%s", cfg.BkBizId, cfg.ImmuteDomain, cfg.DbLike, cfg.TbLike)
			if _, ok := seen[key]; ok {
				out.Errors = append(out.Errors, fmt.Sprintf(
					"本次克隆内部冲突，跳过: source=%s target=%s dblike=%s tblike=%s",
					pair.Source.ImmuteDomain, cfg.ImmuteDomain, cfg.DbLike, cfg.TbLike))
				continue
			}
			seen[key] = struct{}{}

			exists, err := cloneTargetExists(tbName, cfg)
			if err != nil {
				out.Errors = append(out.Errors, fmt.Sprintf(
					"检查冲突失败 source=%s target=%s dblike=%s tblike=%s err=%s",
					pair.Source.ImmuteDomain, cfg.ImmuteDomain, cfg.DbLike, cfg.TbLike, err.Error()))
				continue
			}
			if exists {
				out.Errors = append(out.Errors, fmt.Sprintf(
					"目标已存在配置，跳过: source=%s target=%s dblike=%s tblike=%s",
					pair.Source.ImmuteDomain, cfg.ImmuteDomain, cfg.DbLike, cfg.TbLike))
				continue
			}

			if err := model.DB.Self.Table(tbName).Create(&cfg).Error; err != nil {
				slog.Error("v2 clone_conf insert failed",
					"source", pair.Source.ImmuteDomain,
					"target", cfg.ImmuteDomain, "dblike", cfg.DbLike, "tblike", cfg.TbLike, "error", err)
				out.Errors = append(out.Errors, fmt.Sprintf(
					"写入失败 source=%s target=%s dblike=%s tblike=%s err=%s",
					pair.Source.ImmuteDomain, cfg.ImmuteDomain, cfg.DbLike, cfg.TbLike, err.Error()))
				continue
			}

			service.CreateManageLog(tbName, logTbName, cfg.ID, opInsert, input.Operator)
			out.SuccessCount++
		}
	}

	switch {
	case len(out.Errors) == 0:
		out.Info = "分区配置克隆成功！"
	case out.SuccessCount == 0:
		out.Info = "分区配置克隆失败，全部冲突、无源配置或写入失败。"
	default:
		out.Info = "分区配置部分克隆成功，详见 errors。"
	}
	return out, nil
}

func validateCloneConfInput(input *CloneConfInput) error {
	input.ClusterType = strings.TrimSpace(input.ClusterType)
	input.Operator = strings.TrimSpace(input.Operator)
	if input.ClusterType == "" {
		return errors.New("cluster_type 不能为空")
	}
	if input.Operator == "" {
		return errors.New("operator 不能为空")
	}
	if len(input.Infos) == 0 {
		return errors.New("infos 不能为空")
	}
	for i := range input.Infos {
		if err := validateCloneConfPair(&input.Infos[i], i); err != nil {
			return err
		}
	}
	return nil
}

func validateCloneConfPair(pair *CloneConfPair, idx int) error {
	prefix := fmt.Sprintf("infos[%d]", idx)
	src := &pair.Source
	dst := &pair.Target

	src.ImmuteDomain = strings.TrimSpace(src.ImmuteDomain)
	src.Dblikes = trimNonEmpty(src.Dblikes)
	src.Tblikes = trimNonEmpty(src.Tblikes)
	dst.ImmuteDomain = strings.TrimSpace(dst.ImmuteDomain)
	dst.Dblikes = trimNonEmpty(dst.Dblikes)
	dst.Tblikes = trimNonEmpty(dst.Tblikes)
	dst.DbAppAbbr = strings.TrimSpace(dst.DbAppAbbr)
	dst.BkBizName = strings.TrimSpace(dst.BkBizName)

	if src.ImmuteDomain == "" {
		return fmt.Errorf("%s 源端 immute_domain 不能为空", prefix)
	}
	if len(src.Dblikes) == 0 && len(src.Tblikes) > 0 {
		return fmt.Errorf("%s 指定表必须同时指定源端库列表", prefix)
	}
	if len(src.Dblikes) == 0 && len(dst.Dblikes) > 0 {
		return fmt.Errorf("%s 集群级克隆不允许填写目标库名列表", prefix)
	}
	if len(src.Tblikes) == 0 && len(dst.Tblikes) > 0 {
		return fmt.Errorf("%s 未指定源表时不允许填写目标表名列表", prefix)
	}
	if len(dst.Dblikes) > 0 && len(dst.Dblikes) != len(src.Dblikes) {
		return fmt.Errorf("%s 目标 dblikes 须与源 dblikes 等长，或为空表示同名映射", prefix)
	}
	if len(dst.Tblikes) > 0 && len(dst.Tblikes) != len(src.Tblikes) {
		return fmt.Errorf("%s 目标 tblikes 须与源 tblikes 等长，或为空表示同名映射", prefix)
	}
	if dst.ImmuteDomain == "" {
		return fmt.Errorf("%s 目标端 immute_domain 不能为空", prefix)
	}
	if dst.ClusterId == 0 {
		return fmt.Errorf("%s 目标端 cluster_id 不能为空", prefix)
	}
	if dst.Port == 0 {
		return fmt.Errorf("%s 目标端 port 不能为空", prefix)
	}
	if dst.BkBizId == 0 {
		return fmt.Errorf("%s 目标端 bk_biz_id 不能为空", prefix)
	}
	if dst.DbAppAbbr == "" {
		return fmt.Errorf("%s 目标端 db_app_abbr 不能为空", prefix)
	}
	if dst.BkBizName == "" {
		return fmt.Errorf("%s 目标端 bk_biz_name 不能为空", prefix)
	}
	return nil
}

func trimNonEmpty(items []string) []string {
	out := make([]string, 0, len(items))
	for _, item := range items {
		item = strings.TrimSpace(item)
		if item == "" {
			continue
		}
		out = append(out, item)
	}
	return out
}

func zipNameMap(srcNames, dstNames []string) map[string]string {
	m := make(map[string]string, len(srcNames))
	if len(dstNames) == 0 {
		return m
	}
	for i, src := range srcNames {
		m[src] = dstNames[i]
	}
	return m
}

func querySourceConfigs(tbName string, src CloneEndpoint) ([]service.PartitionConfig, error) {
	tx := model.DB.Self.Table(tbName).Where("immute_domain = ?", src.ImmuteDomain)
	if len(src.Dblikes) > 0 {
		tx = tx.Where("dblike IN ?", src.Dblikes)
	}
	if len(src.Tblikes) > 0 {
		tx = tx.Where("tblike IN ?", src.Tblikes)
	}

	var configs []service.PartitionConfig
	if err := tx.Find(&configs).Error; err != nil {
		slog.Error("v2 clone_conf query source failed", "error", err)
		return nil, err
	}
	return configs, nil
}

func rewriteCloneConfig(
	src service.PartitionConfig,
	target CloneEndpoint,
	operator string,
	now time.Time,
	dblikeMap, tblikeMap map[string]string,
) service.PartitionConfig {
	cfg := src
	cfg.ID = 0
	cfg.ImmuteDomain = target.ImmuteDomain
	cfg.ClusterId = target.ClusterId
	cfg.Port = target.Port
	cfg.BkCloudId = target.BkCloudId
	cfg.BkBizId = target.BkBizId
	cfg.DbAppAbbr = target.DbAppAbbr
	cfg.BkBizName = target.BkBizName
	if renamed, ok := dblikeMap[src.DbLike]; ok {
		cfg.DbLike = renamed
	}
	if renamed, ok := tblikeMap[src.TbLike]; ok {
		cfg.TbLike = renamed
	}
	cfg.Phase = phaseOnline
	cfg.Creator = operator
	cfg.Updator = operator
	cfg.CreateTime = now
	cfg.UpdateTime = now
	return cfg
}

func cloneTargetExists(tbName string, cfg service.PartitionConfig) (bool, error) {
	var count int64
	err := model.DB.Self.Table(tbName).
		Where("bk_biz_id = ? and immute_domain = ? and dblike = ? and tblike = ?",
			cfg.BkBizId, cfg.ImmuteDomain, cfg.DbLike, cfg.TbLike).
		Count(&count).Error
	if err != nil {
		return false, err
	}
	return count > 0, nil
}
