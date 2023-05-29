package model

import (
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// CreateOrUpdate TODO
// create 表示明确是插入
func (c *ConfigFileNodeModel) CreateOrUpdate(create bool, db *gorm.DB) (uint64, error) {
	if create {
		return c.ID, db.Create(c).Error
	}
	id, _ := RecordExists(db, c.TableName(), 0, c.UniqueWhere())
	if id > 0 {
		// node_id 已经存在，且本次是 generate，不覆盖原 description 信息. 见 GenerateConfigVersion
		if c.ConfFileLC == "" && c.Description == "generated" {
			return c.ID, nil
		}
		c.ID = id
		return c.ID, db.Updates(c).Error
	} else {
		return c.ID, db.Create(c).Error
	}
}

// List TODO
func (c *ConfigFileNodeModel) List(db *gorm.DB, inheritFrom string) ([]*ConfigFileNodeModel, error) {
	var platFiles []*ConfigFileNodeModel
	columnsRet := "id, namespace,conf_type,conf_file, conf_file_lc,description,updated_by,created_at,updated_at"
	platFile := &ConfigFileDefModel{
		Namespace: c.Namespace,
		ConfType:  c.ConfType,
	}
	platRes := db.Debug().Table(platFile.TableName()).Select(columnsRet).Where(platFile)
	if c.ConfFile != "" {
		platRes = platRes.Where("conf_file = ?", c.ConfFile)
	}
	if c.LevelName == constvar.LevelPlat {
		// query plat
		err := platRes.Find(&platFiles).Error
		if err != nil {
			return nil, err
		}
		return platFiles, nil
		// } else if c.LevelName == constvar.LevelApp && c.BKBizID == c.LevelValue{
	} else if c.BKBizID != constvar.BKBizIDForPlat {
		var files []*ConfigFileNodeModel
		// query app
		sqlRes := db.Debug().Table(c.TableName()).Select(columnsRet).
			Where("namespace = ? and conf_type = ? and level_name = ? and level_value = ? and bk_biz_id = ?",
				c.Namespace, c.ConfType, c.LevelName, c.LevelValue, c.BKBizID)
		if c.ConfFile != "" {
			sqlRes = sqlRes.Where("conf_file = ?", c.ConfFile)
		}
		err := sqlRes.Find(&files).Error
		if err != nil {
			return nil, err
		}
		if inheritFrom == constvar.BKBizIDForPlat {
			// query plat
			err := platRes.Find(&platFiles).Error
			if err != nil {
				return nil, err
			}
			var filesNew []*ConfigFileNodeModel
			logger.Info("platFiles: %+v  appFiles: %+v", platFiles, files)
			for _, fb := range platFiles {
				flag := false
				for _, f := range files {
					if fb.Namespace == f.Namespace && fb.ConfType == f.ConfType && fb.ConfFile == f.ConfFile {
						// app 优先
						filesNew = append(filesNew, f)
						flag = true
						continue
					}
				}
				if !flag {
					filesNew = append(filesNew, fb)
				}
			}
			return filesNew, nil
		} else {
			return files, nil
		}
	} else {
		return nil, errors.Errorf("illegal params for level=%s bk_biz_id=%s", c.LevelName, c.BKBizID)
	}
}

// Detail 有 id 则根据 id 查，无 id 则根据 unique key 查
// 如果没查到，node 返回 nil，不返回 ErrorNotFound
func (c *ConfigFileNodeModel) Detail(db *gorm.DB) (*ConfigFileNodeModel, error) {
	var files []*ConfigFileNodeModel
	// query app
	columnsRet :=
		"id,namespace,bk_biz_id,conf_type,conf_file,level_name,level_value,conf_file_lc,description,updated_by,created_at,updated_at"
	sqlRes := db.Debug().Table(c.TableName()).Select(columnsRet)
	if c.ID == 0 {
		sqlRes = sqlRes.Where(c.UniqueWhere())
	} else {
		sqlRes = sqlRes.Where("id = ?", c.ID)
	}
	err := sqlRes.Find(&files).Error
	if err != nil {
		return nil, err
	} else if len(files) == 0 {
		return nil, nil
	} else {
		return files[0], nil
	}
}
