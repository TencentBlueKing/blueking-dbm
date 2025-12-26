package model

import (
	"fmt"
	"strings"

	"bk-dbconfig/pkg/util"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// DeleteByUnique TODO
func DeleteByUnique(db *gorm.DB, tableName string, uniqueWhere map[string]interface{}) error {
	var sqlRes *gorm.DB
	sqlRes = db.Debug().Table(tableName).Where(uniqueWhere).Delete(tableName)
	if sqlRes.Error != nil {
		return sqlRes.Error
	}
	return nil
}

// BatchDeleteByID TODO
func BatchDeleteByID(db *gorm.DB, tableName string, ids []uint64) error {
	var sqlRes *gorm.DB
	sqlRes = db.Delete(tableName).Where("id in ?", ids)
	if sqlRes.Error != nil {
		return sqlRes.Error
	}
	return nil
}

type modelID struct {
	ID uint64 `json:"id" gorm:"column:id;type:bigint;PRIMARY_KEY"`
}

// RecordExists TODO
// 判断记录是否存在，如果存在则返回记录 id
// 优先根据唯一建索引判断，如果记录存在但与输入的id不同(且输入id>0)，则报错，否则返回实际id (from db)；如果唯一索引不存在，则根据id判断
// 只检查 1 条记录。外层根据 error 是否 ErrRecordNotFound 判断记录是否存在
func RecordExists(db *gorm.DB, tbName string, id uint64, uniqueWhere map[string]interface{}) (uint64, error) {
	var sqlRes *gorm.DB
	var idnew modelID
	if !util.IsEmptyMap(uniqueWhere) { // by unique key
		sqlRes = db.Table(tbName).Select("id").Where(uniqueWhere).Take(&idnew)
		if err := sqlRes.Error; err != nil {
			// not found or error. 返回的 id 没有意义
			return idnew.ID, err
		} else if id > 0 && id != idnew.ID {
			// found. 判断 id 是否与 idnew.ID 相同
			return idnew.ID, fmt.Errorf("id error id_1=%d, id_2=%d", id, idnew.ID)
		} else {
			// found and return id
			return idnew.ID, nil
		}
	} else { // by ID
		sqlRes = db.Table(tbName).Select("id").Where("id = ?", id).Take(&idnew)
		return id, sqlRes.Error // Take() have ErrRecordNotFound
	}
}

// RecordGet TODO
func RecordGet(db *gorm.DB, tbName string, id uint64, uniqueWhere map[string]interface{}) (map[string]interface{},
	error) {
	var sqlRes *gorm.DB
	var idnew modelID
	objMap := map[string]interface{}{}

	if !util.IsEmptyMap(uniqueWhere) { // by unique key
		sqlRes = db.Debug().Table(tbName).Select("*").Where(uniqueWhere).Take(&objMap)
		if err := sqlRes.Error; err != nil {
			// not found or error. 返回的 id 没有意义
			return objMap, err
		} else if id > 0 && id != idnew.ID {
			// found. 判断 id 是否与 idnew.ID 相同
			return objMap, fmt.Errorf("id error id_1=%d, id_2=%d", id, idnew.ID)
		} else {
			// found and return id
			return objMap, nil
		}
	} else { // by ID
		sqlRes = db.Debug().Table(tbName).Select("*").Where("id = ?", id).Take(&objMap)
		return objMap, sqlRes.Error // Take() have ErrRecordNotFound
	}
}

// Exists TODO
func (c *ConfigFileDefModel) Exists(db *gorm.DB) (uint64, error) {
	var sqlRes *gorm.DB
	if c.ID != 0 { // by ID
		if err := db.Select("id").Take(c).Error; err != nil {
			// Take have ErrRecordNotFound
			return 0, err
		}
		return c.ID, nil
	} else { // by unique key
		sqlRes = DB.Self.Model(ConfigFileDefModel{}).Select("id").Where(c.UniqueWhere()).Take(&c)
		if err := sqlRes.Error; err != nil {
			return 0, err
		}
		return c.ID, nil
	}
}

func (c *ConfigFileDefModel) Upsert(db *gorm.DB) error {
	/*
		db.Debug().Clauses(clause.OnConflict{
			Columns:   []clause.Column{Name: "conf_type_lc"},
			UpdateAll: true,
		})

	*/
	e := db.Transaction(func(tx *gorm.DB) error {
		err := tx.Debug().Create(c).Error
		if err != nil && (errors.Is(err, gorm.ErrDuplicatedKey) || strings.Contains(err.Error(), "Duplicate entry")) {
			err = tx.Debug().Where(c.UniqueWhere()).Select("conf_type_lc",
				"conf_file_lc",
				"level_versioned",
				"level_names",
				"conf_name_validate",
				"conf_value_validate",
				"value_type_strict",
				"description",
				"updated_by").Updates(c).Error
			if err != nil {
				return err
			}
		}
		return err
	})
	return e
}

// SaveAndGetID TODO
func (c *ConfigFileDefModel) SaveAndGetID(db *gorm.DB) (uint64, error) {

	err := db.Transaction(func(tx *gorm.DB) error {
		_, err := c.Exists(tx)
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil
		} else {
			return err
		}
	})

	id, err := RecordExists(db, c.TableName(), 0, c.UniqueWhere())
	if errors.Is(err, gorm.ErrRecordNotFound) {
		if err := db.Save(c).Error; err != nil {
			return 0, err
		}
	} else {
		err = db.Debug().Model(c).Where(c.UniqueWhere()).Select("conf_type_lc",
			"conf_file_lc",
			"level_versioned",
			"level_names",
			"conf_name_validate",
			"conf_value_validate",
			"value_type_strict",
			"description",
			"updated_by").Error
		if err != nil {
			return 0, err
		}
	}
	return id, nil
}
