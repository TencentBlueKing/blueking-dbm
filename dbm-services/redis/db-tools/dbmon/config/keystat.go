package config

// ConfKeyStat TODO
type ConfKeyStat struct {
	TopCnt   int `json:"top_count" mapstructure:"top_count"`
	Duration int `json:"duration_seconds" mapstructure:"duration_seconds"`
}

// ConfBigKeyStat TODO
type ConfBigKeyStat struct {
	TopCnt   int `json:"top_count" mapstructure:"top_count"`
	Duration int `json:"duration_seconds" mapstructure:"duration_seconds"`
	// 是否在Master 上运行， 默认在slave 上运行
	RunOnMaster bool `json:"on_master" mapstructure:"on_master"`
	// 是否使用RDB 来分析
	UseRdb bool `json:"use_rdb" mapstructure:"use_rdb"`
	// 磁盘最大使用率，大于这个值将不执行分析
	DiskMaxUsage int `json:"disk_max_usage" mapstructure:"disk_max_usage"`
	// 业务可以执行key模式， 如果有，会优先按照这里匹配
	KeyModSpec string `json:"keymod_spec"  mapstructure:"keymod_spec"`
	// 可以模式算法
	KeyModeEngine string `json:"keymod_engine" mapstructure:"keymod_engine"`
}

// key模式分析，3个需求:
// 1，支持第3方的新增的Key模式算法
// 2，内存版，支持估算valueSize （取部分member的value Size）
// 3，支持从rdb中分析  （好象和备份有冲突？）
