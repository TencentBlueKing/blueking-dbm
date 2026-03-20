package model

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"

	"gorm.io/gorm"
)

// ConfItemChangesModel 一个集群/业务的配置项的变更记录
// 一个配置项，以 Namespace,ConfType,ConfFile,ConfName 为唯一键
type ConfItemChangesModel struct {
	ID         uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	BKBizID    string `json:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(120);not null"`
	Namespace  string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	ConfType   string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfFile   string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	ConfName   string `json:"conf_name" gorm:"column:conf_name;type:varchar(120);not null"`
	LevelName  string `json:"level_name" gorm:"column:level_name;type:varchar(120);not null"`
	LevelValue string `json:"level_value" gorm:"column:level_value;type:varchar(120)"`

	BeforeImage ConfItem `json:"before_image" gorm:"column:before_image;type:varchar(255)"`
	AfterImage  ConfItem `json:"after_image" gorm:"column:after_image;type:varchar(255)"`

	OpUser string `json:"op_user" gorm:"column:op_user;type:varchar(120)"`
	OpType string `json:"op_type" gorm:"column:op_type;type:varchar(60)"`
	BaseDatetime
}

// TableName TODO
func (c *ConfItemChangesModel) TableName() string {
	return "tb_conf_item_changes"
}

// ConfItem 一个配置项的可修改内容
// 总体与 ConfigModel 对齐
type ConfItem struct {
	ConfValue   string `json:"conf_value"`
	Description string `json:"description"`
	FlagDisable int8   `json:"flag_disable"`
	FlagLocked  int8   `json:"flag_locked"`
	// LevelFrom  配置项来源于哪一个层级. 用在记录 before_image
	LevelFrom string `json:"level_from"`
}

// Value 实现 driver.Valuer 接口，将 ConfItem 序列化为 JSON 字符串存入数据库
func (c ConfItem) Value() (driver.Value, error) {
	b, err := json.Marshal(c)
	if err != nil {
		return nil, err
	}
	return string(b), nil
}

// Scan 实现 sql.Scanner 接口，从数据库读取 JSON 字符串反序列化为 ConfItem
func (c *ConfItem) Scan(value interface{}) error {
	if value == nil {
		return nil
	}
	var b []byte
	switch v := value.(type) {
	case []byte:
		b = v
	case string:
		b = []byte(v)
	default:
		return fmt.Errorf("ConfItem.Scan: unsupported type %T", value)
	}
	return json.Unmarshal(b, c)
}

// NewConfItemFromModel 从 ConfigModel 构建 ConfItem 快照
func NewConfItemFromModel(c *ConfigModel) ConfItem {
	return ConfItem{
		ConfValue:   c.ConfValue,
		Description: c.Description,
		FlagDisable: c.FlagDisable,
		FlagLocked:  c.FlagLocked,
		LevelFrom:   c.LevelName,
	}
}

// ConfItemChangesCreate 批量写入 conf_item 变更记录
func ConfItemChangesCreate(db *gorm.DB, changes []*ConfItemChangesModel) error {
	if len(changes) == 0 {
		return nil
	}
	return db.Omit("created_at", "updated_at").Create(&changes).Error
}

// ConfItemChangesQueryReq 查询 conf_item 变更历史的请求参数
type ConfItemChangesQueryReq struct {
	BKBizID    string `json:"bk_biz_id" form:"bk_biz_id" binding:"required"`
	Namespace  string `json:"namespace" form:"namespace" binding:"required"`
	ConfType   string `json:"conf_type" form:"conf_type"`
	ConfFile   string `json:"conf_file" form:"conf_file"`
	LevelName  string `json:"level_name" form:"level_name"`
	LevelValue string `json:"level_value" form:"level_value"`
}

// QueryConfItemChanges 查询 conf_item 变更历史
func QueryConfItemChanges(db *gorm.DB, req *ConfItemChangesQueryReq) ([]*ConfItemChangesModel, error) {
	var changes []*ConfItemChangesModel
	query := db.Where("bk_biz_id = ? AND namespace = ?", req.BKBizID, req.Namespace)
	if req.ConfType != "" {
		query = query.Where("conf_type = ?", req.ConfType)
	}
	if req.ConfFile != "" {
		query = query.Where("conf_file = ?", req.ConfFile)
	}
	if req.LevelName != "" {
		query = query.Where("level_name = ?", req.LevelName)
	}
	if req.LevelValue != "" {
		query = query.Where("level_value = ?", req.LevelValue)
	}
	if err := query.Order("id DESC").Find(&changes).Error; err != nil {
		return nil, err
	}
	return changes, nil
}
