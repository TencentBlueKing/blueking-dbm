package api

import (
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/util"

	"github.com/pkg/errors"
)

// BKBizIDDef TODO
type BKBizIDDef struct {
	// 业务ID，必选项
	BKBizID string `json:"bk_biz_id" form:"bk_biz_id" validate:"required" example:"testapp"`
}

// RequestType TODO
type RequestType struct {
	// 配置文件修改动作的请求类型，`SaveOnly`: 仅保存, `SaveAndPublish`保存并发布
	ReqType string `json:"req_type" form:"req_type" validate:"required,enums" enums:"SaveOnly,SaveAndPublish"`
}

// OperationType TODO
type OperationType struct {
	// 配置项修改动作，需提供操作类型字段，允许值 `add`,`update`,`remove`
	OPType string `json:"op_type" form:"op_type" validate:"required,enums" enums:"add,update,remove"`
}

// OperationUser TODO
type OperationUser struct {
	// 操作人
	OPUser string `json:"op_user" form:"op_user"`
}

// RespFormatDef TODO
type RespFormatDef struct {
	// `map.`, `map#`, `map|` 是特殊的map格式，返回结果会以 . 或者 # 或者 | 拆分 conf_name
	Format string `json:"format" form:"format" validate:"enums" enums:",list,map,map.,map#,map|"`
}

// UpLevelInfo TODO
type UpLevelInfo struct {
	// 上层级信息，如获取当前层级 cluster=c1 的配置，需要设置 level_info: {"module": "m1"} 提供cluster所属上级 module 的信息
	// 非必选项，目前只在查询 cluster 级别配置时需要指定模块信息有用
	// todo 将来可能本配置中心，直接请求dbmeta元数据来获取 可能的 app-module-cluster-host-instance 关系
	LevelInfo map[string]string `json:"level_info" form:"level_info"`
}

// Validate TODO
// 这里应该根据 level_names 字段来判断是否需要上层级信息
func (v *UpLevelInfo) Validate(currentLevelName string) error {
	// todo 检查 level_name key 的合法性
	if currentLevelName == constvar.LevelCluster {
		if !util.MapHasElement(v.LevelInfo, constvar.LevelModule) {
			return errors.Errorf("query level [cluster] shoud have level_info [module]")
		}
	} else if currentLevelName == constvar.LevelInstance {
		if !util.MapHasElement(v.LevelInfo, constvar.LevelModule) ||
			!util.MapHasElement(v.LevelInfo, constvar.LevelCluster) {
			return errors.Errorf("query level [instance] shoud have level_info [module,cluster]")
		}
	} else if !util.IsEmptyMapString(v.LevelInfo) {
		return errors.Errorf("query level [%s] should not have level_info %s", currentLevelName, v.LevelInfo)
	}
	return nil
}

// GetLevelValue TODO
func (v *UpLevelInfo) GetLevelValue(levelName string) string {
	if levelValue, ok := v.LevelInfo[levelName]; ok {
		return levelValue
	} else {
		return ""
	}
}

// BaseLevelDef TODO
type BaseLevelDef struct {
	// 配置层级名，当前允许值 `app`,`module`,`cluster`,`instance`
	// 配合 flag_locked 锁定标记，可以知道 锁定级别
	LevelName string `json:"level_name" label:"level" form:"level_name" validate:"required,enums" enums:"plat,app,bk_cloud_id,module,cluster,instance" example:"cluster"`
	// 配置层级值
	LevelValue string `json:"level_value" form:"level_value"`
}

// BaseLevelsDef TODO
type BaseLevelsDef struct {
	// 配置层级名，当前允许值 `app`,`module`,`cluster`,`instance`
	LevelName string `json:"level_name" form:"level_name" validate:"required,enums" enums:"plat,app,bk_cloud_id,module,cluster,instance" example:"cluster"`
	// 配置层级值, array 多个
	LevelValues []string `json:"level_values" form:"level_values" validate:"required"`
}
