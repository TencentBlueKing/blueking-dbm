package config

// DefaultHotKeyQpsThreshold 热key分析实例QPS默认阈值
const DefaultHotKeyQpsThreshold = 10000

// ConfKeyStat 热key统计配置
type ConfKeyStat struct {
	// Enable 是否启用热key分析; 未配置(nil)时默认启用,兼容旧配置文件
	Enable *bool `json:"enable" mapstructure:"enable"`
	// QpsThreshold 实例QPS阈值(instantaneous_ops_per_sec), 超过则不发起热key分析;
	// 未配置/0 时默认 DefaultHotKeyQpsThreshold(10000); 如需不检查可配置足够大的阈值
	QpsThreshold int64 `json:"qps_threshold" mapstructure:"qps_threshold"`
	TopCnt       int   `json:"top_count" mapstructure:"top_count"`
	Duration     int   `json:"duration_seconds" mapstructure:"duration_seconds"`
}

// Enabled 热key分析是否启用(未配置默认启用)
func (c *ConfKeyStat) Enabled() bool {
	return c.Enable == nil || *c.Enable
}

// ConfBigKeyStat 大key/key模式统计配置
type ConfBigKeyStat struct {
	// Enable 是否启用大key/key模式分析; 未配置(nil)时默认启用,兼容旧配置文件
	Enable   *bool `json:"enable" mapstructure:"enable"`
	TopCnt   int   `json:"top_count" mapstructure:"top_count"`
	Duration int   `json:"duration_seconds" mapstructure:"duration_seconds"`
	// 是否在Master 上运行， 默认在slave 上运行
	RunOnMaster bool `json:"on_master" mapstructure:"on_master"`
	// 是否使用RDB 来分析
	UseRdb bool `json:"use_rdb" mapstructure:"use_rdb"`
	// 内存最大使用率，大于这个值将不用RDB分析
	MemMaxUsage int `json:"mem_max_usage" mapstructure:"mem_max_usage"`
	// 磁盘最大使用率，大于这个值将不执行分析
	DiskMaxUsage int `json:"disk_max_usage" mapstructure:"disk_max_usage"`
	// 业务可以执行key模式， 如果有，会优先按照这里匹配
	KeyModSpec string `json:"keymod_spec"  mapstructure:"keymod_spec"`
	// 可以模式算法
	KeyModeEngine string `json:"keymod_engine" mapstructure:"keymod_engine"`
}

// Enabled 大key/key模式分析是否启用(未配置默认启用)
func (c *ConfBigKeyStat) Enabled() bool {
	return c.Enable == nil || *c.Enable
}

// key模式分析，3个需求:
// 1，支持第3方的新增的Key模式算法
// 2，内存版，支持估算valueSize （取部分member的value Size）
// 3，支持从rdb中分析  （好象和备份有冲突？）
