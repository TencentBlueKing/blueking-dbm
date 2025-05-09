package config

type bkCustom struct {
	BkDataId    int    `yaml:"bk_data_id" validate:"required"`
	AccessToken string `yaml:"access_token" validate:"required"`
	ReportType  string `yaml:"report_type" validate:"required"`
	MessageKind string `yaml:"message_kind" validate:"required"`
}

// BkMonitorBeat TODO
type BkMonitorBeat struct {
	CustomMetrics bkCustom `yaml:"custom_metrics" validate:"required"`
	CustomEvent   bkCustom `yaml:"custom_event" validate:"required"`
	BeatPath      string   `yaml:"beat_path" validate:"required,file"`
	AgentAddress  string   `yaml:"agent_address" validate:"required,file"`
}
