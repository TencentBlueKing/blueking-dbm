package model

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"

	"gorm.io/gorm"
)

// ConfNameChangesModel 配置项 定义的变更记录
// 一个配置项，以 Namespace,ConfType,ConfFile,ConfName 为唯一键
type ConfNameChangesModel struct {
	ID        uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	Namespace string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	ConfType  string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	ConfFile  string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	ConfName  string `json:"conf_name" gorm:"column:conf_name;type:varchar(120);not null"`

	BeforeImage ConfName `json:"before_image" gorm:"column:before_image;type:varchar(255)"`
	AfterImage  ConfName `json:"after_image" gorm:"column:after_image;type:varchar(255)"`

	OpUser string `json:"op_user" gorm:"column:op_user;type:varchar(120)"`
	OpType string `json:"op_type" gorm:"column:op_type;type:varchar(60)"`
	BaseDatetime
}

// TableName TODO
func (c *ConfNameChangesModel) TableName() string {
	return "tb_conf_name_changes"
}

// ConfName 一个配置项的可修改内容
// 总体与 ConfigNameDefModel 对齐
type ConfName struct {
	ConfNameLC   string `json:"conf_name_lc"`
	ValueType    string `json:"value_type"`
	ValueDefault string `json:"value_default"`
	ValueAllowed string `json:"value_allowed"`
	ValueTypeSub string `json:"value_type_sub"`

	FlagVisible  int8 `json:"flag_visible"`
	FlagReadonly int8 `json:"flag_readonly"`
	FlagLocked   int8 `json:"flag_locked"`
	FlagEncrypt  int8 `json:"flag_encrypt"`
	// 0:enable, 1:disable
	FlagDisable int8 `json:"flag_disable"`

	NeedRestart  int8   `json:"need_restart"`
	SinceVersion string `json:"since_version"`
	Description  string `json:"description"`
}

// Value 实现 driver.Valuer 接口，将 ConfName 序列化为 JSON 字符串存入数据库
func (c ConfName) Value() (driver.Value, error) {
	b, err := json.Marshal(c)
	if err != nil {
		return nil, err
	}
	return string(b), nil
}

// Scan 实现 sql.Scanner 接口，从数据库读取 JSON 字符串反序列化为 ConfName
func (c *ConfName) Scan(value interface{}) error {
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
		return fmt.Errorf("ConfName.Scan: unsupported type %T", value)
	}
	return json.Unmarshal(b, c)
}

// ConfNameChangesCreate 批量写入 conf_name_def 变更记录
func ConfNameChangesCreate(db *gorm.DB, changes []*ConfNameChangesModel) error {
	if len(changes) == 0 {
		return nil
	}
	return db.Omit("created_at", "updated_at").Create(&changes).Error
}

// ConfNameChangesQueryReq 查询 conf_name_def 变更历史的请求参数
type ConfNameChangesQueryReq struct {
	Namespace string `json:"namespace" form:"namespace" binding:"required"`
	ConfType  string `json:"conf_type" form:"conf_type"`
	ConfFile  string `json:"conf_file" form:"conf_file"`
}

// QueryConfNameChanges 查询 conf_name_def 变更历史
func QueryConfNameChanges(db *gorm.DB, req *ConfNameChangesQueryReq) ([]*ConfNameChangesModel, error) {
	var changes []*ConfNameChangesModel
	query := db.Where("namespace = ?", req.Namespace)
	if req.ConfType != "" {
		query = query.Where("conf_type = ?", req.ConfType)
	}
	if req.ConfFile != "" {
		query = query.Where("conf_file = ?", req.ConfFile)
	}
	if err := query.Order("id DESC").Find(&changes).Error; err != nil {
		return nil, err
	}
	return changes, nil
}

// NewConfNameFromDef 从 ConfigNameDefModel 构建 ConfName 快照
func NewConfNameFromDef(c *ConfigNameDefModel) ConfName {
	return ConfName{
		ConfNameLC:   c.ConfNameLC,
		ValueType:    c.ValueType,
		ValueDefault: c.ValueDefault,
		ValueAllowed: c.ValueAllowed,
		ValueTypeSub: c.ValueTypeSub,
		FlagVisible:  c.FlagVisible,
		FlagReadonly: c.FlagReadonly,
		FlagLocked:   c.FlagLocked,
		FlagEncrypt:  c.FlagEncrypt,
		FlagDisable:  c.FlagDisable,
		NeedRestart:  c.NeedRestart,
		SinceVersion: c.SinceVersion,
		Description:  c.Description,
	}
}
