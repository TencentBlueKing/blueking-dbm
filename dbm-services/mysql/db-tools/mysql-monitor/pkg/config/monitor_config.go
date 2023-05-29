package config

import (
	"time"
)

// ConnectAuth TODO
type ConnectAuth struct {
	User     string `yaml:"user" validate:"required"`
	Password string `yaml:"password" validate:"required"`
}

type authCollect struct {
	Mysql      *ConnectAuth `yaml:"mysql"` // spider, ctl 也是这一套
	Proxy      *ConnectAuth `yaml:"proxy"`
	ProxyAdmin *ConnectAuth `yaml:"proxy_admin"`
}

type monitorConfig struct {
	BkBizId         int           `yaml:"bk_biz_id"`
	Ip              string        `yaml:"ip" validate:"required,ipv4"`
	Port            int           `yaml:"port" validate:"required,gt=1024,lte=65535"`
	BkInstanceId    int64         `yaml:"bk_instance_id" validate:"required,gt=0"`
	ImmuteDomain    string        `yaml:"immute_domain"`
	MachineType     string        `yaml:"machine_type"`
	Role            *string       `yaml:"role"`
	BkCloudID       *int          `yaml:"bk_cloud_id" validate:"required,gte=0"`
	Log             *LogConfig    `yaml:"log"`
	ItemsConfigFile string        `yaml:"items_config_file" validate:"required"`
	ApiUrl          string        `yaml:"api_url" validate:"required"`
	Auth            authCollect   `yaml:"auth"`
	DBASysDbs       []string      `yaml:"dba_sys_dbs" validate:"required"`
	InteractTimeout time.Duration `yaml:"interact_timeout" validate:"required"`
	DefaultSchedule string        `yaml:"default_schedule" validate:"required"`
}
