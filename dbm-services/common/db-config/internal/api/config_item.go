package api

import (
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/validate"

	"github.com/pkg/errors"
)

// BaseConfItemDef TODO
type BaseConfItemDef struct {
	// 配置项名称
	ConfName    string `json:"conf_name" form:"conf_name" validate:"required"`
	ConfValue   string `json:"conf_value" form:"conf_value"`
	Description string `json:"description" form:"description"`
	// 是否禁用，默认 0 表示启用. 1表示禁用
	FlagDisable int8 `json:"flag_disable" form:"flag_disable" example:"0"`
	// 是否锁定，默认 0 表上不锁定
	FlagLocked int8 `json:"flag_locked" form:"flag_locked" example:"0"`
	// 返回该 conf_name 的发布、应用状态. 1: 已发布未应用 2: 已应用
	Stage int8 `json:"stage" form:"stage" example:"0"`
}

// BaseConfItemResp TODO
type BaseConfItemResp struct {
	BaseConfItemDef
	BaseLevelDef
	// op_type 仅在返回差异config部分时有效
	OPType string `json:"op_type"`
}

// UpsertConfItem TODO
type UpsertConfItem struct {
	BaseConfItemDef
	OperationType
}

// UpsertConfItemsReq TODO
// 更新 app/module/cluster 的配置
type UpsertConfItemsReq struct {
	SaveConfItemsReq
	RequestType
	Revision string `json:"revision" form:"revision"`
}

// UpsertConfItemsResp TODO
type UpsertConfItemsResp struct {
	BKBizID string `json:"bk_biz_id"`
	BaseConfFileDef
	// 编辑配置文件，第一次保存返回 revision, 后续保存/发布 需传入 revision
	Revision    string `json:"revision"`
	IsPublished int8   `json:"is_published"`
}

// SaveConfItemsReq 直接保存 config node, 只针对无版本概念的 conf_type
type SaveConfItemsReq struct {
	BKBizIDDef
	// 保存时如果与下层级存在冲突，提示确认，用 confirm=1 重新请求
	Confirm int8 `json:"confirm" form:"confirm"`
	// 发布描述
	Description string `json:"description" form:"description"`
	BaseLevelDef
	UpLevelInfo
	ConfFileInfo ConfFileDef       `json:"conf_file_info" form:"conf_file_info"`
	ConfItems    []*UpsertConfItem `json:"conf_items" form:"conf_items"`
}

// Validate TODO
func (v *SaveConfItemsReq) Validate() error {
	if err := ValidateAppWithLevelName(v.BKBizID, v.LevelName, v.LevelValue); err != nil {
		return err
	}
	if err := validate.GoValidateStruct(*v, true); err != nil {
		return err
	}
	for _, c := range v.ConfItems {
		if err := validate.GoValidateStruct(*c, true); err != nil {
			return err
		}
	}
	return nil
}

// Validate TODO
func (v *UpsertConfItemsReq) Validate() error {
	if err := ValidateAppWithLevelName(v.BKBizID, v.LevelName, v.LevelValue); err != nil {
		return err
	}
	if err := validate.GoValidateStruct(*v, true); err != nil {
		return err
	}
	for _, c := range v.ConfItems {
		if err := validate.GoValidateStruct(*c, true); err != nil {
			return err
		}
	}
	return nil
}

// GetConfigItemsReq TODO
// 获取配置项信息，可用于平台、业务、模块、集群等个级别配置项获取。注意返回的结果是与上层级 merge 后的，但不会持久化成新版本
type GetConfigItemsReq struct {
	BKBizIDDef
	BaseConfFileDef
	BaseLevelDef
	UpLevelInfo
	// 返回的数据格式
	RespFormatDef
	// 指定要查询的 conf_name， 多个值以,分隔，为空表示查询该 conf_file 的所有conf_name
	ConfName string `json:"conf_name" form:"conf_name"`
} // @name GetConfigItemsReq

// GetConfigItemsResp TODO
type GetConfigItemsResp struct {
	BKBizID string `json:"bk_biz_id"`
	// Module   string `json:"module"`
	// Cluster  string `json:"cluster"`
	BaseLevelDef
	ConfFileResp `json:"conf_file_info"`
	// content is a {conf_name:conf_type} dict like {"a":1, "b":"string"}
	Content map[string]interface{} `json:"content"`
} // @name GetConfigItemsResp

// Validate TODO
func (v *GetConfigItemsReq) Validate() error {
	if err := ValidateAppWithLevelName(v.BKBizID, v.LevelName, v.LevelValue); err != nil {
		return err
	}
	if err := validate.GoValidateStruct(*v, true); err != nil {
		return err
	}
	return nil
}

// GenerateConfigReq TODO
// Description Generate config file request
type GenerateConfigReq struct {
	BaseConfigNode
	UpLevelInfo
	// method must be one of GenerateOnly|GenerateAndSave|GenerateAndPublish
	// `GenerateOnly`: generate merged config
	// `GenerateAndSave`: generate and save the merged config to db (snapshot).
	// `GenerateAndPublish`: generate and save the merged config to db, and mark it as published (release)
	Method string `json:"method" form:"method" validate:"required,enums" enums:"GenerateAndSave,GenerateAndPublish"`
	RespFormatDef
} // @name GenerateConfigReq

// GenerateConfigResp TODO
type GenerateConfigResp struct {
	BKBizID string `json:"bk_biz_id"`
	BaseLevelDef
	ConfFile string `json:"conf_file"`
	// content is a {conf_name:conf_type} dict like {"a":1, "b":"string"}
	Content map[string]interface{} `json:"content"`
	// version name for this config_file generation
	Revision string `json:"revision"`
} // @name GenerateConfigResp

// Validate TODO
func (v *GenerateConfigReq) Validate() error {
	if err := ValidateAppWithLevelName(v.BKBizID, v.LevelName, v.LevelValue); err != nil {
		return err
	}
	if err := validate.GoValidateStruct(*v, true); err != nil {
		return err
	}
	return nil
}

// ValidateAppWithLevelName TODO
func ValidateAppWithLevelName(bkBizID, levelName, levelValue string) error {
	if (bkBizID == constvar.BKBizIDForPlat && levelName != constvar.LevelPlat) ||
		(bkBizID != constvar.BKBizIDForPlat && levelName == constvar.LevelPlat) {
		return errors.New("bk_biz_id=0 should have level_name=plat")
	}
	if levelName == constvar.LevelApp && bkBizID != constvar.BKBizIDForPlat && levelValue != bkBizID {
		return errors.New("level_name=bk_biz_id should have bk_biz_id=level_value")
	}
	return nil
}
