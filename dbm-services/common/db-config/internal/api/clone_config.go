package api

// CloneModuleConfigReq clone module config
type CloneModuleConfigReq struct {
	SourceModuleID string `json:"source_module_id" binding:"required"`
	TargetModuleID string `json:"target_module_id" binding:"required"`
	SourceBkBizID  string `json:"source_bk_biz_id" binding:"required"`
	TargetBkBizID  string `json:"target_bk_biz_id" binding:"required"`
	SourceConfFile string `json:"source_conf_file" binding:"required"`
	TargetConfFile string `json:"target_conf_file" binding:"required"`
	ConfType       string `json:"conf_type" binding:"required"`
	Namespace      string `json:"namespace" binding:"required"`
}

// CloneClusterConfigReq clone cluster config
type CloneClusterConfigReq struct {
	CloneModuleConfigReq
	ClusterDomains []string `json:"cluster_domains" binding:"required"`
}

// DeleteModuleConfigReq delete module config
type DeleteModuleConfigReq struct {
	DbModuleId string `json:"db_module_id" binding:"required"`
	BkBizID    string `json:"bk_biz_id" binding:"required"`
	Namespace  string `json:"namespace" binding:"required"`
}

type CloneModuleQueryConfigResp struct {
	GetConfigItemsResp
	// ConfNamesDeprecated 目标模块中废弃的配置项
	ConfNamesDeprecated []string `json:"conf_names_deprecated"`
	// ConfNamesValueModified 源模块修改过的自定义配置项
	ConfNamesValueModified []string `json:"conf_names_value_modified"`
	// ConfNamesValueDiff 源模块和目标模块 默认配置项差异
	ConfNamesValueDiff map[string]interface{} `json:"conf_names_value_diff"`
}
