package model

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/pkg/util"

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

	BeforeImage api.ConfName `json:"before_image" gorm:"column:before_image;type:text"`
	AfterImage  api.ConfName `json:"after_image" gorm:"column:after_image;type:text"`

	OpUser    string      `json:"op_user" gorm:"column:op_user;type:varchar(120)"`
	OpType    string      `json:"op_type" gorm:"column:op_type;type:varchar(60)"`
	CreatedAt util.DBTime `json:"created_at" gorm:"->;column:created_at;type:varchar(30)"`
	UpdatedAt util.DBTime `json:"updated_at" gorm:"->;column:updated_at;type:varchar(30)"`
}

// TableName TODO
func (c *ConfNameChangesModel) TableName() string {
	return "tb_conf_name_changes"
}

// ConfNameChangesCreate 批量写入 conf_name_def 变更记录
func ConfNameChangesCreate(db *gorm.DB, changes []*ConfNameChangesModel) error {
	if len(changes) == 0 {
		return nil
	}
	return db.Omit("created_at", "updated_at").Create(&changes).Error
}

// QueryConfNameChanges 查询 conf_name_def 变更历史
// 按操作时间逆序 (id DESC)
func QueryConfNameChanges(db *gorm.DB, req *api.ConfNameChangesQueryReq) ([]*ConfNameChangesModel, error) {
	var changes []*ConfNameChangesModel
	query := db.Where("namespace = ?", req.Namespace)
	if len(req.ConfType) > 0 {
		query = query.Where("conf_type in ?", req.ConfType)
	}
	if len(req.ConfFile) > 0 {
		query = query.Where("conf_file in ?", req.ConfFile)
	}
	if req.Limit > 0 {
		query = query.Limit(req.Limit)
	}
	if req.Offset > 0 {
		query = query.Offset(req.Offset)
	}
	if err := query.Order("id DESC").Find(&changes).Error; err != nil {
		return nil, err
	}
	return changes, nil
}

// NewConfNameFromDef 从 ConfigNameDefModel 构建 ConfName 快照
func NewConfNameFromDef(c *ConfigNameDefModel) api.ConfName {
	return api.ConfName{
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
