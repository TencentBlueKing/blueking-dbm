package v2

// ListCheckBizInput v2 巡检：按业务分页列表入参
type ListCheckBizInput struct {
	ClusterType string `json:"cluster_type"`
	Limit       int64  `json:"limit"`
	Offset      int    `json:"offset"`
}

// CheckBizItem v2 巡检：单业务汇总
type CheckBizItem struct {
	BkBizId     int64  `json:"bk_biz_id"`
	DbAppAbbr   string `json:"db_app_abbr"`
	ConfigCount int64  `json:"config_count"`
}

// ListCheckBizOutput v2 巡检：按业务分页列表出参
type ListCheckBizOutput struct {
	Count int64          `json:"count"`
	Items []CheckBizItem `json:"items"`
}

// ListCheckConfIdsInput v2 巡检：按业务分页配置 ID 入参
type ListCheckConfIdsInput struct {
	ClusterType string `json:"cluster_type"`
	BkBizId     int64  `json:"bk_biz_id"`
	Limit       int64  `json:"limit"`
	Offset      int    `json:"offset"`
}

// ListCheckConfIdsOutput v2 巡检：按业务分页配置 ID 出参
type ListCheckConfIdsOutput struct {
	Count     int64   `json:"count"`
	ConfigIds []int64 `json:"config_ids"`
}
