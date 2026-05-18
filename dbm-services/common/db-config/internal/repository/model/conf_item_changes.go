package model

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/pkg/util"

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

	BeforeImage api.ConfItem `json:"before_image" gorm:"column:before_image;type:text"`
	AfterImage  api.ConfItem `json:"after_image" gorm:"column:after_image;type:text"`

	OpUser    string      `json:"op_user" gorm:"column:op_user;type:varchar(120)"`
	OpType    string      `json:"op_type" gorm:"column:op_type;type:varchar(60)"`
	CreatedAt util.DBTime `json:"created_at" gorm:"->;column:created_at;type:varchar(30)"`
	UpdatedAt util.DBTime `json:"updated_at" gorm:"->;column:updated_at;type:varchar(30)"`
}

// TableName TODO
func (c *ConfItemChangesModel) TableName() string {
	return "tb_conf_item_changes"
}

// NewConfItemFromModel 从 ConfigModel 构建 ConfItem 快照
func NewConfItemFromModel(c *ConfigModel) api.ConfItem {
	return api.ConfItem{
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

// QueryConfItemChanges 查询 conf_item 变更历史
func QueryConfItemChanges(db *gorm.DB, req *api.ConfItemChangesQueryReq) ([]*ConfItemChangesModel, error) {
	var changes []*ConfItemChangesModel
	query := db.Where("bk_biz_id = ? AND namespace = ?", req.BKBizID, req.Namespace)
	if len(req.ConfType) > 0 {
		query = query.Where("conf_type in ?", req.ConfType)
	}
	if len(req.ConfFile) > 0 {
		query = query.Where("conf_file in ?", req.ConfFile)
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
