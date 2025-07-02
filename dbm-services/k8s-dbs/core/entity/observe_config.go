package entity

// ObserveConfig Covering logs, monitoring, tracking and other dimensions
type ObserveConfig struct {
	BkLogConfig *BkLogConfig `json:"bkLogConfig,omitempty"`
	SvcMonitor  *SvcMonitor  `json:"svcMonitor,omitempty"`
}

// BkLogConfig bk-logconfig parameter from request
type BkLogConfig struct {
	Enabled bool              `json:"enabled,omitempty"`
	Labels  map[string]string `json:"labels,omitempty"`
	DataID  int32             `json:"dataId,omitempty"`
}

// SvcMonitor serviceMonitor parameter from request
type SvcMonitor struct {
	Enabled  bool              `json:"enabled,omitempty"`
	Labels   map[string]string `json:"labels,omitempty"`
	Interval string            `json:"interval,omitempty"`
}
