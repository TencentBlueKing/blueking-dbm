package api

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"

	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
)

// ConfNameChangesQueryReq 查询 conf_name_def 变更历史的请求参数
type ConfNameChangesQueryReq struct {
	Namespace string   `json:"namespace" form:"namespace" binding:"required"`
	ConfType  []string `json:"conf_type" form:"conf_type"`
	ConfFile  []string `json:"conf_file" form:"conf_file"`
	// Limit 当>0 时启用后端分页。每页返回条数
	Limit int `json:"limit"`
	// Offset 当>0 时启用后端分页。偏移量表示第几页
	Offset int `json:"offset"`
}

// ConfNameChangesQueryRowResp 查询 conf_name_def 变更历史的返回参数
// copy from model.ConfNameChangesModel
type ConfNameChangesQueryRowResp struct {
	ID        uint64 `json:"id"`
	Namespace string `json:"namespace"`
	ConfType  string `json:"conf_type"`
	ConfFile  string `json:"conf_file"`
	ConfName  string `json:"conf_name"`

	BeforeImage ConfName    `json:"before_image"`
	AfterImage  ConfName    `json:"after_image"`
	OpUser      string      `json:"op_user"`
	OpType      string      `json:"op_type"`
	CreatedAt   util.DBTime `json:"created_at"`
	UpdatedAt   util.DBTime `json:"updated_at"`

	ConfigFileDesc
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
	if len(b) == 0 {
		return nil
	}
	err := json.Unmarshal(b, c)
	if err != nil {
		logger.Error("ConfName.Scan: error parsing JSON: %w", err)
	}
	return err
}
