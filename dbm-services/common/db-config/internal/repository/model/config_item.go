package model

import (
	"fmt"

	"bk-dbconfig/internal/pkg/cst"
	"bk-dbconfig/pkg/core/config"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"bk-dbconfig/pkg/util/crypt"

	"gorm.io/gorm"
)

// Create may have unique_key error
// create should not have id
func (c *ConfigModel) Create(upsert bool) error {
	var err error
	if err = c.HandleFlagEncrypt(); err != nil {
		return err
	}
	if upsert { // same as c.Update(false)
		if err = DB.Self.Save(c).Error; err != nil {
			logger.Error("Save fail:%v, err:%s", *c, err.Error())
			return err
		}
	} else {
		if err = DB.Self.Create(c).Error; err != nil {
			logger.Errorf("Create fail:%v, err:%s", *c, err.Error())
			return err
		}
	}
	return nil
}

// CheckRecordExists TODO
// check by id or unique_key
func (c *ConfigModel) CheckRecordExists(db *gorm.DB) (uint64, error) {
	var sqlRes *gorm.DB
	var tmpModel ConfigModel
	if c.ID != 0 { // by ID
		if err := db.Select("id").Take(c).Error; err != nil {
			// Take have ErrRecordNotFound
			return 0, err
		}
		return c.ID, nil
	} else { // by unique key
		// unique key: bk_biz_id, namespace, conf_name, conf_type, conf_file, level_name, level_value => conf_value
		c.ID = 0
		sqlRes = db.Model(ConfigModel{}).Select("id").Where(
			"bk_biz_id=? and namespace=? and conf_type=? and conf_name=? and conf_file=? and level_name=? and level_value=?",
			c.BKBizID, c.Namespace, c.ConfType, c.ConfName, c.ConfFile, c.LevelName, c.LevelValue).Take(&tmpModel)
		if err := sqlRes.Error; err != nil {
			return 0, err
		}
		return tmpModel.ID, nil
	}
}

// HandleFlagEncrypt 根据 flag_encrypt 判断是否需要加密
func (c *ConfigModel) HandleFlagEncrypt() error {
	if _, ok := crypt.IsEncryptedString(c.ConfValue); ok {
		// 以 ** 开头，已经是加密过的密码
		return nil
	} else if util.ConfValueIsPlaceHolder(c.ConfValue) {
		return nil
	}
	nameDef, err := CacheGetConfigNameDef(c.Namespace, c.ConfType, c.ConfFile, c.ConfName)
	if err == nil && nameDef.FlagEncrypt == 1 {
		key := config.GetString("encrypt.keyPrefix")
		c.ConfValue, err = crypt.EncryptString(c.ConfValue, key, constvar.EncryptEnableZip)
		if err != nil {
			logger.Errorf("HandleFlagEncrypt %+v. Error: %w", c, err)
			return errors.WithMessage(err, c.ConfName)
		}
	}
	return nil
}

// MayDecrypt 只根据前缀判断已加密串，直接解密
// 使用 encrypt.keyPrefix + level_value 作为 key来加密
func (c *ConfigModel) MayDecrypt() error {
	if _, ok := crypt.IsEncryptedString(c.ConfValue); !ok {
		// 不以 ** 开头，未加密
		return nil
	}
	var err error
	// 确实是已加密字符串，可以不用去 tb_config_name_def 里面获取 flag_encrypt
	key := config.GetString("encrypt.keyPrefix")
	c.ConfValue, err = crypt.DecryptString(c.ConfValue, key, constvar.EncryptEnableZip)
	if err != nil {
		logger.Errorf("MayDecrypt %+v. Error: %w", c, err)
		return errors.WithMessage(err, c.ConfName)
	}
	// }
	return nil
}

// UpdateMust TODO
// allow by id or by unique key
// if record is not exists, return err
func (c *ConfigModel) UpdateMust(db *gorm.DB) error {
	if configID, err := c.CheckRecordExists(db); err != nil {
		return err
	} else {
		c.ID = configID
		if err = c.HandleFlagEncrypt(); err != nil {
			return err
		}
		if err = db.Omit("time_created", "time_updated", "id").Updates(c).Error; err != nil {
			return err
		}
		// if record exists, do not check RowsAffected
		return nil
	}
}

// Update upsert
// found=true: if record is not exists, return error
// found=false: upsert
func (c *ConfigModel) Update(db *gorm.DB, ifNotFoundErr bool) error {
	if ifNotFoundErr {
		return c.UpdateMust(db)
	} else {
		// if err := DB.Self.Updates(c).Error; err != nil {
		if err := c.HandleFlagEncrypt(); err != nil {
			return err
		}
		if err := db.Omit("created_at", "updated_at").Save(c).Error; err != nil {
			return err
		}
		return nil
	}
}

// UpdateBatch TODO
// allow update and create
func UpdateBatch(db *gorm.DB, configs []*ConfigModel, ifNotFoundErr bool) error {
	upt := db.Transaction(func(tx *gorm.DB) error {
		for _, c := range configs {
			if err := c.Update(tx, ifNotFoundErr); err != nil {
				return err
			}
		}
		return nil
	})

	return upt
}

// CreateBatch TODO
// only allow id=0, only create
// if have duplicate, return err
func CreateBatch(db *gorm.DB, configs []*ConfigModel) error {
	var sqlRes *gorm.DB
	var err error
	for _, c := range configs {
		if err = c.HandleFlagEncrypt(); err != nil {
			return err
		}
	}
	sqlRes = db.Omit("created_at", "updated_at").Create(&configs)
	// sqlRes = DB.Self.Omit("time_created", "time_updated").Save(&configs)
	if err = sqlRes.Error; err != nil {
		logger.Errorf("add config items fail:%+v, err:%s", configs, err.Error())
		return err
	}
	return nil
}

// DeleteBatch TODO
// 批量根据 id 删除配置项
func DeleteBatch(db *gorm.DB, configs []*ConfigModel) error {
	del := db.Transaction(func(tx *gorm.DB) error {
		for _, c := range configs {
			if err := DeleteByUnique(tx, c.TableName(), c.UniqueWhere()); err != nil {
				return err
			}
		}
		return nil
	}, nil)
	return del
}

// CheckUniqueKeyProvided TODO
func (c *ConfigModel) CheckUniqueKeyProvided() bool {
	if c.ID > 0 {
		return true
	} else if c.BKBizID == "" || c.ConfType == "" || c.ConfName == "" || c.ConfFile == "" || c.LevelName == "" ||
		c.LevelValue == "" {
		return false
	} else {
		return true
	}
}

// GetOneConfigByUnique TODO
func GetOneConfigByUnique(c *ConfigModel) (*ConfigModel, error) {
	// UniqueKey: (bk_biz_id,conf_name,conf_type,conf_file,level_name,level_value) (namespace,conf_file不关键)
	var sqlRes *gorm.DB
	if !c.CheckUniqueKeyProvided() {
		return nil, errors.New("get one config should have a unique key")
	}
	configs := make([]*ConfigModel, 0)
	sqlRes = DB.Self.Where(c).Find(&configs) // .Find doesnot throw NotFound Error
	if err := sqlRes.Error; err != nil {
		return nil, err
	} else if len(configs) == 0 {
		return nil, gorm.ErrRecordNotFound
	} else if len(configs) > 1 {
		return nil, fmt.Errorf("expect 1 row found but get %d", len(configs))
	}
	return configs[0], nil
}

// GetConfigByIDs TODO
func GetConfigByIDs(ids []uint64) ([]*ConfigModel, error) {
	var sqlRes *gorm.DB
	configs := make([]*ConfigModel, 0)
	sqlRes = DB.Self.Select("id", "bk_biz_id", "conf_type", "conf_value", "description").Find(&configs, ids)
	// DB.Self.Where("id IN ?", ids).Find(&configs)
	if err := sqlRes.Error; err != nil {
		return nil, err
	}
	logger.Warnf("GetConfigByIDs sql: %+v", configs)
	return configs, nil
}

// GetUpLevelInfo TODO
func GetUpLevelInfo(r *api.BaseConfigNode, up *api.UpLevelInfo) (*api.UpLevelInfo, error) {
	fd := api.BaseConfFileDef{Namespace: r.Namespace, ConfType: r.ConfType, ConfFile: r.ConfFile}
	fileDef, err := CacheGetConfigFile(fd)
	upLevel := []string{}
	if err != nil {
		return nil, err
	} else if fileDef != nil {
		fileLevels := fileDef.LevelNameList
		allUpLevels := cst.GetConfigLevelsUp(r.LevelName)
		for _, l := range allUpLevels {
			if util.StringsHas(fileLevels, l) {
				upLevel = append(upLevel, l)
			}
		}
	}
	if up.LevelInfo == nil {
		up.LevelInfo = make(map[string]string)
	}
	for _, l := range upLevel {
		if l == constvar.LevelPlat || l == constvar.LevelApp {
			continue
		}
		if _, ok := up.LevelInfo[l]; !ok {
			// try get from versioned
			return nil, errors.Errorf("level=%s need up level_info %s", r.LevelName, l)
		}
	}
	return up, nil
}

// QueryAndDeleteConfig TODO
func QueryAndDeleteConfig(db *gorm.DB, levelNode *api.BaseConfigNode, configNames []string) error {
	conf := &ConfigModel{}
	copier.Copy(conf, levelNode)
	for _, confName := range configNames {
		conf.ConfName = confName
		if cNew, err := GetOneConfigByUnique(conf); err != nil {
			if err == gorm.ErrRecordNotFound {
				continue
			} else {
				return err
			}
		} else {
			delWhere := map[string]interface{}{
				"bk_biz_id":   cNew.BKBizID,
				"namespace":   cNew.Namespace,
				"conf_type":   cNew.ConfType,
				"conf_file":   cNew.ConfFile,
				"level_name":  cNew.LevelName,
				"level_value": cNew.LevelValue,
				"conf_name":   cNew.ConfName,
			}
			logger.Warn("delete config: %+v", cNew)
			if err := DeleteByUnique(db, cNew.TableName(), delWhere); err != nil {
				return err
			}
		}
	}
	// DeleteBatch(db, configsDel)
	return nil
}
