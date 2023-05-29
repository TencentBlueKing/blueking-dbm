package model

import (
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// ExistsAppliedVersion 是否存在已发布的 version
// 可用户判断是否已经 generate, 不存在 applied 时 error 返回 nil
func (c *ConfigVersionedModel) ExistsAppliedVersion(db *gorm.DB) (bool, error) {
	where := map[string]interface{}{
		"bk_biz_id":   c.BKBizID,
		"namespace":   c.Namespace,
		"conf_type":   c.ConfType,
		"conf_file":   c.ConfFile,
		"level_name":  c.LevelName,
		"level_value": c.LevelValue,
		"is_applied":  1,
	}
	if _, err := RecordExists(db, c.TableName(), 0, where); err != nil {
		if err == gorm.ErrRecordNotFound {
			return false, nil
		} else {
			return false, err
		}
	} else {
		return true, nil
	}
}

// GetVersion 获取 ConfigVersionedModel
// 如果不存在，则返回 NotFound
func (c *ConfigVersionedModel) GetVersion(db *gorm.DB, where map[string]interface{}) (*ConfigVersioned, error) {
	versioned := &ConfigVersionedModel{}
	sqlRes := db.Table(c.TableName()).Where(c.UniqueWhere(true))
	if where != nil {
		sqlRes = sqlRes.Where(where)
	}
	err := sqlRes.First(&versioned).Error
	if err != nil {
		return nil, err
	}
	v := &ConfigVersioned{Versioned: versioned}
	if err := v.UnPack(); err != nil {
		return nil, err
	}
	if err := v.MayDecrypt(); err != nil {
		return nil, err
	}
	return v, nil
}

// GetVersionApplied 获取已应用版本
func (c *ConfigVersionedModel) GetVersionApplied(db *gorm.DB) (*ConfigVersioned, error) {
	// c.Revision = ""
	where := map[string]interface{}{"is_applied": 1}
	if v, err := c.GetVersion(db, where); err != nil {
		return nil, errors.Wrap(err, "get applied config")
	} else {
		return v, nil
	}
}

// GetVersionPublished 获取已发布版本
func (c *ConfigVersionedModel) GetVersionPublished(db *gorm.DB) (*ConfigVersioned, error) {
	// c.Revision = ""
	where := map[string]interface{}{"is_published": 1}
	if v, err := c.GetVersion(db, where); err != nil {
		return nil, errors.Wrap(err, "get published config")
	} else {
		return v, nil
	}
}

// BatchGetVersion TODO
func (c *ConfigVersionedModel) BatchGetVersion(levelValues []string, db *gorm.DB) (
	[]*ConfigVersionedModel, []*ConfigVersionedModel, error) {
	where := map[string]interface{}{
		"bk_biz_id":   c.BKBizID,
		"namespace":   c.Namespace,
		"conf_file":   c.ConfFile,
		"level_name":  c.LevelName,
		"level_value": levelValues,
	}

	published := make([]*ConfigVersionedModel, 0)
	publishedRes := db.Table(c.TableName()).
		Select("id", "level_value", "revision", "is_published", "is_applied").
		Where(where).Where("is_published", 1).Find(&published)
	if publishedRes.Error != nil {
		return nil, nil, publishedRes.Error
	}

	applied := make([]*ConfigVersionedModel, 0)
	appliedRes := db.Table(c.TableName()).
		Select("id", "level_value", "revision", "is_published", "is_applied").
		Where(where).Where("is_applied", 1).Find(&applied)
	if appliedRes.Error != nil {
		return nil, nil, appliedRes.Error
	}
	return published, applied, nil
}

// BatchGetPublished TODO
func (c *ConfigVersionedModel) BatchGetPublished(levelValues []string, db *gorm.DB) ([]*ConfigVersionedModel, error) {
	where := map[string]interface{}{
		"bk_biz_id":   c.BKBizID,
		"namespace":   c.Namespace,
		"conf_file":   c.ConfFile,
		"level_name":  c.LevelName,
		"level_value": levelValues,
	}

	published := make([]*ConfigVersionedModel, 0)
	publishedRes := db.Table(c.TableName()).
		Select("id", "level_value", "revision", "is_published", "is_applied").
		Where(where).Where("is_published", 1).Find(&published)
	if publishedRes.Error != nil {
		return nil, publishedRes.Error
	}
	return published, nil
}

// BatchGetApplied TODO
func (c *ConfigVersionedModel) BatchGetApplied(levelValues []string, db *gorm.DB) ([]*ConfigVersionedModel, error) {
	where := map[string]interface{}{
		"bk_biz_id":   c.BKBizID,
		"namespace":   c.Namespace,
		"conf_file":   c.ConfFile,
		"level_name":  c.LevelName,
		"level_value": levelValues,
	}

	applied := make([]*ConfigVersionedModel, 0)
	appliedRes := db.Table(c.TableName()).
		Select("id", "level_value", "revision", "is_published", "is_applied").
		Where(where).Where("is_applied", 1).Find(&applied)
	if appliedRes.Error != nil {
		return nil, appliedRes.Error
	}
	return applied, nil
}
