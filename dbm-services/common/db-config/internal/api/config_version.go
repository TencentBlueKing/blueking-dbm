package api

// GetVersionedDetailReq TODO
type GetVersionedDetailReq struct {
	BKBizIDDef
	BaseConfFileDef
	BaseLevelDef
	// 当 revision = "v_latest" 时，会返回当前最新的版本
	Revision string `json:"revision" form:"revision" validate:"required" example:"v_20220309215824"`
	RespFormatDef
}

// GetVersionedDetailResp TODO
type GetVersionedDetailResp struct {
	ID uint64 `json:"id"`
	// 版本号
	Revision string `json:"revision"`
	// Content     interface{} `json:"content"`
	ContentStr  string `json:"content_str"`
	IsPublished int8   `json:"is_published"`
	// 上一个版本好
	PreRevision string `json:"pre_revision"`
	// 相对上一个版本 影响行数
	RowsAffected int    `json:"rows_affected"`
	Description  string `json:"description"`
	// 发布人
	CreatedBy string `json:"created_by"`
	// 发布时间
	CreatedAt string `json:"created_at"`
	// 配置项，根据 format 会有不同的格式
	Configs map[string]interface{} `json:"configs"`
	// 与上一个版本的差异
	ConfigsDiff map[string]interface{} `json:"configs_diff"`
}

// PublishConfigFileReq TODO
type PublishConfigFileReq struct {
	BaseConfigNode
	// the version you want to publish
	Revision string `json:"revision" form:"revision" validate:"required" example:"v_20220309161928"`
	// patch will overwrite conf_value to versioned config_file. it's a key-value dict
	Patch map[string]string `json:"patch" form:"patch"`
} // @name PublishConfigFileReq

// ListConfigVersionsReq list config file versions
type ListConfigVersionsReq struct {
	BKBizIDDef
	BaseConfFileDef
	BaseLevelDef
} // @name ListConfigVersionsReq

// ListConfigVersionsResp TODO
type ListConfigVersionsResp struct {
	BKBizID   string `json:"bk_biz_id"`
	Namespace string `json:"namespace"`
	ConfFile  string `json:"conf_file"`
	// 版本列表，格式 [{"revision":"v1", "rows_affected":1},{"revision":"v2", "rows_affected":2}]
	Versions []map[string]interface{} `json:"versions"`
	// version published. empty when published version is not in versions
	VersionLatest string `json:"published"`
	BaseLevelDef
} // @name ListConfigVersionsResp
