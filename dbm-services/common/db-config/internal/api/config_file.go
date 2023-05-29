package api

// ListConfFileReq TODO
type ListConfFileReq struct {
	// 业务id, bk_biz_id=0 代表平台配置
	BKBizID string `json:"bk_biz_id" form:"bk_biz_id" validate:"required"`
	// 命名空间，一般指DB类型
	Namespace string `json:"namespace" form:"namespace" validate:"required"`
	ConfType  string `json:"conf_type" form:"conf_type" validate:"required" example:"dbconf"`
	// 如果指定了 conf_file 则只查这一个文件信息
	ConfFile string `json:"conf_file" form:"conf_file"`
	BaseLevelDef
}

// ListConfFileResp TODO
type ListConfFileResp struct {
	ConfFileDef
	// 创建时间
	CreatedAt string `json:"created_at"`
	// 更新时间
	UpdatedAt string `json:"updated_at"`
	// 更新人
	UpdatedBy string `json:"updated_by"`
}
