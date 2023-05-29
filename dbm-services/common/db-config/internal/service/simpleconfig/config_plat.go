package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"fmt"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// ConfigNamesBatchUpsert TODO
func ConfigNamesBatchUpsert(db *gorm.DB, cf api.ConfFileDef, confNames []*api.UpsertConfNames) error {
	adds := make([]*model.ConfigNameDefModel, 0)
	updates := make([]*model.ConfigNameDefModel, 0)
	deletes := make([]*model.ConfigNameDefModel, 0)

	// 目前只允许 update 这几个属性 "value_default", "value_allowed", "flag_status", "flag_locked"，见 ConfigNamesBatchUpdate
	for _, cn := range confNames {
		confName := &model.ConfigNameDefModel{
			Namespace:    cf.Namespace,
			ConfType:     cf.ConfType,
			ConfFile:     cf.ConfFile,
			ConfName:     cn.ConfName,
			ConfNameLC:   cn.ConfNameLC,
			ValueAllowed: cn.ValueAllowed,
			ValueDefault: cn.ValueDefault,
			ValueType:    cn.ValueType,
			FlagDisable:  cn.FlagDisable,
			FlagLocked:   cn.FlagLocked,
			NeedRestart:  cn.NeedRestart,
			Description:  cn.Description,
			FlagStatus:   cn.FlagStatus, // 只读属性，允许 api去修改，不允许页面修改
			Stage:        1,
		}
		// platConfig = append(platConfig, confName)

		if cn.OPType == constvar.OPTypeAdd {
			adds = append(adds, confName)
		} else if cn.OPType == constvar.OPTypeUpdate {
			updates = append(updates, confName)
		} else if cn.OPType == constvar.OPTypeRemove {
			deletes = append(deletes, confName)
		}
	}
	err := db.Transaction(func(tx *gorm.DB) error {
		if len(adds) > 0 {
			if err := model.ConfigNamesBatchSave(tx, adds); err != nil {
				return err
			}
		}
		if len(updates) > 0 {
			if err := model.ConfigNamesBatchSave(tx, updates); err != nil {
				return err
			}
		}
		if len(deletes) > 0 {
			if err := model.ConfigNamesBatchDelete(tx, deletes); err != nil {
				return err
			}
		}
		return nil
	})
	return err
}

// UpsertConfigFilePlat TODO
// 添加平台配置
// 如果 conf_file 已经存在，则报错
// 新建 conf_file，保存操作在 def 表，发布时进入 node 表，生成revision并发布
func UpsertConfigFilePlat(r *api.UpsertConfFilePlatReq, clientOPType, opUser string) (*api.UpsertConfFilePlatResp,
	error) {
	fileDef := r.ConfFileInfo.BaseConfFileDef
	exists, cf, err := checkConfigFileExists(&fileDef)
	if err != nil {
		return nil, err
	} else {
		cf.Description = r.ConfFileInfo.Description // 文件描述
		cf.ConfTypeLC = r.ConfFileInfo.ConfTypeLC
		cf.ConfFileLC = r.ConfFileInfo.ConfFileLC
		cf.UpdatedBy = opUser
	}
	logger.Info("UpsertConfigFilePlat conf_file info %+v", cf)
	if exists && r.FileID == 0 {
		if clientOPType == "new" {
			return nil, fmt.Errorf("conf_file %s for %s already exists with id=%d",
				cf.ConfFile, cf.Namespace, cf.ID)
		} else { // edit
		}
	}
	resp := &api.UpsertConfFilePlatResp{
		BaseConfFileDef: fileDef,
	}
	// build config item model
	configs, configsDiff := NewConfigModels(r)
	// 平台配置永远可以修改，如果与下级存在锁冲突，后面会生成修复提示
	configsRef, err := BatchPreCheckPlat(r, configs)
	if err != nil {
		return nil, err
	}

	// configsDiff 是用于操作db的差异部分
	// configsRef 是展示给前端的差异部分
	configsRefDiff := AddConfigsRefToDiff(configsRef)
	configsDiff = append(configsDiff, configsRefDiff...)
	logger.Info("UpsertConfigFilePlat configsRefDiff=%+v", configsRefDiff)
	// 存在下层级配置与当前配置冲突，confirm=1 确认修改
	if len(configsRefDiff) > 0 && r.Confirm == 0 {
		names := []string{}
		for _, conf := range configsRefDiff {
			names = append(names, conf.Config.ConfName)
		}
		return nil, errors.WithMessagef(errno.ErrConflictWithLowerConfigLevel, "%v", names)
	}

	txErr := model.DB.Self.Transaction(func(tx *gorm.DB) error {
		// 保存逻辑
		{
			// 保存到 tb_config_file_def
			if fileID, err := cf.SaveAndGetID(tx); err != nil {
				return err
			} else {
				resp.FileID = fileID
				cf.ID = fileID
			}
			if len(configs) == 0 { // 如果 items 为空，只修改 conf_file 信息
				return nil
			}
			/*
			   // confirm 处理下层级冲突 tb_config_node
			   if err := ProcessOPConfig(configsRef); err != nil {
			       return err
			   }

			*/
			// 保存到 tb_config_name_def
			// @todo 这里保存到 tb_config_name_def 就意味着发布了，与 tb_config_versioned 不一致
			if err := ConfigNamesBatchUpsert(tx, r.ConfFileInfo, r.ConfNames); err != nil {
				return err
			}
			resp.IsPublished = 0
		}
		// 发布逻辑
		if r.ReqType == constvar.MethodSaveAndPublish {
			if !checkVersionable(r.ConfFileInfo.Namespace, r.ConfFileInfo.ConfType) {
				resp.IsPublished = 1
				return nil
			}
			// 保存到 tb_config_node
			levelNode := api.BaseConfigNode{}
			levelNode.Set(constvar.BKBizIDForPlat, fileDef.Namespace, fileDef.ConfType, fileDef.ConfFile, constvar.LevelPlat,
				constvar.BKBizIDForPlat)
			publishReq := &api.SimpleConfigQueryReq{
				BaseConfigNode: levelNode,
				InheritFrom:    "",
				View:           constvar.ViewRaw, // plat不存在合并的问题
				Description:    r.Description,    // 发布描述
				Format:         constvar.FormatList,
				CreatedBy:      opUser,
			}
			publishReq.Decrypt = false
			// todo 从 tb_config_node 移除 flag_status = -1 的平台配置

			// 保存到 tb_config_versioned, 增量回写 tb_config_node
			if v, err := GenerateConfigFile(tx, publishReq, constvar.MethodGenAndPublish, configsDiff); err != nil {
				return err
			} else {
				resp.Revision = v.Revision
				resp.IsPublished = 1
			}
		}
		return nil
	})
	if txErr == nil {
		model.CacheSetAndGetConfigFile(fileDef)
	}
	return resp, txErr
}
