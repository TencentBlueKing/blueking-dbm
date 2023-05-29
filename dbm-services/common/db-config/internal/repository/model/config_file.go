package model

import (
	"fmt"

	"github.com/pkg/errors"
	"gorm.io/gorm"

	"bk-dbconfig/pkg/util"
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

// SaveAndGetID TODO
func (c *ConfigFileDefModel) SaveAndGetID(db *gorm.DB) (uint64, error) {
	id, err := RecordExists(db, c.TableName(), 0, c.UniqueWhere())
	if errors.Is(err, gorm.ErrRecordNotFound) {
		if err := db.Save(c).Error; err != nil {
			return 0, err
		}
	} else {
		if err := db.Updates(c).Error; err != nil {
			return 0, err
		}
	}
	return id, nil
}
