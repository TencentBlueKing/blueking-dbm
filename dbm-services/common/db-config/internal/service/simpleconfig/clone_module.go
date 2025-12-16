package simpleconfig

import (
	"fmt"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"

	"github.com/huandu/go-sqlbuilder"
	"gorm.io/gorm"
)

func CloneModuleConfig(r *api.CloneModuleConfigReq, opUser string, db *gorm.DB) error {
	sb := sqlbuilder.MySQL.NewInsertBuilder()
	sb.InsertIgnoreInto((&model.ConfigModel{}).TableName()).Cols(
		"bk_biz_id", "level_value", "conf_file",
		"namespace", "conf_type", "conf_name", "conf_value", "level_name")
	insertSelect := sb.Select(
		"'"+r.TargetBkBizID+"'",
		"'"+r.TargetModuleID+"'",
		"'"+r.TargetConfFile+"'",
		"namespace", "conf_type", "conf_name", "conf_value", "level_name",
	).From((&model.ConfigModel{}).TableName())
	insertSelect.Where(fmt.Sprintf("level_name='module' and namespace = '%s' and conf_type = '%s'",
		r.Namespace, r.ConfType))
	insertSelect.Where(
		insertSelect.Equal("bk_biz_id", r.SourceBkBizID),
		insertSelect.Equal("level_value", r.SourceModuleID),
		insertSelect.Equal("conf_file", r.SourceConfFile))
	sql, args := sb.Build()
	logger.Infof("clone module config sql: %v, %v", sql, args)

	return db.Exec(sql, args...).Error
}

func CloneClusterConfig(r *api.CloneClusterConfigReq, opUser string, db *gorm.DB) error {
	txErr := model.DB.Self.Transaction(func(tx *gorm.DB) error {
		// module
		err := CloneModuleConfig(&r.CloneModuleConfigReq, "", tx)
		if err != nil {
			return err
		}

		// cluster
		sb2 := sqlbuilder.MySQL.NewInsertBuilder()
		sb2.InsertIgnoreInto((&model.ConfigModel{}).TableName()).Cols(
			"bk_biz_id", "level_value", "conf_file",
			"namespace", "conf_type", "conf_name", "conf_value", "level_name")
		insertSelect2 := sb2.Select(
			"'"+r.TargetBkBizID+"'",
			"level_value",
			"'"+r.TargetConfFile+"'",
			"namespace", "conf_type", "conf_name", "conf_value", "level_name",
		).From((&model.ConfigModel{}).TableName())
		insertSelect2.Where(fmt.Sprintf("level_name='cluster' and namespace = '%s' and conf_type = '%s'",
			r.Namespace, r.ConfType))
		insertSelect2.Where(
			insertSelect2.Equal("bk_biz_id", r.SourceBkBizID),
			insertSelect2.In("level_value", r.ClusterDomains),
			insertSelect2.Equal("conf_file", r.SourceConfFile))
		sql, args := sb2.Build()
		logger.Infof("clone cluster config sql: %v, %v", sql, args)

		if err = tx.Exec(sql, args...).Error; err != nil {
			return err
		}

		for _, clusterDomain := range r.ClusterDomains {
			levelNode := api.BaseConfigNode{}
			levelName := "cluster"
			levelNode.Set(r.TargetBkBizID, r.Namespace, r.ConfType, r.TargetConfFile, levelName, clusterDomain)
			publishReq := &api.SimpleConfigQueryReq{
				BaseConfigNode: levelNode,
				InheritFrom:    "0",
				View:           fmt.Sprintf("merge.%s", levelName),
				Format:         constvar.FormatMap,
				Description:    "clone cluster config", // 发布描述
				Revision:       "",
				CreatedBy:      "",
				UpLevelInfo: api.UpLevelInfo{
					LevelInfo: map[string]string{
						"module": r.TargetModuleID,
					},
				},
			}
			logger.Infof("generate config for new cloned cluster: bk_biz_id %s module %s cluster %s",
				r.TargetBkBizID, r.TargetModuleID, clusterDomain)
			if _, err := GenerateConfigFile(tx, publishReq, constvar.MethodGenAndPublish, nil); err != nil {
				return err
			}
		}
		return nil
	})
	return txErr
}
