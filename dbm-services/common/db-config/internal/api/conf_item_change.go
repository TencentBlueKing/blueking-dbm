package api

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"

	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
)

// ConfItemChangesQueryReq 查询 conf_item 变更历史的请求参数
type ConfItemChangesQueryReq struct {
	BKBizID    string   `json:"bk_biz_id" form:"bk_biz_id" binding:"required"`
	Namespace  string   `json:"namespace" form:"namespace" binding:"required"`
	ConfType   []string `json:"conf_type" form:"conf_type"`
	ConfFile   []string `json:"conf_file" form:"conf_file"`
	LevelName  string   `json:"level_name" form:"level_name"`
	LevelValue string   `json:"level_value" form:"level_value"`
	// Limit 当>0 时启用后端分页。每页返回条数
	Limit int `json:"limit"`
	// Offset 当>0 时启用后端分页。偏移量表示第几页
	Offset int `json:"offset"`
}

// ConfItemChangesQueryRowResp 查询 conf_item 变更历史的返回参数
// copy from model.ConfItemChangesModel
type ConfItemChangesQueryRowResp struct {
	ID         uint64 `json:"id" `
	BKBizID    string `json:"bk_biz_id"`
	Namespace  string `json:"namespace"`
	ConfType   string `json:"conf_type"`
	ConfFile   string `json:"conf_file"`
	ConfName   string `json:"conf_name"`
	LevelName  string `json:"level_name"`
	LevelValue string `json:"level_value"`

	BeforeImage ConfItem    `json:"before_image"`
	AfterImage  ConfItem    `json:"after_image"`
	OpUser      string      `json:"op_user"`
	OpType      string      `json:"op_type"`
	CreatedAt   util.DBTime `json:"created_at"`
	UpdatedAt   util.DBTime `json:"updated_at"`

	ConfigFileDesc
	ConfNameLc string `json:"conf_name_lc"`
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
	if len(b) == 0 {
		return nil
	}
	err := json.Unmarshal(b, c)
	if err != nil {
		logger.Error("ConfItem.Scan: error parsing JSON: %w", err)
	}
	return err
}
