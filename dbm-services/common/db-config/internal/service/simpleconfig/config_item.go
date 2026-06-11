package simpleconfig

import (
	"fmt"
	"time"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"

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
func UpsertConfigItems(db *gorm.DB, configsOp []*model.ConfigModelOp, revision string,
	opUser string, upLevel *api.UpLevelInfo) ([]*model.ConfigModel, error) {
	configsLocked := make([]*model.ConfigModel, 0)
	if configsOp == nil || len(configsOp) == 0 {
		return configsLocked, nil
	}
	configsAdd := make([]*model.ConfigModel, 0)
	configsUpt := make([]*model.ConfigModel, 0)
	configsDel := make([]*model.ConfigModel, 0)
	// 记录 update/delete 操作的 before_image，需要在实际操作前查询
	beforeImages := make(map[string]api.ConfItem, 0)
	//upLevelConfValues := make(map[string]string, 0)
	type UpLevelConfItem map[string]string
	upLevelConfItems := make(map[string]UpLevelConfItem, 0)
	configNamesDef := make(map[string]*model.ConfigNameDefModel, 0)
	for _, c := range configsOp {
		if c.OPType == constvar.OPTypeRemoveRef || c.OPType == constvar.OPTypeRemove {
			// remove 不检验 平台值是否存在
		} else if id, err := model.RecordExists(db, c.Config.TableName(), c.Config.ID, c.Config.UniqueWhere()); err != nil {
			if !errors.Is(err, gorm.ErrRecordNotFound) {
				return nil, err
			}
		} else {
			c.Config.ID = id
		}
		// 对 update/remove 操作，提前查询 before_image
		if c.OPType == constvar.OPTypeUpdate || c.OPType == constvar.OPTypeRemove || c.OPType == constvar.OPTypeRemoveRef {
			var before model.ConfigModel
			baseInfo := api.BaseConfigNode{
				BKBizID: c.Config.BKBizID,
				BaseConfFileDef: api.BaseConfFileDef{
					Namespace: c.Config.Namespace,
					ConfType:  c.Config.ConfType,
					ConfFile:  c.Config.ConfFile,
				},
				BaseLevelDef: api.BaseLevelDef{
					LevelName:  c.Config.LevelName,
					LevelValue: c.Config.LevelValue,
				},
			}
			baseOptions := api.QueryConfigOptions{
				ConfName: c.Config.ConfName,
				View:     "merge",
			}
			// beforeModels 重新获取当前的值
			beforeModels, namesDef, err := GetMergedConfig(db, &baseInfo, upLevel, &baseOptions)
			if err != nil {
				return nil, err
			}
			if len(beforeModels) > 1 {
				return nil, fmt.Errorf("beforeModels len:%d != 1: %+v", len(beforeModels), beforeModels)
			} else if len(beforeModels) == 0 {
				beforeImages[c.Config.ConfName] = api.ConfItem{}
			} else {
				configNamesDef[c.Config.ConfName] = namesDef[c.Config.ConfName]
				before = *beforeModels[0]
				beforeImages[c.Config.ConfName] = model.NewConfItemFromModel(&before)
				if before.UpLevelValue != nil {
					// 这里给 recover 操作，也记录恢复默认后的 新值。recover 操作是删除当前级别的旧值
					upLevelConfItems[c.Config.ConfName] = before.UpLevelValue
				}
			}
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
	// 记录变更历史
	changes := make([]*model.ConfItemChangesModel, 0, len(configsOp))
	for _, c := range configsOp {
		if c.OPType == constvar.OPTypeRemoveRef {
			// remove_ref 是关联删除，不单独记录
			continue
		}
		beforeImage := beforeImages[c.Config.ConfName]
		afterImage := api.ConfItem{}
		if c.OPType != constvar.OPTypeRemove {
			afterImage = model.NewConfItemFromModel(c.Config)
		} else {
			flagVisible := configNamesDef[c.Config.ConfName].FlagVisible
			if len(upLevelConfItems[c.Config.ConfName]) == 0 && flagVisible == 0 {
				c.OPType = "cancel_render"
			} else {
				c.OPType = "recover" // recoverdefault
			}
			afterImage.ConfValue = upLevelConfItems[c.Config.ConfName]["conf_value"]
		}
		changes = append(changes, &model.ConfItemChangesModel{
			BKBizID:     c.Config.BKBizID,
			Namespace:   c.Config.Namespace,
			ConfType:    c.Config.ConfType,
			ConfFile:    c.Config.ConfFile,
			ConfName:    c.Config.ConfName,
			LevelName:   c.Config.LevelName,
			LevelValue:  c.Config.LevelValue,
			BeforeImage: beforeImage,
			AfterImage:  afterImage,
			OpUser:      opUser,
			OpType:      c.OPType,
		})
	}
	if err := model.ConfItemChangesCreate(db, changes); err != nil {
		return nil, err
	}
	return configsLocked, nil
}

func getParentLevelValue(s *api.BaseConfigNode) (map[string]string, error) {
	levelValue := make(map[string]string)
	if s.LevelName == constvar.LevelCluster {
		levelValue[constvar.LevelModule] = s.LevelValue
	} else {
		levelValue[constvar.LevelApp] = s.BKBizID
	}
	return levelValue, nil
}

func QueryParentLevelName(fileDef api.BaseConfFileDef, levelName string) (string, error) {
	confFileDef, err := model.CacheGetConfigFile(fileDef)
	if err != nil {
		return "", err
	}
	upLevelNames := model.GetConfigLevelsUp(levelName, confFileDef.LevelNameList, true)
	return upLevelNames[0], nil
}

// GetMergedConfig TODO
func GetMergedConfig(db *gorm.DB, s *api.BaseConfigNode, upLevelInfo *api.UpLevelInfo,
	options *api.QueryConfigOptions) ([]*model.ConfigModel, map[string]*model.ConfigNameDefModel, error) {
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
				return nil, nil, err
			}
		}
	}

	configs, confNames, err := model.GetSimpleConfig(db, s, upLevelInfo, options)
	if err != nil {
		return nil, nil, err
	}
	confNamesDef := removeConfigsPlat(confNames, nil)

	if s.LevelName != constvar.LevelPlat {
		upConfigs, _ := MergeConfigLevelUp(configs, s.LevelName, options.View)
		confMap := make(map[string]*model.ConfigModel)
		for _, cg := range upConfigs {
			confMap[cg.ConfName] = cg
		}
		for _, cg := range configs {
			if cg.LevelName == s.LevelName { // 是自定义的配置，返回它的上级配置
				if upConfig, ok := confMap[cg.ConfName]; ok {
					cg.UpLevelValue = map[string]string{
						"level_name":  upConfig.LevelName,
						"level_value": upConfig.LevelValue,
						"conf_value":  upConfig.ConfValue,
					}
				} else {
					logger.Error("NO UP LEVEL FOUND: conf_name=%s (%s=%s)",
						cg.ConfName, cg.LevelName, cg.LevelValue)
					//cg.UpLevelValue = make(map[string]string)
				}
			}
		}
	}

	if configs, err = MergeConfig(configs, options.View); err != nil {
		return nil, nil, err
	} else {
		configs = ProcessConfig(configs)
	}
	return configs, confNamesDef, nil
}

// removeConfigsPlat filter and convert confNames
// if configs is nil, return all
func removeConfigsPlat(allPlat []*model.ConfigNameDefModel,
	configs []*model.ConfigModel) map[string]*model.ConfigNameDefModel {
	var newPlat = make(map[string]*model.ConfigNameDefModel, 0)
	if len(configs) == 0 {
		for _, plat := range allPlat {
			newPlat[plat.ConfName] = plat
		}
		return newPlat
	}
	for _, config := range configs {
		for _, plat := range allPlat {
			if config.ConfName == plat.ConfName {
				newPlat[config.ConfName] = plat
			}
		}
	}
	return newPlat
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
		},
		BaseLevelDef: api.BaseLevelDef{
			LevelName:  c.LevelName,
			LevelValue: c.LevelValue,
		},
		UpLevelValue: c.UpLevelValue,
	}
	if opType != "" {
		baseItem.OPType = opType
	}
	return baseItem
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
		if _, err := UpsertConfigItems(tx, configsDiff, "", opUser, &r.UpLevelInfo); err != nil {
			return err
		}
		resp.IsPublished = 1
		return nil
	})
	if txErr == nil {
		model.CacheSetAndGetConfigFile(fileDef) // refresh cache
	}
	return resp, txErr
}

// QueryConfigItems godoc
// queryFileInfo 选项控制是否查询 conf_file 信息。一般对 web 页面需要 info，对接后端 api 不需要 info
func QueryConfigItems(r *api.SimpleConfigQueryReq, queryFileInfo bool) (*api.GetConfigItemsResp, error) {
	resp := &api.GetConfigItemsResp{
		BKBizID: r.BKBizID,
		BaseLevelDef: api.BaseLevelDef{
			LevelName:  r.LevelName,
			LevelValue: r.LevelValue,
		},
		ConfFile: r.BaseConfigNode.BaseConfFileDef.ConfFile,
	}
	r.Decrypt = true
	// 查询合并 nodeLevel
	ret, err := GenerateConfigFile(model.DB.Self, r, constvar.MethodGenerateOnly, nil)
	if err != nil {
		return nil, err
	}
	resp.Content = ret.Content
	if queryFileInfo {
		cf, err := GetConfigFileSimpleInfo(&r.BaseConfigNode)
		if err != nil {
			return nil, err
		}
		resp.ConfFileResp = *cf
	}
	return resp, nil
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

func QueryConfig(db *gorm.DB, r *api.SimpleConfigQueryReq) (*api.GenerateConfigResp,
	map[string]*model.ConfigNameDefModel, error) {
	// query
	var options = api.QueryConfigOptions{}
	if err := copier.Copy(&options, r); err != nil {
		return nil, nil, err
	}
	configs, confNamesDef, err := GetMergedConfig(db, &r.BaseConfigNode, &r.UpLevelInfo, &options) // @TODO use transaction
	if err != nil {
		return nil, nil, err
	}
	// response
	resp, err := FormatConfigFileForResp(r, configs)
	if err != nil {
		return nil, nil, err
	}
	resp.Revision = r.Revision
	return resp, confNamesDef, nil
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
	// 回写 tb_config_node 保存到层级树
	_, err := UpsertConfigItems(db, configsDiff, "", r.CreatedBy, &api.UpLevelInfo{})
	if err != nil {
		return nil, err
	}

	configs, _, err := GetMergedConfig(db, &r.BaseConfigNode, &r.UpLevelInfo, &options) // @TODO use transaction
	if err != nil {
		return nil, err
	}
	if r.Revision == "" {
		r.Revision = (&model.ConfigVersionedModel{}).NewRevisionName()
	}

	// response
	resp, err := FormatConfigFileForResp(r, configs)
	if err != nil {
		return nil, err
	}
	resp.Revision = r.Revision

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
		UpdatedAt:   time.Now(),
	}
	if _, err := configFile.CreateOrUpdate(false, db); err != nil {
		return err
	}
	return nil
}
