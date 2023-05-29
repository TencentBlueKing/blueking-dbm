package api

import (
	"bk-dbconfig/pkg/constvar"

	"github.com/pkg/errors"
)

// CreateResponseConfig TODO
type CreateResponseConfig struct {
}

// ConfigQueryReq2 TODO
type ConfigQueryReq2 struct {
	BKBizID   string `json:"bk_biz_id" form:"bk_biz_id"`
	Namespace string `json:"namespace" form:"namespace"`
	Module    string `json:"module" form:"module"`
	Cluster   string `json:"cluster" form:"cluster"`
	ConfType  string `json:"conf_type" form:"conf_type"`
	ConfFile  string `json:"conf_file" form:"conf_file"`
	ConfName  string `json:"conf_name" form:"conf_name"`
	ConfValue string `json:"conf_value" form:"conf_value"`

	InheritFrom string `json:"inherit_from" form:"inherit_from"`
	Format      string `json:"format" form:"format"`
	View        string `json:"view" form:"view"`
}

// ConfigQueryResp TODO
type ConfigQueryResp struct {
	BKBizID     string                       `json:"bk_biz_id"`
	Namespace   string                       `json:"namespace"`
	ConfType    string                       `json:"conf_type"`
	ConfFile    string                       `json:"conf_file"`
	Module      string                       `json:"module"`
	Cluster     string                       `json:"cluster"`
	ConfValues  map[string]map[string]string `json:"conf_values"`
	ExtraInfo   string                       `json:"extra_info"`
	Description string                       `json:"description"`
	FlagDisable int8                         `json:"flag_disable"`
	TimeCreated string                       `json:"time_created"`
	TimeUpdated string                       `json:"time_updated"`
}

// QueryReqUserConfig TODO
type QueryReqUserConfig struct {
	BKBizID  string `json:"bk_biz_id"`
	Username string `json:"username"`
}

// PlatConfigCloneReq TODO
type PlatConfigCloneReq struct {
	BKBizID   string `json:"bk_biz_id"`
	Namespace string `json:"namespace"`
	ConfType  string `json:"conf_type"`
	ConfFile  string `json:"conf_file"`
}

// SimpleConfigQueryReq TODO
// 所有创建该 Req 的地方，需要调用 Validate
type SimpleConfigQueryReq struct {
	BaseConfigNode

	ConfName  string `json:"conf_name" form:"conf_name"`
	ConfValue string `json:"conf_value" form:"conf_value"`
	Module    string `json:"module" form:"module"`
	Cluster   string `json:"cluster" form:"cluster"`

	InheritFrom string `json:"inherit_from" form:"inherit_from"`
	Format      string `json:"format" form:"format"`
	View        string `json:"view" form:"view"`

	Description string `json:"description" form:"description"`
	CreatedAt   string `json:"created_at" form:"created_at"`
	UpdatedAt   string `json:"updated_at" form:"updated_at"`
	CreatedBy   string `json:"created_by" form:"created_by"`
	UpdatedBy   string `json:"updated_by" form:"updated_by"`

	Revision string `json:"revision" form:"revision"`

	UpLevelInfo

	// 是否是生成配置文件
	Generate bool
	// 是否是解密
	Decrypt bool
}

// Validate TODO
func (v *SimpleConfigQueryReq) Validate() error {
	v.SetLevelNameValue()

	if v.BKBizID == "" || v.ConfType == "" || v.Namespace == "" {
		return errors.New("namespace,conf_type,bk_biz_id can not be empty")
	}
	if v.LevelName == constvar.LevelApp && v.BKBizID != constvar.BKBizIDForPlat && v.LevelValue != v.BKBizID {
		return errors.New("level_name=bk_biz_id should have bk_biz_id=level_value")
	}
	if (v.BKBizID == constvar.BKBizIDForPlat && v.LevelName != constvar.LevelPlat) ||
		(v.BKBizID != constvar.BKBizIDForPlat && v.LevelName == constvar.LevelPlat) {
		return errors.New("bk_biz_id=0 should have level_name=plat")
	}
	/*
	   // todo 暂不校验 level_info 里面的 level_name 是否合法
	   if err := v.UpLevelInfo.Validate(v.LevelName); err != nil {
	       return err
	   } else if v.LevelName == constvar.LevelCluster && v.Module == "" {
	       v.Module, _ = v.UpLevelInfo.LevelInfo[constvar.LevelModule]
	   } else if v.LevelName == constvar.LevelInstance {
	       if v.Module == "" {
	           v.Module, _ = v.UpLevelInfo.LevelInfo[constvar.LevelModule]
	       }
	       if v.Cluster == "" {
	           v.Cluster, _ = v.UpLevelInfo.LevelInfo[constvar.LevelCluster]
	       }
	   }
	*/
	if v.View == constvar.ViewMerge {
		if v.LevelName != "" {
			v.View = v.View + "." + v.LevelName
		} else if v.Cluster != "" {
			v.View = v.View + ".cluster"
		} else if v.Module != "" {
			v.View = v.View + ".module"
		}
	}
	return nil
}

// SetLevelNameValue TODO
func (v *SimpleConfigQueryReq) SetLevelNameValue() {
	if v.LevelName == "" {
		if v.Cluster != "" {
			v.LevelName = constvar.LevelCluster
			v.LevelValue = v.Cluster
		} else if v.Module != "" {
			v.LevelName = constvar.LevelModule
			v.LevelValue = v.Module
		} else if v.BKBizID == constvar.BKBizIDForPlat {
			v.LevelName = constvar.LevelPlat
			v.LevelValue = constvar.BKBizIDForPlat
		}
	} else {
		if v.LevelName == constvar.LevelCluster {
			v.Cluster = v.LevelValue
		} else if v.LevelName == constvar.LevelModule {
			v.Module = v.LevelValue
		} else if v.LevelName == constvar.LevelApp && v.BKBizID == "" {
			v.BKBizID = v.LevelValue
		}
	}
	if v.LevelInfo != nil {
		for upLevelName, upLevelValue := range v.LevelInfo {
			if upLevelName == constvar.LevelModule {
				v.Module = upLevelValue
			} else if upLevelName == constvar.LevelCluster {
				v.Cluster = upLevelValue
			}
		}
	}
	/*
	   if !util.MapHasElement(v.LevelInfo, constvar.LevelApp) {
	       v.LevelInfo[constvar.LevelApp] = v.BKBizID
	   }

	       if !util.MapHasElement(v.LevelInfo, constvar.LevelModule) {
	           v.LevelInfo[constvar.LevelModule] = v.Module
	       }

	*/
}
