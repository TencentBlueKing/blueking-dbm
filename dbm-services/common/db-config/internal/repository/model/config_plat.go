package model

import (
	"fmt"
	"strings"

	"bk-dbconfig/pkg/core/config"

	"github.com/pkg/errors"
	"gorm.io/gorm"

	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/crypt"
)

// ConfigNamesBatchUpdate TODO
// update 逐个进行，开启事务
func ConfigNamesBatchUpdate(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	return db.Transaction(func(tx *gorm.DB) error {
		for _, c := range confNames {
			cnDef, err := CacheGetConfigNameDef(c.Namespace, c.ConfType, c.ConfFile, c.ConfName)
			if err == nil && cnDef.FlagEncrypt == 1 {
				key := fmt.Sprintf("%s%s", config.GetString("encrypt.keyPrefix"), constvar.BKBizIDForPlat)
				c.ValueDefault, _ = crypt.EncryptString(c.ValueDefault, key, constvar.EncryptEnableZip)
			}
			if err1 := tx.Debug().Select(
				"value_default",
				"value_allowed", "value_type", "value_type_sub",
				"flag_status", "flag_locked", "flag_readonly", "flag_visible", "need_restart",
				"description", "conf_name_lc").
				Where(c.UniqueWhere()).Updates(c).Error; err1 != nil {
				return errors.WithMessage(err1, c.ConfName)
			}
		}
		return nil
	})
}

// ConfigNamesBatchDelete TODO
// 删除有两种逻辑：这里假设每一批删除都是同一个逻辑，任意取1元素的FlagDisable判断是那种逻辑
// // 1. 从平台配置列表移除
//
//	   只修改 namestatus
//	2. 从 conf_name 表删除
//	   delete 根据主键id删除，或者使用唯一键. 这个操作目前没有对外 @todo
func ConfigNamesBatchDelete(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	return db.Transaction(func(tx *gorm.DB) error {
		for _, c := range confNames {
			if err := DeleteByUnique(tx, c.TableName(), c.UniqueWhere()); err != nil {
				return errors.WithMessage(err, c.ConfName)
			}
		}
		return nil
	})
}

// ConfigNamesBatchCreate TODO
func ConfigNamesBatchCreate(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	var sqlRes *gorm.DB
	// handle encrypt like update?
	sqlRes = db.Omit("time_created", "time_updated").Create(&confNames)
	// sqlRes = DB.Self.Omit("time_created", "time_updated").Save(&confNames)
	if err := sqlRes.Error; err != nil {
		logger.Errorf("add conf_names :%+v, err:%s", confNames, err.Error())
		return err
	}
	return nil
}

// ConfigNamesBatchSave upsert
// 聚合 create 和 update 的操作，通过唯一键来判断是否是一条记录
// 先执行 create，当报 duplicate key 时，根据唯一键来执行 update 其它非唯一键字段
func ConfigNamesBatchSave(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	return db.Transaction(func(tx *gorm.DB) error {
		for _, c := range confNames {
			if err := tx.Debug().Omit("time_created", "time_updated").Create(c).Error; err != nil {
				fmt.Println(err)
				fmt.Println(gorm.ErrDuplicatedKey)
				if errors.Is(err, gorm.ErrDuplicatedKey) || strings.Contains(err.Error(), "Duplicate entry") {
					// 当遇到重复键错误时，根据唯一键执行 update
					if err := tx.Debug().Model(c).Where(c.UniqueWhere()).Updates(c).Error; err != nil {
						return errors.WithMessage(err, c.ConfName)
					}
				} else {
					// 其他错误直接返回
					return errors.WithMessage(err, c.ConfName)
				}
			} else {
				fmt.Println("create ok")
			}
		}
		return nil
	})
}
