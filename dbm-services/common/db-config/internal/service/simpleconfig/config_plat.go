package simpleconfig

import (
	"errors"
	"fmt"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"

	"github.com/jinzhu/copier"
	"gorm.io/gorm"
)

// ConfigNamesBatchUpsert TODO
func ConfigNamesBatchUpsert(db *gorm.DB, cf api.BaseConfFileDef,
	confNames []*api.UpsertConfNames, opUser string, table string) error {
	adds := make([]*model.ConfigNameDefModel, 0)
	updates := make([]*model.ConfigNameDefModel, 0)
	deletes := make([]*model.ConfigNameDefModel, 0)
	upserts := make([]*model.ConfigNameDefModel, 0)

	// 修改 readonly=1 或者删除操作，需要检查配置项是否有被使用
	var needCheckInherit []string

	// 目前只允许 update 这几个属性 "value_default", "value_allowed", "flag_status", "flag_locked"，
	// 见 ConfigNamesBatchUpdate

	for _, cn := range confNames {
		confName := &model.ConfigNameDefModel{}
		_ = copier.Copy(confName, cn.ConfNameDef)
		confName.Namespace = cf.Namespace
		confName.ConfType = cf.ConfType
		confName.ConfFile = cf.ConfFile

		if cn.OPType == constvar.OPTypeAdd {
			adds = append(adds, confName)
		} else if cn.OPType == constvar.OPTypeUpdate {
			updates = append(updates, confName)
			if cn.FlagReadonly == 1 {
				needCheckInherit = append(needCheckInherit, cn.ConfName)
			}
		} else if cn.OPType == constvar.OPTypeRemove {
			deletes = append(deletes, confName)
			needCheckInherit = append(needCheckInherit, cn.ConfName)
		} else if cn.OPType == constvar.OPTypeUpsert {
			upserts = append(upserts, confName)
			if cn.FlagReadonly == 1 {
				needCheckInherit = append(needCheckInherit, cn.ConfName)
			}
		} else {
			return fmt.Errorf("invalid op_type %s for %s", cn.OPType, cn.ConfName)
		}
	}
	if len(needCheckInherit) > 0 {
		configNodes, err := CheckConfigInherit(db, cf, needCheckInherit)
		if err != nil {
			return err
		}
		var errsMsg error
		var idList []uint64
		for _, cn := range configNodes {
			errMsg := fmt.Errorf("%s(=%s) is used by %s=%s (bk_biz_id=%s)",
				cn.ConfName, cn.ConfValue, cn.LevelName, cn.LevelValue, cn.BKBizID)
			errsMsg = errors.Join(errsMsg, errMsg)
			idList = append(idList, cn.ID)
		}
		if errsMsg != nil {
			return errors.Join(errsMsg, fmt.Errorf("\nid list %v", idList))
		}
	}
	err := db.Transaction(func(tx *gorm.DB) error {
		if len(adds) > 0 {
			namesAdd := model.ConfNameOperation{
				ConfNames: adds,
				OpUser:    opUser,
				Table:     table,
			}
			if err := namesAdd.BatchCreate(tx, adds); err != nil {
				return err
			}
		}
		if len(updates) > 0 {
			namesUpdate := model.ConfNameOperation{
				ConfNames: updates,
				OpUser:    opUser,
				Table:     table,
			}
			if err := namesUpdate.BatchUpdate(tx, updates); err != nil {
				return err
			}
		}
		if len(deletes) > 0 {
			namesDelete := model.ConfNameOperation{
				ConfNames: deletes,
				OpUser:    opUser,
				Table:     table,
			}
			if err := namesDelete.BatchDelete(tx, deletes); err != nil {
				return err
			}
		}
		if len(upserts) > 0 {
			namesUpsert := model.ConfNameOperation{
				ConfNames: upserts,
				OpUser:    opUser,
				Table:     table,
			}
			if err := namesUpsert.BatchSave(tx, upserts); err != nil {
				return err
			}
		}
		return nil
	})
	return err
}

func CheckConfigInherit(db *gorm.DB, cf api.BaseConfFileDef,
	confNames []string) (configNodes []model.ConfigModel, err error) {
	//var configNodes []model.ConfigModel
	err = db.Model(&model.ConfigModel{}).Where("namespace = ? AND conf_type = ? AND conf_file = ? "+
		"AND conf_name IN ?",
		cf.Namespace, cf.ConfType, cf.ConfFile, confNames).Find(&configNodes).Error
	if err != nil {
		return nil, err
	}
	return configNodes, nil
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
			if err := ConfigNamesBatchUpsert(tx, fileDef, r.ConfNames, opUser, "plat"); err != nil {
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
