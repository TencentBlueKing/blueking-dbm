package model

import (
	"fmt"
	"strings"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/pkg/core/config"

	"github.com/pkg/errors"
	"github.com/samber/lo"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/crypt"
)

type ConfNameOperation struct {
	OpUser string
	// def / plat
	Table     string
	ConfNames []*ConfigNameDefModel
}

// BatchUpdate TODO
// update 逐个进行，开启事务
func (op *ConfNameOperation) BatchUpdate(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	return db.Transaction(func(tx *gorm.DB) error {
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			// 查询变更前的快照
			var before ConfigNameDefModel
			beforeImage := api.ConfName{}
			if err := tx.Where(c.UniqueWhere()).First(&before).Error; err == nil {
				beforeImage = NewConfNameFromDef(&before)
			}

			cnDef, err := CacheGetConfigNameDef(c.Namespace, c.ConfType, c.ConfFile, c.ConfName)
			if err == nil && cnDef.FlagEncrypt == 1 {
				key := config.GetString("encrypt.keyPrefix")
				c.ValueDefault, _ = crypt.EncryptString(c.ValueDefault, key, constvar.EncryptEnableZip)
			}
			dbOp := tx.Debug().Select(
				"value_default",
				"value_allowed", "value_type", "value_type_sub",
				"flag_status", "flag_locked", "flag_readonly", "flag_visible", "need_restart", "flag_encrypt",
				"description", "conf_name_lc", "deleted").
				Where(c.UniqueWhere())
			if op.Table != constvar.PlatTypeDef {
				dbOp = dbOp.Model(ConfigNamePlatModel{})
			}
			if err1 := dbOp.Updates(c).Error; err1 != nil {
				return errors.WithMessage(err1, c.ConfName)
			}

			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: beforeImage,
				AfterImage:  NewConfNameFromDef(c),
				OpUser:      op.OpUser,
				OpType:      constvar.OPTypeUpdate,
			})
		}
		if op.OpUser == "system" || op.Table == constvar.PlatTypeDef {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}

// BatchDelete TODO
// 删除有两种逻辑：这里假设每一批删除都是同一个逻辑，任意取1元素的FlagDisable判断是那种逻辑
// // 1. 从平台配置列表移除
//
//	   只修改 namestatus
//	2. 从 conf_name 表删除
//	   delete 根据主键id删除，或者使用唯一键. 这个操作目前没有对外 @todo
func (op *ConfNameOperation) BatchDelete(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	return db.Transaction(func(tx *gorm.DB) error {
		nodes := []*ConfigModel{}
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			// 查询变更前的快照
			var before ConfigNameDefModel
			beforeImage := api.ConfName{}
			if err := tx.Where(c.UniqueWhere()).First(&before).Error; err == nil {
				beforeImage = NewConfNameFromDef(&before)
			}
			opType := constvar.OPTypeRemove
			if before.ConfName != "" {
				opType = constvar.OpTypeRecover
			}

			err := tx.Debug().Model(ConfigModel{}).
				Where("namespace = ? and conf_type = ? and conf_name = ?",
					c.Namespace, c.ConfType, c.ConfName).Find(&nodes).Error
			if err != nil {
				return err
			}
			if len(nodes) > 0 && opType == constvar.OPTypeRemove { // 下级存在引用，不能删除
				return errors.Errorf("conf_name=%s is used by app::%s", c.ConfName,
					strings.Join(lo.Map(nodes, func(node *ConfigModel, _ int) string {
						return fmt.Sprintf("bk_biz_id=%s(%s=%s)", node.BKBizID, node.LevelName, node.LevelValue)
					}), ", "))
			}

			tableName := c.TableName()
			if op.Table != constvar.PlatTypeDef {
				tableName = ConfigNamePlatModel{}.TableName()
			}
			if err := DeleteByUnique(tx, tableName, c.UniqueWhere()); err != nil {
				return errors.WithMessage(err, c.ConfName)
			}

			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: beforeImage,
				AfterImage:  api.ConfName{},
				OpUser:      op.OpUser,
				OpType:      opType,
			})
		}
		if op.OpUser == "system" || op.Table == constvar.PlatTypeDef {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}

// BatchCreate TODO
func (op *ConfNameOperation) BatchCreate(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	return db.Transaction(func(tx *gorm.DB) error {
		// handle encrypt like update?

		dbOp := tx.Omit("time_created", "time_updated")
		if op.Table != constvar.PlatTypeDef {
			dbOp = dbOp.Model(ConfigNamePlatModel{})
		}

		// sqlRes = DB.Self.Omit("time_created", "time_updated").Save(&confNames)
		if err := dbOp.Create(&confNames).Error; err != nil {
			logger.Errorf("add conf_names :%+v, err:%s", confNames, err.Error())
			if errors.Is(err, gorm.ErrDuplicatedKey) {
				// 目前页面修改，都是一个一个提交的
				return errors.Errorf("conf_name:%s already exists", confNames[0].ConfName)
			}
			return err
		}
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: api.ConfName{},
				AfterImage:  NewConfNameFromDef(c),
				OpUser:      op.OpUser,
				OpType:      constvar.OPTypeAdd,
			})
		}
		if op.OpUser == "system" || op.Table == constvar.PlatTypeDef {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}

// BatchSave upsert
// 使用 ON DUPLICATE KEY UPDATE 实现 upsert，一条 SQL 完成插入或更新
func (op *ConfNameOperation) BatchSave(db *gorm.DB, confNames []*ConfigNameDefModel) error {
	// 冲突时需要更新的字段列表
	upsertColumns := []string{
		"conf_name_lc", "value_type", "value_default", "value_allowed", "value_type_sub",
		"flag_visible", "flag_readonly", "flag_locked", "flag_encrypt", "flag_disable",
		"flag_status", "need_restart", "description", "deleted",
	}
	return db.Transaction(func(tx *gorm.DB) error {
		changes := make([]*ConfNameChangesModel, 0, len(confNames))
		for _, c := range confNames {
			// 查询变更前的快照
			var before ConfigNameDefModel
			beforeImage := api.ConfName{}
			opType := constvar.OPTypeAdd
			if err := tx.Where(c.UniqueWhere()).First(&before).Error; err == nil {
				beforeImage = NewConfNameFromDef(&before)
				opType = constvar.OPTypeUpdate
			}
			dbTx := tx.Debug().Omit("time_created", "time_updated")
			if op.Table != constvar.PlatTypeDef {
				dbTx = dbTx.Model(ConfigNamePlatModel{})
			}
			if err := dbTx.Clauses(clause.OnConflict{
				Columns: []clause.Column{
					{Name: "namespace"}, {Name: "conf_type"}, {Name: "conf_file"}, {Name: "conf_name"},
				},
				DoUpdates: clause.AssignmentColumns(upsertColumns),
			}).Create(c).Error; err != nil {
				return errors.WithMessage(err, c.ConfName)
			}

			changes = append(changes, &ConfNameChangesModel{
				Namespace:   c.Namespace,
				ConfType:    c.ConfType,
				ConfFile:    c.ConfFile,
				ConfName:    c.ConfName,
				BeforeImage: beforeImage,
				AfterImage:  NewConfNameFromDef(c),
				OpUser:      op.OpUser,
				OpType:      opType,
			})
		}
		if op.OpUser == "system" || op.Table == constvar.PlatTypeDef {
			return nil
		}
		return ConfNameChangesCreate(tx, changes)
	})
}
