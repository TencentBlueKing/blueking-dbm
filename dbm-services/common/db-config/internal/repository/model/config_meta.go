package model

import (
	"fmt"

	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/util"

	"gorm.io/gorm"

	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/util/crypt"
)

// QueryConfigNames TODO
func QueryConfigNames(namespace, confType, confFile, confName string) ([]*ConfigNameDefModel, error) {
	var sqlRes *gorm.DB
	var err error
	confNames := make([]*ConfigNameDefModel, 0)
	columns :=
		"conf_name,value_type,value_type_sub,value_default,value_allowed,need_restart,flag_locked,flag_disable,flag_encrypt,need_restart,conf_name_lc,description"
	sqlRes = DB.Self.Debug().Model(ConfigNameDefModel{}).Select(columns).
		Where("conf_type = ? and conf_file = ?  and flag_locked = 0 and flag_status = -1 and flag_disable = 0",
			confType, confFile)
	if confName != "" {
		confName = confName + "%"
		sqlRes = sqlRes.Where("conf_name like ?", confName)
	}
	if namespace != "" {
		sqlRes = sqlRes.Where("namespace = ?", namespace)
	}
	if err = sqlRes.Find(&confNames).Error; err != nil {
		if err != gorm.ErrRecordNotFound {
			return nil, err
		}
	}
	key := fmt.Sprintf("%s%s", config.GetString("encrypt.keyPrefix"), constvar.BKBizIDForPlat)
	for _, cn := range confNames {
		cn.ValueDefault, err = crypt.DecryptString(cn.ValueDefault, key, constvar.EncryptEnableZip)
		if err != nil {
			return nil, err
		}
	}
	return confNames, nil
}

// QueryConfigNamesPlat 平台配置
// flag_status = 1 显式平台配置
// flag_disable not in (1, 2)  // 1:disable, 2:enable but readonly
func QueryConfigNamesPlat(namespace, confType, confFile, confName string) ([]*ConfigNameDefModel, error) {
	var sqlRes *gorm.DB
	var err error
	confNames := make([]*ConfigNameDefModel, 0)
	columns :=
		"conf_name,value_type,value_type_sub,value_default,value_allowed,need_restart,flag_locked,flag_disable,flag_encrypt,flag_status,need_restart,stage,conf_name_lc,description"
	sqlRes = DB.Self.Debug().Model(ConfigNameDefModel{}).Select(columns).
		Where("conf_type = ? and conf_file = ? and flag_status >= 1 and flag_disable = 0",
			confType, confFile)
	if confName != "" {
		confName = confName + "%"
		sqlRes = sqlRes.Where("conf_name like ?", confName)
	}
	if namespace != "" {
		sqlRes = sqlRes.Where("namespace = ?", namespace)
	}
	if err := sqlRes.Find(&confNames).Error; err != nil {
		if err != gorm.ErrRecordNotFound {
			return nil, err
		}
	}
	key := fmt.Sprintf("%s%s", config.GetString("encrypt.keyPrefix"), constvar.BKBizIDForPlat)
	for _, cn := range confNames {
		cn.ValueDefault, err = crypt.DecryptString(cn.ValueDefault, key, constvar.EncryptEnableZip)
		if err != nil {
			return nil, err
		}
	}
	return confNames, nil
}

// QueryConfigFileDetail TODO
func QueryConfigFileDetail(namespace, confType, confFile string) ([]*ConfigFileDefModel, error) {
	var sqlRes *gorm.DB
	confFiles := make([]*ConfigFileDefModel, 0)
	sqlRes = DB.Self.Model(&ConfigFileDefModel{}).Where("namespace = ? and conf_type = ?", namespace, confType)
	if confFile != "" {
		sqlRes = sqlRes.Where("conf_file = ?", confFile)
	}
	if err := sqlRes.Find(&confFiles).Error; err != nil {
		return nil, err
	} else if len(confFiles) == 0 {
		return nil, gorm.ErrRecordNotFound
	}
	for _, obj := range confFiles {
		obj.LevelNameList = util.SplitAnyRuneTrim(obj.LevelNames, ",")

	}
	return confFiles, nil
}

// GetConfigFileList godoc
// todo 用户替换QueryConfigFileDetail
func GetConfigFileList(namespace, confType, confFile string) ([]*ConfigFileDefModel, error) {
	sqlRes := DB.Self.Model(&ConfigFileDefModel{})
	if namespace != "" {
		sqlRes = sqlRes.Where("namespace = ?", namespace)
	}
	if confType != "" {
		sqlRes = sqlRes.Where("conf_type = ?", confType)
	}
	if confFile != "" {
		sqlRes = sqlRes.Where("conf_file = ?", confFile)
	}
	var confFiles []*ConfigFileDefModel
	err := sqlRes.Find(&confFiles).Error
	if err != nil {
		return nil, err
	}
	return confFiles, nil
}

// QueryConfigLevel TODO
func QueryConfigLevel(levels []string) ([]*ConfigLevelDefModel, error) {
	var sqlRes *gorm.DB
	confLevels := make([]*ConfigLevelDefModel, 0)
	if len(levels) != 0 {
		sqlRes = DB.Self.Debug().Model(ConfigLevelDefModel{}).Where("level_name in ?", levels)
	} else { // query all levels
		sqlRes = DB.Self.Model(ConfigLevelDefModel{})
	}
	if err := sqlRes.Find(&confLevels).Error; err != nil {
		return nil, err
	}
	return confLevels, nil
}
