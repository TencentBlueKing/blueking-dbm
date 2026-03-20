package model

import (
	"fmt"
	"strings"

	"bk-dbconfig/pkg/core/config"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	"gorm.io/gorm"

	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/crypt"
)

// ConfigNamesBatchUpdate TODO
// update 逐个进行，开启事务
func ConfigNamesBatchUpdate(db *gorm.DB, confNames []*ConfigNameDefModel, opUser string) error {
	return db.Transaction(func(tx *gorm.DB) error {
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			// 查询变更前的快照
			var before ConfigNameDefModel
			beforeImage := ConfName{}
			if err := tx.Where(c.UniqueWhere()).First(&before).Error; err == nil {
				beforeImage = NewConfNameFromDef(&before)
			}

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

			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: beforeImage,
				AfterImage:  NewConfNameFromDef(c),
				OpUser:      opUser,
				OpType:      constvar.OPTypeUpdate,
			})
		}
		if opUser == "system" {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}

// ConfigNamesBatchDelete TODO
// 删除有两种逻辑：这里假设每一批删除都是同一个逻辑，任意取1元素的FlagDisable判断是那种逻辑
// // 1. 从平台配置列表移除
//
//	   只修改 namestatus
//	2. 从 conf_name 表删除
//	   delete 根据主键id删除，或者使用唯一键. 这个操作目前没有对外 @todo
func ConfigNamesBatchDelete(db *gorm.DB, confNames []*ConfigNameDefModel, opUser string) error {
	return db.Transaction(func(tx *gorm.DB) error {
		nodes := []*ConfigModel{}
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			err := tx.Debug().Model(ConfigModel{}).
				Where("namespace = ? and conf_type = ? and conf_name = ?",
					c.Namespace, c.ConfType, c.ConfName).Find(&nodes).Error
			if err != nil {
				return err
			}
			if len(nodes) > 0 { // 下级存在引用，不能删除
				return errors.Errorf("conf_name=%s is used by app::%s", c.ConfName,
					strings.Join(lo.Map(nodes, func(node *ConfigModel, _ int) string {
						return fmt.Sprintf("bk_biz_id=%s(%s=%s)", node.BKBizID, node.LevelName, node.LevelValue)
					}), ", "))
			}

			// 查询变更前的快照
			var before ConfigNameDefModel
			beforeImage := ConfName{}
			if err := tx.Where(c.UniqueWhere()).First(&before).Error; err == nil {
				beforeImage = NewConfNameFromDef(&before)
			}

			if err := DeleteByUnique(tx, c.TableName(), c.UniqueWhere()); err != nil {
				return errors.WithMessage(err, c.ConfName)
			}

			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: beforeImage,
				AfterImage:  ConfName{},
				OpUser:      opUser,
				OpType:      constvar.OPTypeRemove,
			})
		}
		if opUser == "system" {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}

// ConfigNamesBatchCreate TODO
func ConfigNamesBatchCreate(db *gorm.DB, confNames []*ConfigNameDefModel, opUser string) error {
	return db.Transaction(func(tx *gorm.DB) error {
		// handle encrypt like update?
		sqlRes := tx.Omit("time_created", "time_updated").Create(&confNames)
		// sqlRes = DB.Self.Omit("time_created", "time_updated").Save(&confNames)
		if err := sqlRes.Error; err != nil {
			logger.Errorf("add conf_names :%+v, err:%s", confNames, err.Error())
			return err
		}
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: ConfName{},
				AfterImage:  NewConfNameFromDef(c),
				OpUser:      opUser,
				OpType:      constvar.OPTypeAdd,
			})
		}
		if opUser == "system" {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}

// ConfigNamesBatchSave upsert
// 聚合 create 和 update 的操作，通过唯一键来判断是否是一条记录
// 先执行 create，当报 duplicate key 时，根据唯一键来执行 update 其它非唯一键字段
func ConfigNamesBatchSave(db *gorm.DB, confNames []*ConfigNameDefModel, opUser string) error {
	return db.Transaction(func(tx *gorm.DB) error {
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			// 查询变更前的快照
			var before ConfigNameDefModel
			beforeImage := ConfName{}
			opType := constvar.OPTypeAdd
			if err := tx.Where(c.UniqueWhere()).First(&before).Error; err == nil {
				beforeImage = NewConfNameFromDef(&before)
				opType = constvar.OPTypeUpdate
			}

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

			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: beforeImage,
				AfterImage:  NewConfNameFromDef(c),
				OpUser:      opUser,
				OpType:      opType,
			})
		}
		if opUser == "system" {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}
