package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"fmt"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// UpsertConfigByUnique TODO
// 同 model.UpsertBatchConfigs()
func UpsertConfigByUnique(configModels []*model.ConfigModel) error {
	configsAdd := make([]*model.ConfigModel, 0)
	configsUpt := make([]*model.ConfigModel, 0)
	for _, c := range configModels {
		if configID, err := c.CheckRecordExists(model.DB.Self); err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				configsAdd = append(configsAdd, c)
			} else {
				return err
			}
		} else {
			c.ID = configID
			configsUpt = append(configsUpt, c)
		}
	}
	logger.Infof("UpsertConfigByUnique configsAdd:%#v, configsUpt:%+v", configsAdd, configsUpt)
	if len(configsAdd) != 0 {
		if err := model.CreateBatch(model.DB.Self, configsAdd); err != nil {
			return err
		}
	}
	if len(configsUpt) != 0 {
		// set ifNotFoundErr=false because we have checked CheckRecordExists
		if err := model.UpdateBatch(model.DB.Self, configsUpt, false); err != nil {
			return err
		}
	}
	return nil
}

// UpsertConfigItems TODO
// 操作 config node，已明确操作类型
// 会首先根据唯一建，获得 id
// @todo 返回影响行数
func UpsertConfigItems(db *gorm.DB, configsOp []*model.ConfigModelOp, revision string) ([]*model.ConfigModel, error) {
	configsLocked := make([]*model.ConfigModel, 0)
	if configsOp == nil || len(configsOp) == 0 {
		return configsLocked, nil
	}
	configsAdd := make([]*model.ConfigModel, 0)
	configsUpt := make([]*model.ConfigModel, 0)
	configsDel := make([]*model.ConfigModel, 0)
	for _, c := range configsOp {
		if id, err := model.RecordExists(db, c.Config.TableName(), c.Config.ID, c.Config.UniqueWhere()); err != nil {
			if !errors.Is(err, gorm.ErrRecordNotFound) {
				return nil, err
			}
		} else {
			c.Config.ID = id
		}
		c.Config.UpdatedRevision = revision
		c.Config.Stage = 1
		if c.OPType == constvar.OPTypeAdd {
			configsAdd = append(configsAdd, c.Config)
		} else if c.OPType == constvar.OPTypeUpdate {
			configsUpt = append(configsUpt, c.Config)
		} else if c.OPType == constvar.OPTypeRemove {
			configsDel = append(configsDel, c.Config)
		} else if c.OPType == constvar.OPTypeRemoveRef {
			configsDel = append(configsDel, c.Config)
		}
		if c.Config.FlagLocked == 1 && c.OPType != constvar.OPTypeRemove {
			configsLocked = append(configsLocked, c.Config)
		}
	}
	logger.Info("configsAdd: %+v  configsUpt: %+v  configsDel: %+v", configsAdd, configsUpt, configsDel)
	if len(configsAdd) != 0 {
		configsAdd = ProcessConfig(configsAdd)
		if err := model.CreateBatch(db, configsAdd); err != nil {
			return nil, err
		}
	}
	if len(configsUpt) != 0 {
		configsUpt = ProcessConfig(configsUpt)
		// 这里应该是一定存在(已经CheckRecordExists)且能update
		// 这里精确点的话，SaveOnly: ifNotFoundErr=true, SaveAndPublish: ifNotFoundErr=false
		if err := model.UpdateBatch(db, configsUpt, false); err != nil {
			return nil, err
		}
	}
	if len(configsDel) != 0 {
		if err := model.DeleteBatch(db, configsDel); err != nil {
			return nil, err
		}
	}
	return configsLocked, nil
}

// UpsertConfig TODO
// update: 如果是update模式，当没找到对应id的记录时会报错；update=false 记录不存在则忽略
// isOverride: 如果是override模式，记录已经存在则根据id update覆盖；false 依然是insert，会报错
func UpsertConfig(configModels []*model.ConfigModel, update, isOverride bool) error {
	configsID0 := make([]*model.ConfigModel, 0)
	configsIDn := make([]*model.ConfigModel, 0)
	for _, c := range configModels {
		if c.ID == 0 {
			configsID0 = append(configsID0, c)
		} else {
			configsIDn = append(configsIDn, c)
		}
	}
	logger.Infof("UpsertConfig configsID0:%#v, configsIDn:%+v", configsID0, configsIDn)
	configsAdd := make([]*model.ConfigModel, 0)
	configsUpt := make([]*model.ConfigModel, 0)
	configsDel := make([]*model.ConfigModel, 0)
	for _, c := range configsID0 {
		if configID, err := c.CheckRecordExists(model.DB.Self); err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				configsAdd = append(configsAdd, c)
			} else {
				return err
			}
		} else {
			c.ID = configID
			if update || isOverride {
				// update: by unique key
				configsUpt = append(configsUpt, c)
			} else {
				// insert: ErrDuplicateKey
				configsAdd = append(configsAdd, c) // will return err
			}
		}
	}
	for _, c := range configsIDn {
		if _, err := c.CheckRecordExists(model.DB.Self); err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				if update {
					return fmt.Errorf("ErrNotFound id=%d", c.ID)
				} else {
					return fmt.Errorf("ErrInsertWithID id=%d", c.ID)
				}
			} else {
				return err
			}
		} else {
			// c.ID = configID
			if c.FlagDisable == -1 {
				configsDel = append(configsDel, c)
			} else {
				configsUpt = append(configsUpt, c)
			}
		}
	}
	logger.Infof("UpsertConfig configsAdd:%#v, configsUpt:%+v, configsDel:%+v",
		configsAdd, configsUpt, configsDel)
	if len(configsAdd) != 0 {
		configsAdd = ProcessConfig(configsAdd)
		if err := model.CreateBatch(model.DB.Self, configsAdd); err != nil {
			return err
		}
	}
	if len(configsUpt) != 0 {
		configsUpt = ProcessConfig(configsUpt)
		// 这里应该是一定存在(已经CheckRecordExists)且能update，如果不存在抛出错误
		if err := model.UpdateBatch(model.DB.Self, configsUpt, true); err != nil {
			return err
		}
	}
	if len(configsDel) != 0 {
		if err := model.DeleteBatch(model.DB.Self, configsDel); err != nil {
			return err
		}
	}
	return nil
}

// GetMergedConfig TODO
func GetMergedConfig(db *gorm.DB, s *api.BaseConfigNode, upLevelInfo *api.UpLevelInfo,
	options *api.QueryConfigOptions) ([]*model.ConfigModel, error) {
	// 获取集群的配置，必须要有上层级模块的信息
	if options.Module == "" && options.Cluster != "" {
		// we get module from backend
		if res, err := model.GetModuleByCluster(s.BKBizID, options.Cluster); err != nil {
			// module = ""
		} else if len(res) >= 1 {
			options.Module = res[0].Module
		}
	}
	// 目前这 3 个级别需要 up level_info 信息
	if s.LevelName == constvar.LevelCluster || s.LevelName == constvar.LevelInstance || s.LevelName == constvar.LevelHost {
		if len(upLevelInfo.LevelInfo) == 0 {
			// todo 这里只尝试获取直接上级
			if levelInfo, err := model.QueryParentLevelValue(s); err == nil {
				upLevelInfo.LevelInfo = util.MapMerge(upLevelInfo.LevelInfo, levelInfo)
			} else {
				return nil, err
			}
		}
	}

	configs, err := model.GetSimpleConfig(db, s, upLevelInfo, options)
	if err != nil {
		return nil, err
	}
	if configs, err = MergeConfig(configs, options.View); err != nil {
		return nil, err
	} else {
		configs = ProcessConfig(configs)
	}
	return configs, nil
}

// ConfigLevels TODO
type ConfigLevels map[string][]*model.ConfigModel

// ConfigTypeLevel TODO
type ConfigTypeLevel map[string]ConfigLevels

// NewBaseConfItemWithModel TODO
func NewBaseConfItemWithModel(c *model.ConfigModel, opType string) interface{} {
	baseItem := api.BaseConfItemResp{
		BaseConfItemDef: api.BaseConfItemDef{
			ConfName:    c.ConfName,
			ConfValue:   c.ConfValue,
			FlagLocked:  c.FlagLocked,
			FlagDisable: c.FlagDisable,
			// Description: c.Description,
			Stage: c.Stage,
		},
		BaseLevelDef: api.BaseLevelDef{
			LevelName:  c.LevelName,
			LevelValue: c.LevelValue,
		},
	}
	if opType != "" {
		baseItem.OPType = opType
	}
	return baseItem
}

// NewBaseConfItemWithModels TODO
func NewBaseConfItemWithModels(configs []*model.ConfigModel) map[string]interface{} {
	confItems := make(map[string]interface{}, len(configs))
	for _, c := range configs {
		confItems[c.ConfName] = NewBaseConfItemWithModel(c, "")
	}
	return confItems
}

func getLevelNameFromMap(levels api.UpLevelInfo) {

}

// NewConfigModelsWithItemReq TODO
// 转换更新请求，为实际的 config model
func NewConfigModelsWithItemReq(r *api.UpsertConfItemsReq) ([]*model.ConfigModelView, []*model.ConfigModelOp) {
	configs := make([]*model.ConfigModelView, 0)
	configsDiff := make([]*model.ConfigModelOp, 0)
	for _, cn := range r.ConfItems {
		confItem := &model.ConfigModelView{
			ConfigModel: model.ConfigModel{
				BKBizID:     r.BKBizID,
				Namespace:   r.ConfFileInfo.Namespace,
				ConfType:    r.ConfFileInfo.ConfType,
				ConfFile:    r.ConfFileInfo.ConfFile,
				ConfName:    cn.ConfName,
				ConfValue:   cn.ConfValue,
				LevelName:   r.LevelName,
				LevelValue:  r.LevelValue,
				FlagDisable: cn.FlagDisable,
				FlagLocked:  cn.FlagLocked,
				// LevelLocked: GetConfigLockLevel(cn.FlagLocked, constvar.LevelPlat),
				Description: cn.Description,
			},
			UpLevelInfo: r.UpLevelInfo.LevelInfo,
			// Module: r.UpLevelInfo.GetLevelValue(constvar.LevelModule),
		}
		configs = append(configs, confItem)
		COP := &model.ConfigModelOp{
			Config: &confItem.ConfigModel,
			OPType: cn.OPType,
		}
		configsDiff = append(configsDiff, COP)
	}
	return configs, configsDiff
}

// UpdateConfigFileItems 修改配置
func UpdateConfigFileItems(r *api.UpsertConfItemsReq, opUser string) (*api.UpsertConfItemsResp, error) {
	fileDef := r.ConfFileInfo.BaseConfFileDef
	exists, cf, err := checkConfigFileExists(&fileDef)
	defer util.LoggerErrorStack(logger.Error, err)
	if err != nil {
		return nil, err
	}
	if !exists {
		// return nil, fmt.Errorf("conf_file %s for %s does not exists with level_name=%s,level_value=%s", cf.ConfFile, cf.Namespace, r.LevelName, r.LevelValue)
	}
	resp := &api.UpsertConfItemsResp{
		BKBizID:         r.BKBizID,
		BaseConfFileDef: fileDef,
	}
	configs, configsDiff := NewConfigModelsWithItemReq(r)
	// 先判断上层级是否安全, 强制约束，confirm=1 无效
	configsRef, err := BatchPreCheck(configs)
	if err != nil {
		return nil, err
	}

	configsRefDiff := AddConfigsRefToDiff(configsRef)
	configsDiff = append(configsDiff, configsRefDiff...)

	// 存在下层级配置与当前配置冲突，confirm=1 确认修改
	if len(configsRefDiff) > 0 && r.Confirm == 0 {
		names := []string{}
		for _, conf := range configsRefDiff {
			names = append(names, conf.Config.ConfName)
		}
		return nil, errors.WithMessagef(errno.ErrConflictWithLowerConfigLevel, "%v", names)
	}
	txErr := model.DB.Self.Transaction(func(tx *gorm.DB) error {
		// 保存到 to tb_config_file_node
		levelNode := api.BaseConfigNode{}
		levelNode.Set(r.BKBizID, cf.Namespace, cf.ConfType, cf.ConfFile, r.LevelName, r.LevelValue)

		confFileLC := r.ConfFileInfo.ConfFileLC
		if confFileLC == "" {
			confFileLC = cf.ConfFileLC
		}
		if err = SaveConfigFileNode(tx, &levelNode, opUser, r.ConfFileInfo.Description, confFileLC); err != nil {
			return err
		}

		if len(configs) == 0 { // 如果 items 为空，只修改 conf_file 信息
			return nil
		}
		publishReq := &api.SimpleConfigQueryReq{
			BaseConfigNode: levelNode,
			InheritFrom:    "0",
			View:           fmt.Sprintf("merge.%s", r.LevelName),
			Format:         constvar.FormatMap,
			Description:    r.Description, // 发布描述
			Revision:       r.Revision,
			CreatedBy:      opUser,
			UpLevelInfo:    r.UpLevelInfo,
		}
		publishReq.Decrypt = false
		if err = publishReq.Validate(); err != nil {
			return err
		}
		if r.ReqType == constvar.MethodSaveOnly {
			if !checkVersionable(r.ConfFileInfo.Namespace, r.ConfFileInfo.ConfType) {
				return errors.WithMessagef(errno.ErrUnversionable, "%s,%s", fileDef.Namespace, fileDef.ConfType)
			}
			// 保存到 tb_config_versioned
			if v, err := GenerateConfigFile(tx, publishReq, constvar.MethodGenAndSave, configsDiff); err != nil {
				return err
			} else {
				resp.Revision = v.Revision
				resp.IsPublished = 0
			}
		} else if r.ReqType == constvar.MethodSaveAndPublish {
			if !checkVersionable(r.ConfFileInfo.Namespace, r.ConfFileInfo.ConfType) {
				return errors.WithMessagef(errno.ErrUnversionable, "%s,%s", fileDef.Namespace, fileDef.ConfType)
			}
			/*
			   // confirm 处理下层级冲突 tb_config_node
			   if err := ProcessOPConfig(opConfigs); err != nil {
			       return err
			   }
			*/
			// 保存到 tb_config_versioned
			// 保存到 tb_config_node
			if v, err := GenerateConfigFile(tx, publishReq, constvar.MethodGenAndPublish, configsDiff); err != nil {
				return err
			} else {
				resp.Revision = v.Revision
				resp.IsPublished = 1
			}
		} else if r.ReqType == constvar.MethodSave {
			if checkVersionable(r.ConfFileInfo.Namespace, r.ConfFileInfo.ConfType) {
				return errno.ErrVersionable
			}
			if _, err := UpsertConfigItems(tx, configsDiff, ""); err != nil {
				return err
			}
			resp.IsPublished = 1
		}
		return nil
	})
	if txErr == nil {
		model.CacheSetAndGetConfigFile(fileDef) // refresh cache
	}
	return resp, txErr
}

// QueryConfigItems godoc
// 如果是 entity level, 则查询 tb_config_versioned 返回
// 如果是 template level, 则查询 tb_config_node 合并
// queryFileInfo 选项控制是否查询 conf_file 信息。一般对 web 页面需要 info，对接后端 api 不需要 info
func QueryConfigItems(r *api.SimpleConfigQueryReq, queryFileInfo bool) (*api.GetConfigItemsResp, error) {
	resp := &api.GetConfigItemsResp{
		BKBizID: r.BKBizID,
		BaseLevelDef: api.BaseLevelDef{
			LevelName:  r.LevelName,
			LevelValue: r.LevelValue,
		},
	}
	r.Decrypt = true
	if model.IsConfigLevelEntityVersioned(r.Namespace, r.ConfType, r.ConfFile, r.LevelName) {
		if ret, err := QueryConfigItemsFromVersion(r, true); err != nil {
			return nil, err
		} else {
			resp.Content = ret.Content
		}
	} else {
		// 查询合并 nodeLevel
		ret, err := GenerateConfigFile(model.DB.Self, r, constvar.MethodGenerateOnly, nil)
		if err != nil {
			return nil, err
		}
		resp.Content = ret.Content
	}
	if queryFileInfo {
		cf, err := GetConfigFileSimpleInfo(&r.BaseConfigNode)
		if err != nil {
			return nil, err
		}
		resp.ConfFileResp = *cf
	}
	return resp, nil
}

// QueryConfigItemsFromVersion 直接查询已发布的配置
// hasApplied 表示必须要求已经 applied 过的，才能获取它的 published 。applied 表示曾经 generate 过
func QueryConfigItemsFromVersion(r *api.SimpleConfigQueryReq, hasApplied bool) (*api.GenerateConfigResp, error) {
	v := model.ConfigVersionedModel{
		BKBizID:    r.BKBizID,
		Namespace:  r.Namespace,
		ConfType:   r.ConfType,
		ConfFile:   r.ConfFile,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
	}
	if hasApplied {
		if _, err := v.ExistsAppliedVersion(model.DB.Self); err != nil {
			return nil, errors.WithMessage(err, "get published config need applied")
		}
	}
	if vConfigs, err := v.GetVersionPublished(model.DB.Self); err != nil {
		// 没有找到也会返回错误
		return nil, err
	} else {
		if resp, err := FormatConfigFileForResp(r, vConfigs.Configs); err != nil {
			return nil, err
		} else {
			return resp, nil
		}
	}
}

// GetConfigItemsForFiles godoc
// 查询多个配置文件
func GetConfigItemsForFiles(r *api.SimpleConfigQueryReq, confFiles []string) ([]*api.GetConfigItemsResp, error) {
	resp := make([]*api.GetConfigItemsResp, 0)
	for _, f := range confFiles {
		r.ConfFile = f
		if ret, err := QueryConfigItems(r, true); err != nil {
			return nil, err
		} else {
			resp = append(resp, ret)
		}
	}
	return resp, nil
}

// ProcessConfigsDiff 把 configsDiff 变更到 configs 上
func ProcessConfigsDiff(configs []*model.ConfigModel, configsDiff []*model.ConfigModelOp) ([]*model.ConfigModel, int,
	error) {
	if len(configsDiff) == 0 {
		return configs, 0, nil
	}
	configsNew := make(map[string]*model.ConfigModel, 0)
	for _, c := range configs {
		if _, ok := configsNew[c.ConfName]; ok {
			return nil, 0, errors.WithMessagef(errno.ErrDuplicateItem, "conf_name=%s", c.ConfName)
		}
		configsNew[c.ConfName] = c
	}
	affectedRows := 0
	// logger.Info("ProcessConfigsDiff configs=%+v   configsDiff=%+v", configs, configsDiff)
	for _, c := range configsDiff {
		affectedRows += 1
		confName := c.Config.ConfName
		optype := c.OPType
		if optype == constvar.OPTypeAdd {
			if _, ok := configsNew[confName]; ok {
				if configsNew[confName].LevelName == c.Config.LevelName {
					return nil, 0, errors.WithMessagef(errno.ErrDuplicateItem, "conf_name=%s", confName)
				}
				configsNew[confName] = c.Config
			}
			configsNew[confName] = c.Config
		} else if optype == constvar.OPTypeRemove {
			delete(configsNew, confName)
		} else if optype == constvar.OPTypeUpdate {
			configsNew[confName] = c.Config
		} else if optype == constvar.OPTypeRemoveRef {
			// remove_ref 是修改导致的关联删除，一般是当前修改层级的下级配置冲突，不会出现在当前层级的配置信息里
			affectedRows -= 1
		}
	}
	configsProcessed := make([]*model.ConfigModel, 0, len(configsNew))
	for _, c := range configsNew {
		configsProcessed = append(configsProcessed, c)
	}
	return configsProcessed, affectedRows, nil
}

// GenerateConfigFile TODO
// call GetConfig, FormatAndSaveConfigFile
func GenerateConfigFile(db *gorm.DB, r *api.SimpleConfigQueryReq,
	method string, configsDiff []*model.ConfigModelOp) (*api.GenerateConfigResp, error) {
	// query
	var options = api.QueryConfigOptions{}
	if err := copier.Copy(&options, r); err != nil {
		return nil, err
	}
	configs, err := GetMergedConfig(db, &r.BaseConfigNode, &r.UpLevelInfo, &options) // @TODO use transaction
	if err != nil {
		return nil, err
	}
	var m = model.ConfigVersionedModel{
		BKBizID:    r.BKBizID,
		Namespace:  r.Namespace,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
		ConfType:   r.ConfType,
		ConfFile:   r.ConfFile,

		Description: r.Description,
		Module:      r.Module,
		Cluster:     r.Cluster,
		CreatedBy:   r.CreatedBy,
	}
	// todo 根据前端输入，当前已发布版本的snapshot + 变更的diffs，生成新的 configs
	// 是否改成直接根据后端 published 来判断影响行数？
	configsNew, affected, err := ProcessConfigsDiff(configs, configsDiff)
	if err != nil {
		return nil, err
	}
	m.RowsAffected = affected
	options.RowsAffected = affected

	if r.Revision == "" {
		r.Revision = m.NewRevisionName() // m.Revision
	}
	// @TODO 需要启用事务
	if method == constvar.MethodGenAndPublish { // release: save and publish
		if err := GenerateAndPublish(db, &r.BaseConfigNode, &options, &r.UpLevelInfo, r.Revision, configsDiff); err != nil {
			return nil, err
		}
	} else if method == constvar.MethodGenAndSave { // save
		if _, err = m.FormatAndSaveConfigVersioned(db, configsNew, configsDiff); err != nil {
			return nil, err
		}
	} else if method == constvar.MethodGenerateOnly {
		r.Revision = ""
	} else {
		err = fmt.Errorf("illegal param method: %s", method)
		return nil, err
	}
	// response
	resp, err := FormatConfigFileForResp(r, configsNew)
	if err != nil {
		return nil, err
	} else {
		resp.Revision = r.Revision
	}
	return resp, nil
}

// SaveConfigFileNode upsert
func SaveConfigFileNode(db *gorm.DB, r *api.BaseConfigNode, opUser, description, confFileLC string) error {
	configFile := &model.ConfigFileNodeModel{
		BKBizID:     r.BKBizID,
		Namespace:   r.Namespace,
		ConfType:    r.ConfType,
		ConfFile:    r.ConfFile,
		LevelName:   r.LevelName,
		LevelValue:  r.LevelValue,
		UpdatedBy:   opUser,
		ConfFileLC:  confFileLC,
		Description: description,
	}
	if _, err := configFile.CreateOrUpdate(false, db); err != nil {
		return err
	}
	return nil
}

// GenerateAndPublish todo revision 可以去掉
func GenerateAndPublish(db *gorm.DB, r *api.BaseConfigNode, o *api.QueryConfigOptions, up *api.UpLevelInfo,
	revision string, configsDiff []*model.ConfigModelOp) (err error) {
	if revision == "" {
		return errors.New("revision should not be empty")
	}
	var m = model.ConfigVersionedModel{}
	copier.Copy(&m, r)
	m.CreatedBy = o.CreatedBy
	m.Description = o.Description
	m.RowsAffected = o.RowsAffected
	if val, ok := up.LevelInfo[constvar.LevelModule]; ok {
		m.Module = val
	} else {
		m.Module = o.Module
	}
	if val, ok := up.LevelInfo[constvar.LevelCluster]; ok {
		m.Cluster = val
	} else if r.LevelName == constvar.LevelCluster {
		m.Cluster = r.LevelValue
	}
	// copier.Copy(&m, o)
	txErr := db.Transaction(func(tx *gorm.DB) error { // new transaction
		// 回写 tb_config_node 保存到层级树
		configsLocked, err := UpsertConfigItems(tx, configsDiff, revision)
		if err != nil {
			return err
		}

		// 重新基于最新的 tb_config_node 生成 merged_configs
		configs, err := GetMergedConfig(tx, r, up, o)
		if err != nil {
			return err
		}
		// 保存新版本到 tb_config_versioned
		if _, err = m.FormatAndSaveConfigVersioned(tx, configs, configsDiff); err != nil {
			return err
		}
		// logger.Info("GenerateConfigFile ConfigVersionedModel=%+v", m)
		publish := PublishConfig{
			Versioned:     &m,
			ConfigsLocked: configsLocked,
			Patch:         nil,
			FromGenerated: o.Generate,
			Revision:      revision,
		}
		if err = publish.PublishAndApplyVersioned(tx, o.FromNodeConfigApplied); err != nil {
			return err
		}
		return nil
	})
	if txErr != nil {
		return txErr
	}
	return txErr
}
