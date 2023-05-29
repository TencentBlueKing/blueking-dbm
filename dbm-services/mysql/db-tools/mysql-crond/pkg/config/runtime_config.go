package config

type runtimeConfig struct {
	Ip             string         `yaml:"ip" validate:"required,ipv4"`
	Port           int            `yaml:"port" validate:"required,gt=1024,lte=65535"`
	BkCloudID      *int           `yaml:"bk_cloud_id" validate:"required,gte=0"`
	BkMonitorBeat  *BkMonitorBeat `yaml:"bk_monitor_beat" validate:"required"`
	Log            *LogConfig     `yaml:"log"`
	PidPath        string         `yaml:"pid_path" validate:"required,dir"`
	JobsUser       string         `yaml:"jobs_user" validate:"required"`
	JobsConfigFile string         `yaml:"jobs_config" validate:"required"`
}
