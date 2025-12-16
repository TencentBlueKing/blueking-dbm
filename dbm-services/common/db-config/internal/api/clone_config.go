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
