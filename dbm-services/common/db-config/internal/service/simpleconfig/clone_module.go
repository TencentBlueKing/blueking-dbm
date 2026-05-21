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

// DeleteModuleConfig 删除模块所有配置
func DeleteModuleConfig(r *api.DeleteModuleConfigReq, opUser string, db *gorm.DB) error {
	/*
		sb := sqlbuilder.MySQL.NewDeleteBuilder()
		sb.DeleteFrom((&model.ConfigModel{}).TableName()).
			Where(fmt.Sprintf("level_name='module' and namespace = '%s' and conf_type = '%s'",
				r.Namespace, r.ConfType))
		sql, args := sb.Build()
	*/
	//logger.Infof("delete module config sql: %v, %v", sql, args)
	deleteWhere := map[string]string{
		"namespace":   r.Namespace,
		"bk_biz_id":   r.BkBizID,
		"level_value": r.DbModuleId,
		"level_name":  "module",
	}
	res := db.Debug().Where(deleteWhere).Delete(&model.ConfigModel{})
	return res.Error
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

func ModuleCloneQuery(r *api.CloneModuleConfigReq, db *gorm.DB) (*api.CloneModuleQueryConfigResp, error) {
	reqSource := &api.SimpleConfigQueryReq{
		BaseConfigNode: api.BaseConfigNode{
			BKBizID: r.SourceBkBizID,
			BaseConfFileDef: api.BaseConfFileDef{
				Namespace: r.Namespace,
				ConfType:  r.ConfType,
				ConfFile:  r.SourceConfFile,
			},
			BaseLevelDef: api.BaseLevelDef{
				LevelName:  "module",
				LevelValue: r.SourceModuleID,
			},
		},
		Module:  r.SourceModuleID,
		Decrypt: true,
		Format:  constvar.FormatList,
		View:    constvar.ViewMerge,
	}
	reqTarget := &api.SimpleConfigQueryReq{
		BaseConfigNode: api.BaseConfigNode{
			BKBizID: r.TargetBkBizID,
			BaseConfFileDef: api.BaseConfFileDef{
				Namespace: r.Namespace,
				ConfType:  r.ConfType,
				ConfFile:  r.TargetConfFile,
			},
			BaseLevelDef: api.BaseLevelDef{
				LevelName:  "module",
				LevelValue: r.TargetModuleID,
			},
		},
		Module:  r.TargetModuleID,
		Decrypt: true,
		Format:  constvar.FormatList,
		View:    constvar.ViewMerge,
	}
	retSource, err := GenerateConfigFile(db, reqSource, constvar.MethodGenerateOnly, nil)
	if err != nil {
		return nil, err
	}
	retTarget, err := GenerateConfigFile(db, reqTarget, constvar.MethodGenerateOnly, nil)
	if err != nil {
		return nil, err
	}

	var confNamesDeprecated []string                        // 目标模块已经废弃的配置项
	var confNamesValueSource = make(map[string]interface{}) // 目标模块与原模块，哪些配置项值不一样。 map value 存的是 source 的值
	var confNamesValueModified []string                     // 源模块需要同步给模板模块的自定义配置项
	for confName, valueSource := range retSource.Content {
		valueTarget, ok := retTarget.Content[confName]
		if !ok {
			// 如果 retSource 里面有 retTarget 里面不存在的配置项，说明目标废弃了这个配置项
			confNamesDeprecated = append(confNamesDeprecated, confName)
			continue
		}
		sourceValueObj := valueSource.(api.BaseConfItemResp)
		targetValueObj := valueTarget.(api.BaseConfItemResp)
		if sourceValueObj.LevelName == "module" {
			// 将原 module的自定义配置，同步给新的 module，标记为自定义
			// 这里只是返回给前端，最终需要前端根据自定义的标记，向后端发起保存
			targetValueObj.ConfValue = sourceValueObj.ConfValue
			targetValueObj.LevelName = "module"
			targetValueObj.LevelValue = r.TargetModuleID
			retTarget.Content[confName] = targetValueObj
			confNamesValueModified = append(confNamesValueModified, confName)
		} else if sourceValueObj.ConfValue != targetValueObj.ConfValue {
			// 业务 / 平台级别配置不一致
			confNamesValueSource[confName] = sourceValueObj.ConfValue
			continue
		}
	}

	// 如果 retTarget 里面有 retSource 里面不存在的配置项，说明是目标新增的配置，需要提示
	for confName, _ := range retTarget.Content {
		if _, ok := retSource.Content[confName]; !ok {
			confNamesValueSource[confName] = "_NONE_" // 只在目标存在的配置项，标记为空
		}
	}
	resp := &api.CloneModuleQueryConfigResp{
		GetConfigItemsResp: api.GetConfigItemsResp{
			BKBizID: r.TargetBkBizID,
			BaseLevelDef: api.BaseLevelDef{
				LevelName:  "module",
				LevelValue: r.TargetModuleID,
			},
			Content: retTarget.Content,
		},
		ConfNamesDeprecated:    confNamesDeprecated,
		ConfNamesValueDiff:     confNamesValueSource,
		ConfNamesValueModified: confNamesValueModified,
	}
	return resp, nil
}
