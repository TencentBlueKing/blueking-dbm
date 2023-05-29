// Package model TODO
package model

import (
	"fmt"
	"sort"
	"strings"

	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"bk-dbconfig/pkg/util/serialize"
)

// ConfigFileBaseModel TODO
type ConfigFileBaseModel struct {
	ConfType  string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfFile  string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	Namespace string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
}

// ConfigItemBaseModel TODO
type ConfigItemBaseModel struct {
	ConfName    string `json:"conf_name" gorm:"column:conf_name;type:varchar(120);not null"`
	ConfValue   string `json:"conf_value" gorm:"conf_value:dbs;type:varchar(255);not null"`
	LevelName   string `json:"level_name" gorm:"column:level_name;type:varchar(120);not null"`
	LevelValue  string `json:"level_value" gorm:"column:level_value;type:varchar(120)"`
	ExtraInfo   string `json:"extra_info" gorm:"column:extra_info;type:text"`
	Description string `json:"description" gorm:"column:description;type:varchar(255)"`
	FlagDisable int8   `json:"flag_disable" gorm:"column:flag_disable;type:tinyint(4);default:0"`
	FlagLocked  int8   `json:"flag_locked" gorm:"column:flag_locked;type:tinyint(4);default:0"`
}

// CmdbInfoBase TODO
// tb_app_module_cluster
type CmdbInfoBase struct {
	ID          uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	BKBizID     string `json:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(120);not null"`
	Cluster     string `json:"cluster" gorm:"column:cluster;type:varchar(120)"`
	Module      string `json:"module" gorm:"column:module;type:varchar(120)"`
	DBZone      string `json:"dbzone" gorm:"column:dbzone;type:varchar(120)"`
	DBZoneInfo  string `json:"dbzone_info" gorm:"column:dbzone_info;type:varchar(255)"`
	Service     string `json:"service" gorm:"column:service;type:varchar(120)"`
	Description string `json:"description" gorm:"column:description;type:varchar(255)"`
	Status      int8   `json:"status" gorm:"column:status;type:tinyint;default:1"`
}

// String 用于打印
func (c *CmdbInfoBase) String() string {
	return fmt.Sprintf("CmdbInfoBase{ID:%d BKBizID:%s Cluster:%s Module:%s DBZone:%s Service:%s City:%s}",
		c.ID, c.BKBizID, c.Cluster, c.Module, c.DBZone, c.Service, c.Description)
}

// TableName TODO
func (c *CmdbInfoBase) TableName() string {
	return "tb_app_module_cluster"
}

// ConfigVersionedModel TODO
// tb_config_versioned
type ConfigVersionedModel struct {
	ID         uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	NodeID     uint64 `json:"node_id" gorm:"column:node_id;type:int"` // level node id
	BKBizID    string `json:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(120);not null"`
	ConfType   string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfFile   string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	Namespace  string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	LevelName  string `json:"level_name" gorm:"column:level_name;type:varchar(120)"`
	LevelValue string `json:"level_value" gorm:"column:level_value;type:varchar(120)"`
	Revision   string `json:"revision" gorm:"column:revision;type:varchar(120)"`
	ContentStr string `json:"content_str" gorm:"column:content_str;type:text"`
	// content_str 的 md5 值
	ContentMd5     string `json:"content_md5" gorm:"column:content_md5;type:varchar(60)"`
	ContentObj     string `json:"content_obj" gorm:"column:content_obj;type:blob"`
	IsPublished    int8   `json:"is_published" gorm:"column:is_published;type:tinyint"`
	IsApplied      int8   `json:"is_applied" gorm:"column:is_applied;type:tinyint"`
	PreRevision    string `json:"pre_revision" gorm:"column:pre_revision;type:varchar(120)"`
	RowsAffected   int    `json:"rows_affected" gorm:"column:rows_affected;type:int"`
	ContentObjDiff string `json:"content_obj_diff" gorm:"column:content_obj_diff;type:blob"`
	Module         string `json:"module" gorm:"column:module;type:varchar(120)"`
	Cluster        string `json:"cluster" gorm:"column:cluster;type varchar(120)"`
	Description    string `json:"description" gorm:"column:description;type:varchar(255)"`
	CreatedBy      string `json:"created_by" gorm:"column:created_by;type:varchar(120)"`
	BaseDatetime
}

// TableName TODO
func (c ConfigVersionedModel) TableName() string {
	return "tb_config_versioned"
}

// UniqueWhere TODO
// revision 控制是否添加 revision where条件，前提是 c.Revision != ""
func (c ConfigVersionedModel) UniqueWhere(revision bool) map[string]interface{} {
	uniqueWhere := map[string]interface{}{
		"bk_biz_id":   c.BKBizID,
		"namespace":   c.Namespace,
		"level_name":  c.LevelName,
		"level_value": c.LevelValue,
		"conf_type":   c.ConfType,
		"conf_file":   c.ConfFile,
	}
	if c.Revision != "" && revision {
		uniqueWhere["revision"] = c.Revision
	}
	return uniqueWhere
}

// ConfigVersioned TODO
type ConfigVersioned struct {
	Versioned   *ConfigVersionedModel
	Configs     []*ConfigModel   // unpacked ContentObj
	ConfigsDiff []*ConfigModelOp // unpacked ContentObjDiff
}

// Pack Configs object to Versioned(base64)
func (v *ConfigVersioned) Pack() error {
	confItems := make([]string, 0) // fileContent
	for _, c := range v.Configs {
		confItems = append(confItems, fmt.Sprintf("%s = %s", c.ConfName, c.ConfValue))
	}
	sort.Strings(confItems)
	fileContent := strings.Join(confItems, "\n")
	v.Versioned.ContentStr = fileContent
	v.Versioned.ContentMd5 = util.Str2md5(fileContent)
	if len(v.Configs) > 0 {
		if contentObj, err := serialize.SerializeToString(v.Configs, true); err != nil {
			return err
		} else {
			v.Versioned.ContentObj = contentObj
		}
	}
	if len(v.ConfigsDiff) > 0 {
		if diffContentObj, err := serialize.SerializeToString(v.ConfigsDiff, false); err != nil {
			return err
		} else {
			v.Versioned.ContentObjDiff = diffContentObj
		}
	}
	return nil
}

// UnPack Versioned(base64) to Configs object
func (v *ConfigVersioned) UnPack() error {
	if v.Versioned.ContentObj == "" {
		v.Configs = nil
	} else if err := serialize.UnSerializeString(v.Versioned.ContentObj, &v.Configs, true); err != nil {
		return err
	}
	if v.Versioned.ContentObjDiff == "" {
		// v.ConfigsDiff = nil
	} else if err := serialize.UnSerializeString(v.Versioned.ContentObjDiff, &v.ConfigsDiff, false); err != nil {
		return err
	}
	return nil
}

// HandleFlagEncrypt 加密
func (v *ConfigVersioned) HandleFlagEncrypt() (err error) {
	for _, c := range v.ConfigsDiff {
		if err = c.Config.HandleFlagEncrypt(); err != nil {
			logger.Errorf("version HandleFlagEncrypt %+v. Error: %w", c.Config, err)
			return err
		}
	}
	for _, c := range v.Configs {
		if err = c.HandleFlagEncrypt(); err != nil {
			return err
		}
	}
	return nil
}

// MayDecrypt TODO
func (v *ConfigVersioned) MayDecrypt() (err error) {
	for _, c := range v.ConfigsDiff {
		if err = c.Config.MayDecrypt(); err != nil {
			logger.Errorf("ConfigVersioned diffs MayDecrypt, Error: %w", err)
			return err
		}
	}
	for _, c := range v.Configs {
		if err = c.MayDecrypt(); err != nil {
			logger.Errorf("ConfigVersioned configs MayDecrypt, Error: %w", err)
			return err
		}
	}
	return nil
}

// ConfigFileDefModel TODO
// tb_config_file_def
type ConfigFileDefModel struct {
	ID                uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	Namespace         string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	ConfType          string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfTypeLC        string `json:"conf_type_lc" gorm:"column:conf_type_lc;type:varchar(60)"`
	ConfFile          string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	ConfFileLC        string `json:"conf_file_lc" gorm:"column:conf_file_lc;type:varchar(120)"`
	NamespaceInfo     string `json:"namespace_info" gorm:"column:namespace_info;type:varchar(120)"`
	LevelNames        string `json:"level_names" gorm:"column:level_names;type:varchar(255);not null"`
	LevelVersioned    string `json:"level_versioned" gorm:"column:level_versioned;type:varchar(120)"`
	VersionKeepLimit  int    `json:"version_keep_limit" gorm:"column:version_keep_limit;type:int;not null"`
	VersionKeepDays   int    `json:"version_keep_days" gorm:"column:version_keep_days;type:int;not null"`
	ConfNameValidate  int8   `json:"conf_name_validate" gorm:"column:conf_name_validate;type:tinyint;not null"`
	ConfValueValidate int8   `json:"conf_value_validate" gorm:"column:conf_value_validate;type:tinyint;not null"`
	// 严格按照定义的 value_type 类型返回
	ValueTypeStrict int8   `json:"value_type_strict" gorm:"column:value_type_strict;type:tinyint;not null"`
	ConfNameOrder   int8   `json:"conf_name_order" gorm:"column:conf_name_order;type:tinyint;not null"`
	Description     string `json:"description" gorm:"column:description;type:varchar(255)"`
	UpdatedBy       string `json:"updated_by" gorm:"column:updated_by;type:varchar(120)"`
	BaseDatetime

	LevelNameList []string `json:"level_name_list" gorm:"-"`
}

// TableName TODO
func (c ConfigFileDefModel) TableName() string {
	return "tb_config_file_def"
}

// UniqueWhere TODO
// 定义该表唯一键的查询条件
func (c ConfigFileDefModel) UniqueWhere() map[string]interface{} {
	uniqueWhere := map[string]interface{}{
		"namespace": c.Namespace,
		"conf_type": c.ConfType,
		"conf_file": c.ConfFile,
	}
	return uniqueWhere
}

// ConfigNameDefModel TODO
// tb_config_name_def
type ConfigNameDefModel struct {
	ID           uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	Namespace    string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	ConfType     string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfFile     string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	ConfName     string `json:"conf_name" gorm:"column:conf_name;type:varchar(120);not null"`
	ConfNameLC   string `json:"conf_name_lc" gorm:"column:conf_name_lc;type:varchar(120);not null"`
	ValueType    string `json:"value_type" gorm:"column:value_type;type:varchar(120)"`
	ValueDefault string `json:"value_default" gorm:"column:value_default;type:varchar(120)"`
	ValueAllowed string `json:"value_allowed" gorm:"column:value_allowed;type:varchar(120)"`
	ValueTypeSub string `json:"value_type_sub" gorm:"column:value_type_sub;type:varchar(60)"`
	FlagLocked   int8   `json:"flag_locked" gorm:"column:flag_locked;type:tinyint"`
	FlagEncrypt  int8   `json:"flag_encrypt" gorm:"column:flag_encrypt;type:tinyint"`
	// 0:enable, 1:disable
	FlagDisable int8 `json:"flag_disable" gorm:"column:flag_disable;type:tinyint"`
	// 1: 显式的公共配置 0:不会显式出现在配置文件的全量配置项, 2: 显式的公共配置且只读即 visible only when rendering
	FlagStatus int8 `json:"flag_status" gorm:"column:flag_status;type:tinyint"`

	NeedRestart  int8   `json:"need_restart" gorm:"column:need_restart;type:tinyint"`
	ValueFormula string `json:"value_formula" gorm:"column:value_formula;type:varchar(120)"`
	OrderIndex   int    `json:"order_index" gorm:"column:order_index;type:int"`
	SinceVersion string `json:"since_version" gorm:"column:since_version;type:varchar(120)"`
	Description  string `json:"description" gorm:"column:description;type:text"`
	Stage        int8   `json:"stage" gorm:"column:stage;type:tinyint"`
	BaseDatetime
}

// BaseAutoTimeModel TODO
type BaseAutoTimeModel struct {
	CreatedAt string `json:"created_at" gorm:"->;column:created_at;type:varchar(30)"`
	UpdatedAt string `json:"updated_at" gorm:"->;column:updated_at;type:varchar(30)"`
}

// TableName TODO
func (c ConfigNameDefModel) TableName() string {
	return "tb_config_name_def"
}

// UniqueWhere TODO
// 定义该表唯一键的查询条件
func (c ConfigNameDefModel) UniqueWhere() map[string]interface{} {
	uniqueWhere := map[string]interface{}{
		"namespace": c.Namespace,
		"conf_type": c.ConfType,
		"conf_file": c.ConfFile,
		"conf_name": c.ConfName,
	}
	return uniqueWhere
}

// IsReadOnly TODO
func (c ConfigNameDefModel) IsReadOnly() bool {
	if c.FlagStatus == 2 {
		return true
	}
	return false
}

// IsFormula TODO
func (c ConfigNameDefModel) IsFormula() bool {
	if c.ValueFormula != "" {
		return true
	}
	return false
}

// ConfigLevelDefModel TODO
// tb_config_level_def
type ConfigLevelDefModel struct {
	LevelName     string `json:"level_name" gorm:"column:level_name;type:varchar(120);not null"`
	LevelPriority int    `json:"level_priority" gorm:"column:level_priority;type:int;not null"`
	LevelNameCN   string `json:"level_name_cn" gorm:"column:level_name_cn;type:varchar(120);not null"`
}

// TableName TODO
func (c ConfigLevelDefModel) TableName() string {
	return "tb_config_level_def"
}

// ConfigOplogModel TODO
// tb_config_oplog
type ConfigOplogModel struct {
}

// TableName TODO
func (c ConfigOplogModel) TableName() string {
	return "tb_config_oplog"
}

// ConfigTaskModel TODO
// tb_config_task
type ConfigTaskModel struct {
}

// TableName TODO
func (c ConfigTaskModel) TableName() string {
	return "tb_config_task"
}

// ConfigFileNodeModel TODO
// tb_config_file_node
type ConfigFileNodeModel struct {
	ID          uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	BKBizID     string `json:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(120);not null"`
	Namespace   string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	LevelName   string `json:"level_name" gorm:"column:level_name;type:varchar(120)"`
	LevelValue  string `json:"level_value" gorm:"column:level_value;type:varchar(120)"`
	ConfType    string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfTypeLC  string `json:"conf_type_lc" gorm:"column:conf_type_lc;type:varchar(60)"`
	ConfFile    string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	ConfFileLC  string `json:"conf_file_lc" gorm:"column:conf_file_lc;type:varchar(120)"`
	Description string `json:"description" gorm:"column:description;type:varchar(255)"`
	UpdatedBy   string `json:"updated_by" gorm:"column:updated_by;type:varchar(120)"`
	BaseDatetime
}

// TableName TODO
func (c ConfigFileNodeModel) TableName() string {
	return "tb_config_file_node"
}

// UniqueWhere TODO
// 定义该表唯一键的查询条件
func (c ConfigFileNodeModel) UniqueWhere() map[string]interface{} {
	uniqueWhere := map[string]interface{}{
		"bk_biz_id":   c.BKBizID,
		"namespace":   c.Namespace,
		"conf_type":   c.ConfType,
		"conf_file":   c.ConfFile,
		"level_name":  c.LevelName,
		"level_value": c.LevelValue,
	}
	return uniqueWhere
}
