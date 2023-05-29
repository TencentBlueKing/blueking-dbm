package model

import (
	"fmt"

	"bk-dbconfig/pkg/core/config"

	"github.com/pkg/errors"
	"gorm.io/gorm"

	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/crypt"
)

// ConfigNamesBatchSave godoc
// flag_status = -0 plat_config pre_defined
// flag_status = 1 pub_config intended to be inherited
func ConfigNamesBatchSave(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	for _, confName := range confNames {
		if confName.FlagDisable == -1 { // 直接物理删除
			if confName.FlagStatus != -1 || confName.FlagLocked == 1 {
				return errors.Errorf("conf_name[%s] intend to be plat_config, delete is not allowed", confName.ConfName)
			}
			return errors.Errorf("conf_name[%s] intend to be plat_config, delete not support currently", confName.ConfName)
		} else if confName.FlagDisable == 1 { // 禁用该选项，等于删除，只是软删
			// todo 当 flag_status=-1 时，如果发布平台配置，需要从 tb_config_node plat_config 移除
			confName.FlagStatus = -1
		} else if confName.FlagStatus == -1 { // 页面删除，放回 pre_defined 配置项列表

		} else {
			// 只要在通过api/前端访问过来的修改请求，都把 flag_status 标志位1，代表平台配置
			confName.FlagStatus = 1
		}
		if confName.FlagLocked == 1 && confName.FlagDisable == 0 { // 锁定的配置 显式出现在平台配置列表
			confName.FlagStatus = 1
		}
		// 不能即 lock 又 disable
	}
	return ConfigNamesBatchUpdate(db, confNames)
}

// ConfigNamesBatchUpdate TODO
// update 逐个进行，开启事务
func ConfigNamesBatchUpdate(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	err := db.Transaction(func(tx *gorm.DB) error {
		for _, c := range confNames {
			cnDef, err := CacheGetConfigNameDef(c.Namespace, c.ConfType, c.ConfFile, c.ConfName)
			if err == nil && cnDef.FlagEncrypt == 1 {
				key := fmt.Sprintf("%s%s", config.GetString("encrypt.keyPrefix"), constvar.BKBizIDForPlat)
				c.ValueDefault, _ = crypt.EncryptString(c.ValueDefault, key, constvar.EncryptEnableZip)
			}
			if err1 := tx.Debug().Select("value_default", "value_allowed", "flag_status", "flag_locked").
				Where(c.UniqueWhere()).Updates(c).Error; err1 != nil {
				return errors.WithMessage(err1, c.ConfName)
			}
		}
		return nil
	})
	return err
}

// ConfigNamesBatchDelete TODO
// 删除有两种逻辑：这里假设每一批删除都是同一个逻辑，任意取1元素的FlagDisable判断是那种逻辑
// // 1. 从平台配置列表移除
//
//	   只修改 namestatus
//	2. 从 conf_name 表删除
//	   delete 根据主键id删除，或者使用唯一键. 这个操作目前没有对外 @todo
func ConfigNamesBatchDelete(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	deleteConfName := false
	for _, confName := range confNames {
		confName.FlagStatus = -1 // 从平台配置 放回 配置名列表
		if confName.FlagDisable == -1 {
			deleteConfName = true
		}
	}
	if deleteConfName { // 2. 从 conf_name 表删除
		// 删除 conf_name 涉及到上下级锁定关系，暂不支持
		return errors.New("delete conf_name is not allowed for now")
		/*
		   return db.Transaction(func(tx *gorm.DB) error {
		       for _, c := range confNames {
		           if c.ID > 0 {
		               return DeleteByUnique(tx, c.TableName(), c.UniqueWhere())
		           } else {
		               return BatchDeleteByID(tx, c.TableName(), []uint64{c.ID})
		           }
		       }
		       return nil
		   })
		*/
	} else { // 1. 从平台配置列表移除
		return ConfigNamesBatchSave(db, confNames)
	}
}

// ConfigNamesBatchCreate2 TODO
func ConfigNamesBatchCreate2(confNames []*ConfigNameDefModel) error {
	var sqlRes *gorm.DB
	sqlRes = DB.Self.Omit("time_created", "time_updated").Create(&confNames)
	// sqlRes = DB.Self.Omit("time_created", "time_updated").Save(&confNames)
	if err := sqlRes.Error; err != nil {
		logger.Errorf("add conf_names :%+v, err:%s", confNames, err.Error())
		return err
	}
	return nil
}

// ConfigNamesBatchUpdate2 TODO
// update 逐个进行，开启事务
func ConfigNamesBatchUpdate2(confNames []*ConfigNameDefModel) error {
	err := DB.Self.Transaction(func(tx *gorm.DB) error {
		for _, c := range confNames {
			if err1 := DB.Self.UpdateColumns(c).Error; err1 != nil {
				return err1
			}
		}
		return nil
	})
	return err
}

// ConfigNamesBatchDelete2 TODO
// delete 必须根据主键id删除，不使用唯一键
func ConfigNamesBatchDelete2(confNames []*ConfigNameDefModel) error {
	var sqlRes *gorm.DB
	sqlRes = DB.Self.Delete(&confNames)
	if err := sqlRes.Error; err != nil {
		logger.Errorf("delete config names fail:%+v, err:%s", confNames, err.Error())
		return err
	}
	return nil
}
