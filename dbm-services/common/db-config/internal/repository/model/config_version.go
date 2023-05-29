package model

import (
	"fmt"
	"time"

	"bk-dbconfig/pkg/util"

	"github.com/pkg/errors"
	"gorm.io/gorm"

	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/serialize"
)

// ListConfigFileVersions TODO
// 模块集群 的版本发布历史
// 平台、业务 的配置文件，可能有多个版本
func (c *ConfigVersionedModel) ListConfigFileVersions(app bool) ([]*ConfigVersionedModel, error) {
	var sqlRes *gorm.DB
	versions := make([]*ConfigVersionedModel, 0)
	sqlRes = DB.Self.Debug().Model(ConfigVersionedModel{}).Order("created_at desc").
		Select("revision", "conf_file", "created_at", "created_by", "rows_affected", "description", "is_published")
	if app {
		sqlRes.Where(
			"bk_biz_id = ? and namespace = ? and level_name = ? and level_value = ? and conf_type = ? and conf_file = ?",
			c.BKBizID, c.Namespace, c.LevelName, c.LevelValue, c.ConfType, c.ConfFile).Find(&versions)
	} else {
		sqlRes.Where(c.UniqueWhere(false)).Find(&versions)
	}
	if err := sqlRes.Error; err != nil {
		if err != gorm.ErrRecordNotFound {
			return nil, err
		}
	}
	return versions, nil
}

// GetDetail TODO
// 获取 revision 详情
func (c *ConfigVersionedModel) GetDetail(db *gorm.DB, versionList []string) (*ConfigVersioned, error) {
	var sqlRes *gorm.DB
	sqlRes = db.Debug().Model(ConfigVersionedModel{}).Where(c.UniqueWhere(true))
	if c.ID != 0 {
		sqlRes = sqlRes.Where("id = ?", c.ID)
	}
	sqlRes = sqlRes.Find(&c)
	if err := sqlRes.Error; err != nil {
		if err != gorm.ErrRecordNotFound {
			return nil, err
		}
	}
	versioned := &ConfigVersioned{Versioned: c}
	if err := versioned.UnPack(); err != nil {
		return nil, err
	}
	return versioned, nil
}

// GetVersionedConfigFile TODO
// level_value is cluster
func (c *ConfigVersionedModel) GetVersionedConfigFile(db *gorm.DB, versionList []string) ([]*ConfigVersionedModel,
	error) {
	var sqlRes *gorm.DB
	versions := make([]*ConfigVersionedModel, 0)
	logger.Info("GetVersionedConfigFile ConfigVersionedModel=%+v", c)
	if (c.ID == 0) && (c.BKBizID == "" || c.ConfType == "" || c.ConfFile == "" || c.LevelValue == "") {
		return nil, fmt.Errorf("GetVersionedConfigFile wrong params")
	}
	// .Select("revision", "is_published", "content", "content_md5", "content_obj")
	sqlRes = db.Debug().Model(ConfigVersionedModel{}).Where(c.UniqueWhere(false))
	if c.ID != 0 {
		sqlRes = sqlRes.Where("id = ?", c.ID)
	}
	if c.IsPublished == 1 {
		sqlRes = sqlRes.Where("is_published = ?", c.IsPublished)
	}
	if c.IsApplied == 1 {
		sqlRes = sqlRes.Where("is_applied = ?", c.IsApplied)
	}
	if len(versionList) > 0 {
		sqlRes = sqlRes.Where("revision in ?", versionList)
	} // else query all versions
	sqlRes = sqlRes.Find(&versions)
	if err := sqlRes.Error; err != nil {
		if err != gorm.ErrRecordNotFound {
			return nil, err
		}
	}
	return versions, nil
}

// UpdateConfigVersioned TODO
func (c *ConfigVersionedModel) UpdateConfigVersioned() error {
	return nil
}

// SaveConfigVersioned TODO
func (c *ConfigVersionedModel) SaveConfigVersioned(db *gorm.DB) error {
	if id, err := RecordExists(db, c.TableName(), c.ID, c.UniqueWhere(true)); err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			if err := db.Create(c).Error; err != nil {
				logger.Errorf("Save fail2:%v, err:%s", *c, err.Error())
				return err
			}
			return nil
		}
		return err
	} else {
		c.ID = id
		sqlRes := db.Table(c.TableName()).Updates(c).Where(c.UniqueWhere(true))
		if sqlRes.Error != nil {
			return sqlRes.Error
		}
		return nil
	}
}

// FormatAndSaveConfigVersioned TODO
// 生成 version，但不发布. is_published=false, is_applied=false
func (c *ConfigVersionedModel) FormatAndSaveConfigVersioned(db *gorm.DB,
	configs []*ConfigModel, configsDiff []*ConfigModelOp) (string, error) {
	// format: content versioned to save, list
	if c.Revision == "" {
		c.Revision = c.NewRevisionName()
	}
	if c.PreRevision == "" {
		// 需要把当前已发布的版本作为 pre_revision
		if publishedVersion, err := c.GetVersionPublished(db); err != nil {
			if !errors.Is(err, gorm.ErrRecordNotFound) {
				return "", err
			}
			logger.Warnf("no published pre_revision found %+v", c)
		} else {
			c.PreRevision = publishedVersion.Versioned.Revision
		}
	}
	vc := &ConfigVersioned{
		Versioned:   c,
		Configs:     configs,
		ConfigsDiff: configsDiff,
	}
	if err := vc.HandleFlagEncrypt(); err != nil {
		return "", err
	}
	if err := vc.Pack(); err != nil {
		return "", err
	}
	// 获取 node_id，用于关联
	if c.NodeID == 0 {
		fn := &ConfigFileNodeModel{
			Namespace:  c.Namespace,
			ConfType:   c.ConfType,
			ConfFile:   c.ConfFile,
			BKBizID:    c.BKBizID,
			LevelName:  c.LevelName,
			LevelValue: c.LevelValue,
		}
		if fnNew, err := fn.Detail(db); fnNew != nil && err == nil {
			c.NodeID = fnNew.ID
		} else if err == gorm.ErrRecordNotFound {
			if nodeID, err := fn.CreateOrUpdate(true, db); err != nil {
				return "", err
			} else {
				c.NodeID = nodeID
			}
			/*
			   errInfo := fmt.Sprintf("bk_biz_id=%s,namespace=%s,conf_type=%s,conf_file=%s,level_name=%s,level_value=%s",
			       c.BKBizID, c.Namespace, c.ConfType, c.ConfFile, c.LevelName, c.LevelValue)
			   logger.Errorf("node_id not found: %s", errInfo)
			   return "", errors.Wrap(errno.ErrNodeNotFound, errInfo)
			*/
		}
	}
	if err := c.SaveConfigVersioned(db); err != nil {
		return "", err
	}
	logger.Info("FormatAndSaveConfigVersioned: v=%s id=%d", c.Revision, c.ID)
	return c.Revision, nil
}

// GetConfigFileConfigs TODO
// get configModels from contentObj that need unSerializing
// not get from db
func (c *ConfigVersionedModel) GetConfigFileConfigs() ([]*ConfigModel, error) {
	configs := make([]*ConfigModel, 0)
	if err := serialize.UnSerializeString(c.ContentObj, &configs, true); err != nil {
		return nil, err
	}
	return configs, nil
}

// NewRevisionName TODO
// auto set revision name with current time
func (c *ConfigVersionedModel) NewRevisionName() string {
	t := time.Now()
	s := t.Format("20060102150405")
	revision := fmt.Sprintf("v_%s", s)
	c.Revision = revision
	return revision
}

// PatchConfigVersioned TODO
// patch config.Content. not save to db
func (c *ConfigVersionedModel) PatchConfigVersioned(patch map[string]string) error {
	// logger.Warnf("PatchConfigVersioned:%+v, patch:%v", c, patch)
	configs := make([]*ConfigModel, 0)
	var err error
	if configs, err = c.GetConfigFileConfigs(); err != nil {
		return err
	}
	for k, v := range patch {
		for _, i := range configs {
			if k == i.ConfName {
				if !util.ConfValueIsPlaceHolder(i.ConfValue) {
					return fmt.Errorf("cannot patch conf_name=%s conf_value=%s to v=%s", i.ConfName, i.ConfValue, v)
				} else {
					i.ConfValue = v // patch value only startswith {{
				}
			}
			if err := i.HandleFlagEncrypt(); err != nil {
				return err
			}
		}
	}
	c.RowsAffected += len(patch)
	vc := ConfigVersioned{Versioned: c, Configs: configs, ConfigsDiff: nil}
	if err = vc.Pack(); err != nil {
		return err
	}
	return nil
}

// VersionApplyStatus 修改版本状态为 已应用
// 只用户发布版本，之前已生成revision
// c 里面用到在字段 unique, revision
// 每次应用完之后，都是 is_published=1, is_applied=1
// 如果是 level_config 应用，则给所有下级发布新的配置版本
func (c *ConfigVersionedModel) VersionApplyStatus(db *gorm.DB) error {
	if c.Revision == "" {
		return fmt.Errorf("revision to apply cannot be empty: %+v", c)
	}
	// 判断是否是否已发布
	where := c.UniqueWhere(true)
	where["is_published"] = 1
	if _, err := RecordExists(db, c.TableName(), 0, where); errors.Is(err, gorm.ErrRecordNotFound) {
		return errors.Errorf("版本应用必须是已发布: %s", c.Revision)
	}
	// 获取已应用的配置版本
	var verObj *ConfigVersionedModel // queried from db
	sqlRes := db.Model(c).
		Where(c.UniqueWhere(false)).Where("is_applied = ?", 1).
		Select("id", "revision", "is_applied", "is_published").First(&verObj)
	if err := sqlRes.Error; err != nil {
		if err == gorm.ErrRecordNotFound { // ignore no record found
			logger.Warnf("applied version not found: %+v", c)
		} else {
			return err
		}
	} else {
		if verObj.Revision == c.Revision {
			return fmt.Errorf("revision is applied already: %s", c.Revision)
		}
	}
	logger.Warnf("ApplyConfigVersioned get:%+v", c)
	versionBefore := ConfigVersionedModel{
		BKBizID:    c.BKBizID,
		Namespace:  c.Namespace,
		LevelName:  c.LevelName,
		LevelValue: c.LevelValue,
		ConfFile:   c.ConfFile,
		ConfType:   c.ConfType,
	}
	versionNew := versionBefore
	versionNew.Revision = c.Revision
	//    versionNew.ID = verObj.ID

	// 已应用版本，变为 0
	if err := db.Debug().Table(c.TableName()).Where(&versionBefore).Where("is_applied = ?", 1).
		Select("is_applied").Update("is_applied", 0).Error; err != nil {
		if err != gorm.ErrRecordNotFound { // ignore no record found
			return err
		}
	}
	// 把将应用版本变为 1
	if err := db.Debug().Table(c.TableName()).Where(&versionNew).
		Select("is_applied").Update("is_applied", 1).Error; err != nil {
		return err
	}
	return nil
}

// PublishConfig TODO
// 只发布版本，之前已生成revision. is_published=true
// c 里面用到在字段 unique, revision
func (c *ConfigVersionedModel) PublishConfig(db *gorm.DB) (err error) {
	if c.Revision == "" {
		return fmt.Errorf("revision to publish cannot be empty: %+v", c)
	}
	// 获取已发布的配置版本
	var verObj *ConfigVersionedModel // queried from db
	sqlRes := db.Model(c).
		Where(c.UniqueWhere(false)).Where("is_published = ?", 1).
		Select("id", "revision", "is_applied", "is_published").First(&verObj)
	if err = sqlRes.Error; err != nil {
		if err == gorm.ErrRecordNotFound { // ignore no record found
			logger.Warnf("published version not found: %+v", c)
		} else {
			return err
		}
	}

	if verObj.Revision == c.Revision {
		return fmt.Errorf("revision is applied already: %s", c.Revision)
	}
	// logger.Warnf("PublishConfigVersioned get:%+v", c)
	versionBefore := ConfigVersionedModel{
		BKBizID:    c.BKBizID,
		Namespace:  c.Namespace,
		LevelName:  c.LevelName,
		LevelValue: c.LevelValue,
		ConfFile:   c.ConfFile,
		ConfType:   c.ConfType,
	}
	versionNew := versionBefore
	versionNew.Revision = c.Revision
	versionNew.ID = c.ID

	// 已发布版本，变为 0
	if err = db.Debug().Table(c.TableName()).Where(&versionBefore).Where("is_published = ?", 1).
		Select("is_published").Update("is_published", 0).Error; err != nil {
		if err != gorm.ErrRecordNotFound { // ignore no record found
			return err
		}
	}
	// 把将发布版本变为 1
	if err = db.Debug().Table(c.TableName()).Where(&versionNew).
		Select("is_published").Update("is_published", 1).Error; err != nil {
		return err
	}
	return
}

// PatchConfig TODO
// 只用户发布版本，之前已生成revision. is_published=true, is_applied=false
func (c *ConfigVersionedModel) PatchConfig(db *gorm.DB, patch map[string]string) error {
	if c.Revision == "" {
		return fmt.Errorf("revision to patch cannot be empty: %+v", c)
	} else if patch == nil || len(patch) == 0 {
		return fmt.Errorf("no patch items givien")
	}
	// check if c exists
	var verObj *ConfigVersionedModel // queried from db
	sqlRes := db.Model(c).Where(c.UniqueWhere(true)).First(&verObj)
	if err := sqlRes.Error; err != nil {
		if err != gorm.ErrRecordNotFound { // ignore no record found
			logger.Warnf("patch version not found: %+v", c)
			return err
		}
	}
	logger.Warnf("PatchConfigVersioned get:%+v", c)
	if err := verObj.PatchConfigVersioned(patch); err != nil {
		return err
	}
	if err := verObj.SaveConfigVersioned(db); err != nil {
		return err
	}
	return nil
}

// Update update 指定字段
// 如果 where=nil, updates=nil, 直接 update c
// 如果 where=nil, c 则作为条件
// 如果 updates=nil, c 则作为 update 内容
// 如果有 columns, 则 update 指定字段
func (c *ConfigVersionedModel) Update(db *gorm.DB, where map[string]interface{}, updates map[string]interface{},
	columns ...string) error {
	// save c
	if where == nil && updates == nil {
		return db.Updates(c).Error
	}
	sqlRes := db.Debug().Table(c.TableName())
	if where == nil {
		sqlRes = sqlRes.Where(c)
	} else {
		sqlRes = sqlRes.Where(where)
	}
	if len(columns) > 0 {
		sqlRes = sqlRes.Select(columns)
	}
	if updates == nil {
		sqlRes = sqlRes.Updates(c)
	} else {
		sqlRes = sqlRes.Updates(updates)
	}
	if err := sqlRes.Error; err != nil {
		if err != gorm.ErrRecordNotFound { // ignore no record found
			return err
		}
	}
	return nil
}
