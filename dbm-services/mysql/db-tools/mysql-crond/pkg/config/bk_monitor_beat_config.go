package config

type bkCustom struct {
	BkDataId    int    `yaml:"bk_data_id" validate:"required"`
	AccessToken string `yaml:"access_token" validate:"required"`
	ReportType  string `yaml:"report_type" validate:"required"`
	MessageKind string `yaml:"message_kind" validate:"required"`
}

// BkMonitorBeat TODO
type BkMonitorBeat struct {
	// CustomEvent struct {
	//	bkCustom `yaml:",inline"`
	//	//Name     string `yaml:"name" validate:"required"`
	// } `yaml:"custom_event" validate:"required"`
	CustomMetrics bkCustom `yaml:"custom_metrics" validate:"required"`
	CustomEvent   bkCustom `yaml:"custom_event" validate:"required"`
	// InnerEventName   string   `yaml:"inner_event_name" validate:"required"`
	// InnerMetricsName string   `yaml:"inner_metrics_name" validate:"required"`
	BeatPath     string `yaml:"beat_path" validate:"required,file"`
	AgentAddress string `yaml:"agent_address" validate:"required,file"`
}
