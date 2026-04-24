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

type ListConfLevelReq struct {
	// 业务id, bk_biz_id=0 代表平台配置
	BKBizID string `json:"bk_biz_id" form:"bk_biz_id" validate:"required"`
	// 命名空间，一般指DB类型
	Namespace string `json:"namespace" form:"namespace" validate:"required"`
	ConfType  string `json:"conf_type" form:"conf_type" validate:"required" example:"dbconf"`
	// 如果指定了 conf_file 则只查这一个文件信息
	ConfFile  string `json:"conf_file" form:"conf_file"`
	LevelName string `json:"level_name" form:"level_name" validate:"required,enums" enums:"plat,app,bk_cloud_id,module,cluster,instance" example:"cluster"`
}

// ListConfLevelResp 查询配置层级节点的响应
type ListConfLevelResp struct {
	BKBizID    string `json:"bk_biz_id" gorm:"column:bk_biz_id"`
	Namespace  string `json:"namespace" gorm:"column:namespace"`
	ConfType   string `json:"conf_type" gorm:"column:conf_type"`
	ConfFile   string `json:"conf_file" gorm:"column:conf_file"`
	LevelName  string `json:"level_name" gorm:"column:level_name"`
	LevelValue string `json:"level_value" gorm:"column:level_value"`
}

type DeleteConfLevelReq ListConfFileReq
