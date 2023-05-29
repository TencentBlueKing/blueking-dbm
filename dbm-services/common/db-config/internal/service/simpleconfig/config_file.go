package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	util "bk-dbconfig/pkg/util/dbutil"
	"strconv"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// GetConfigLockLevel TODO
func GetConfigLockLevel(locked int8, levelName string) string {
	if locked <= 0 {
		return ""
	} else {
		return levelName
	}
}

func checkConfigFileExists(r *api.BaseConfFileDef) (bool, *model.ConfigFileDefModel, error) {
	cf := &model.ConfigFileDefModel{
		Namespace: r.Namespace,
		ConfType:  r.ConfType,
		ConfFile:  r.ConfFile,
	}
	fileDefObj, err := model.RecordGet(model.DB.Self, cf.TableName(), cf.ID, cf.UniqueWhere())

	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			// conf_file 不存在
			return false, cf, nil
		} else {
			// 其余错误，包括输入了错误id与唯一建
			return false, cf, err
		}
	}
	fileDef := util.ConvDBResultToStr(fileDefObj)
	logger.Infof("checkConfigFileExists fileDef:+v", fileDef)
	idNew, _ := fileDef["id"]
	cf.ID, _ = strconv.ParseUint(idNew, 10, 64)
	cf.ConfFileLC, _ = fileDef["conf_file_lc"]
	cf.Description, _ = fileDef["description"]
	return true, cf, nil
}

// NewConfigModels TODO
func NewConfigModels(r *api.UpsertConfFilePlatReq) ([]*model.ConfigModel, []*model.ConfigModelOp) {
	configs := make([]*model.ConfigModel, 0)
	configsDiff := make([]*model.ConfigModelOp, 0)
	for _, cn := range r.ConfNames {
		confItem := &model.ConfigModel{
			BKBizID:     constvar.BKBizIDForPlat,
			Namespace:   r.ConfFileInfo.Namespace,
			ConfType:    r.ConfFileInfo.ConfType,
			ConfFile:    r.ConfFileInfo.ConfFile,
			ConfName:    cn.ConfName,
			ConfValue:   cn.ValueDefault,
			LevelName:   constvar.LevelPlat,
			LevelValue:  constvar.BKBizIDForPlat,
			FlagLocked:  cn.FlagLocked,
			FlagDisable: cn.FlagDisable,
			Description: cn.Description,
		}
		configs = append(configs, confItem)
		COP := &model.ConfigModelOp{
			Config: confItem,
			OPType: cn.OPType,
		}
		configsDiff = append(configsDiff, COP)
	}
	return configs, configsDiff
}

// ProcessOPConfig TODO
func ProcessOPConfig(opConfigs map[string]*ConfigModelRef) error {
	for _, opConfig := range opConfigs {
		for optype, configs := range *opConfig {
			if optype == constvar.OPTypeRemoveRef {
				if err := UpsertConfig(configs, false, false); err != nil {
					// model.UpsertBatchConfigs(configs, false); err != nil {
				}
			} else if optype == constvar.OPTypeNotified {
				// 值有变化，红点通知同步
			} else { // locked
				// 暂不处理
			}
		}
	}
	return nil
}

// ListConfigFiles godoc
// 查询平台配置文件列表 和 业务配置文件列表
func ListConfigFiles(r *api.ListConfFileReq) ([]*api.ListConfFileResp, error) {
	// confFiles := make([]*model.ConfigFileDefModel, 0)
	fileNode := &model.ConfigFileNodeModel{
		Namespace:  r.Namespace,
		ConfType:   r.ConfType,
		BKBizID:    r.BKBizID,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
		ConfFile:   r.ConfFile,
	}
	confFiles, err := fileNode.List(model.DB.Self, constvar.BKBizIDForPlat)
	if err != nil {
		return nil, err
	}

	resp := make([]*api.ListConfFileResp, 0)
	for _, f := range confFiles {
		p := &api.ListConfFileResp{
			ConfFileDef: api.ConfFileDef{
				BaseConfFileDef: api.BaseConfFileDef{
					Namespace: r.Namespace,
					ConfType:  r.ConfType,
					ConfFile:  f.ConfFile,
				},
				ConfFileLC:  f.ConfFileLC,
				ConfTypeLC:  f.ConfTypeLC,
				Description: f.Description,
			},
			CreatedAt: f.CreatedAt.String(),
			UpdatedAt: f.UpdatedAt.String(),
			UpdatedBy: f.UpdatedBy,
		}
		resp = append(resp, p)
	}
	return resp, nil
}

// GetConfigFileSimpleInfo godoc
// 查询配置文件信息，会合并平台配置文件
func GetConfigFileSimpleInfo(r *api.BaseConfigNode) (*api.ConfFileResp, error) {
	confFile := &model.ConfigFileNodeModel{
		Namespace:  r.Namespace,
		ConfType:   r.ConfType,
		ConfFile:   r.ConfFile,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
		BKBizID:    r.BKBizID,
	}
	// confFile := model.ConfigFileNodeModel{}
	// copier.CopyWithOption(confFile, r)
	// get config file info
	cf, err := confFile.Detail(model.DB.Self)
	if err != nil {
		return nil, err
	}
	fd := api.BaseConfFileDef{
		Namespace: r.Namespace,
		ConfType:  r.ConfType,
		ConfFile:  r.ConfFile,
	}
	resp := &api.ConfFileResp{
		ConfFileDef: api.ConfFileDef{
			BaseConfFileDef: fd,
		},
	}
	if cf == nil || cf.ConfFileLC == "" { // 如果没有找到本节点的 config_file，使用平台的(从cache中拿)
		platFile, err := model.CacheGetConfigFile(fd)
		if err != nil {
			return nil, err
		} else if platFile == nil { // 不存在平台配置文件
			return nil, errors.Errorf("config file %s not found", r.ConfFile)
			// NotFoundInDB
		} else {
			resp.ConfFileLC = platFile.ConfFileLC
			resp.ConfTypeLC = platFile.ConfTypeLC
			resp.Description = platFile.Description
		}
		if r.BKBizID == constvar.BKBizIDForPlat && r.LevelName == constvar.LevelPlat {
			resp.CreatedAt = platFile.CreatedAt.String()
			resp.UpdatedAt = platFile.UpdatedAt.String()
			resp.UpdatedBy = platFile.UpdatedBy
		}
	} else {
		resp.ConfFileLC = cf.ConfFileLC
		resp.ConfTypeLC = cf.ConfTypeLC
		resp.Description = cf.Description
		resp.CreatedAt = cf.CreatedAt.String()
		resp.UpdatedAt = cf.UpdatedAt.String()
		resp.UpdatedBy = cf.UpdatedBy
	}
	return resp, nil
}
