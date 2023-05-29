package config

import (
	"time"
)

type monitorConfig struct {
	BkBizId      int    `yaml:"bk_biz_id"`
	Ip           string `yaml:"ip" validate:"required,ipv4"`
	Port         int    `yaml:"port" validate:"required,gt=1024,lte=65535"`
	BkInstanceId int64  `yaml:"bk_instance_id" validate:"required,gt=0"`
	ImmuteDomain string `yaml:"immute_domain"`
	MachineType  string `yaml:"machine_type"`
	BkCloudID    *int   `yaml:"bk_cloud_id" validate:"required,gte=0"`
	// 日志配置项
	Log *LogConfig `yaml:"log"`
	// items-config.yaml 路径
	ItemsConfigFile string `yaml:"items_config_file" validate:"required"`
	// crond的访问url
	ApiUrl string `yaml:"api_url" validate:"required"`
	// 超时时间
	InteractTimeout time.Duration `yaml:"interact_timeout" validate:"required"`
	// 调度频率
	DefaultSchedule string `yaml:"default_schedule" validate:"required"`
}
