package model

import "fmt"

// ConfigModel TODO
// tb_config_node
type ConfigModel struct {
	ID          uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	NodeID      uint64 `json:"node_id" gorm:"column:node_id;type:int"`
	BKBizID     string `json:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(120);not null"`
	Namespace   string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	ConfType    string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfFile    string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	ConfName    string `json:"conf_name" gorm:"column:conf_name;type:varchar(120);not null"`
	ConfValue   string `json:"conf_value" gorm:"conf_value:dbs;type:varchar(255);not null"`
	LevelName   string `json:"level_name" gorm:"column:level_name;type:varchar(120);not null"`
	LevelValue  string `json:"level_value" gorm:"column:level_value;type:varchar(120)"`
	Description string `json:"description" gorm:"column:description;type:varchar(255)"`
	FlagDisable int8   `json:"flag_disable" gorm:"column:flag_disable;type:tinyint(4);default:0"`
	FlagLocked  int8   `json:"flag_locked" gorm:"column:flag_locked;type:tinyint(4);default:0"`
	// 是哪个发布版本进行的修改
	UpdatedRevision string `json:"updated_revision" gorm:"column:updated_revision;type:varchar(120)"`
	Stage           int8   `json:"stage" gorm:"column:stage;type:tinyint"`
	BaseDatetime
}

// TableName TODO
func (c *ConfigModel) TableName() string {
	return "tb_config_node"
}

// String 用于打印
func (c *ConfigModel) String() string {
	return fmt.Sprintf(
		"ConfigModel{ID:%d BKBizID:%s Namespace:%s ConfType:%s ConfFile:%s ConfName:%s ConfValue:%s LevelName:%s LevelValue:%s Description:%s FlagDisable:%d TimeCreated:%s TimeUpdated:%s}",
		c.ID, c.BKBizID, c.Namespace, c.ConfType, c.ConfFile, c.ConfName, c.ConfValue, c.LevelName, c.LevelValue,
		c.Description, c.FlagDisable, c.CreatedAt, c.UpdatedAt)
}

// UniqueWhere TODO
func (c *ConfigModel) UniqueWhere() map[string]interface{} {
	uniqueWhere := map[string]interface{}{
		"bk_biz_id":   c.BKBizID,
		"namespace":   c.Namespace,
		"conf_file":   c.ConfFile,
		"conf_name":   c.ConfName,
		"level_name":  c.LevelName,
		"level_value": c.LevelValue,
		// "conf_type": c.ConfType,
	}
	return uniqueWhere
}

// ConfigModelOp TODO
type ConfigModelOp struct {
	Config *ConfigModel
	// config model 操作类型, add,delete,update, delete_ref
	OPType string `json:"op_type"`
}

// ConfigModelVOp will replace ConfigModelOp
type ConfigModelVOp struct {
	Config *ConfigModelView
	// config model 操作类型, add,delete,update, delete_ref
	OPType string `json:"op_type"`
}

// ConfigModelView TODO
// v_tb_config_node
type ConfigModelView struct {
	ConfigModel
	Cluster string `json:"cluster" gorm:"column:cluster;type:varchar(120)"`
	Module  string `json:"module" gorm:"column:module;type:varchar(120)"`
	// todo used to replace Cluster Module, 用户存放改item的上层信息
	UpLevelInfo map[string]string `json:"up_level_info"`
}
