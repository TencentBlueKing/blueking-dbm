package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/core/logger"

	"gorm.io/gorm"
)

// ChangeConfNameDef TODO
// 添加平台配置
// 如果 conf_file 已经存在，则报错
// 新建 conf_file，保存操作在 def 表，发布时进入 node 表，生成revision并发布
func ChangeConfNameDef(r *api.ChangeConfNameDefReq, opUser string) (*api.UpsertConfFilePlatResp,
	error) {
	fileDef := r.BaseConfFileDef
	exists, cf, err := checkConfigFileExists(&fileDef)
	if err != nil {
		return nil, err
	} else {
		cf.UpdatedBy = opUser
	}
	logger.Info("UpsertConfigFilePlat conf_file info %+v", cf)
	if exists {

	}
	resp := &api.UpsertConfFilePlatResp{
		BaseConfFileDef: fileDef,
	}

	txErr := model.DB.Self.Transaction(func(tx *gorm.DB) error {
		// 保存逻辑
		{

			// 保存到 tb_config_name_def
			// @todo 这里保存到 tb_config_name_def 就意味着发布了，与 tb_config_versioned 不一致
			if err := ConfigNamesBatchUpsert(tx, r.BaseConfFileDef, r.ConfNames); err != nil {
				return err
			}
			resp.IsPublished = 0
		}
		return nil
	})
	if txErr == nil {
		model.CacheSetAndGetConfigFile(fileDef)
	}
	return resp, txErr
}
