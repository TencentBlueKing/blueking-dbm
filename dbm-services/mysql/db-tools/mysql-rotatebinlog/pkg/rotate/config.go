package rotate

import (
	"github.com/mitchellh/go-homedir"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"
)

var PublicConfig PublicCfg

// Config rotate_binlog config
type Config struct {
	Public       PublicCfg              `json:"public" mapstructure:"public" validate:"required"`
	Servers      []*ServerObj           `json:"servers" mapstructure:"servers"`
	Report       ReportCfg              `json:"report" mapstructure:"report"`
	Encrypt      EncryptCfg             `json:"encrypt" mapstructure:"encrypt"`
	Crond        ScheduleCfg            `json:"crond" mapstructure:"crond"`
	BackupClient map[string]interface{} `json:"backup_client" mapstructure:"backup_client"`
}

// PublicCfg public config
type PublicCfg struct {
	KeepPolicy         string `json:"keep_policy" mapstructure:"keep_policy"`
	MaxBinlogTotalSize string `json:"max_binlog_total_size" mapstructure:"max_binlog_total_size"`
	// MaxDiskUsedPct 100 制
	MaxDiskUsedPct float64 `json:"max_disk_used_pct" mapstructure:"max_disk_used_pct"  validate:"required"`
	// 本地 binlog 最大保留时间，超过会直接删除
	MaxKeepDuration string `json:"max_keep_duration" mapstructure:"max_keep_duration"`
	// 间隔多久执行一次 purge index
	PurgeInterval string `json:"purge_interval" mapstructure:"purge_interval" validate:"required"`
	// 每隔多久执行一次 flush binary logs
	RotateInterval string `json:"rotate_interval" mapstructure:"rotate_interval" validate:"required"`
	// BackupEnable 是否启用备份上报到备份系统
	// auto，或为空: 根据 role 角色自动判断是否上报
	// yes: 上报 binlog 到备份系统
	// no: 不上报 binlog 到备份系统
	BackupEnable string `json:"backup_enable" mapstructure:"backup_enable"`

	maxBinlogTotalSizeMB int
}

// ReportCfg report config
type ReportCfg struct {
	// Enable 是否上报备份系统. repeater/orphan/slave 受此选项影响, master 一定会上报备份系统
	Enable        bool   `json:"enable" mapstructure:"enable"`
	Filepath      string `json:"filepath" mapstructure:"filepath"`
	LogMaxsize    int    `json:"log_maxsize" mapstructure:"log_maxsize"`
	LogMaxbackups int    `json:"log_maxbackups" mapstructure:"log_maxbackups"`
	LogMaxage     int    `json:"log_maxage" mapstructure:"log_maxage"`
}

// EncryptCfg encrypt config
type EncryptCfg struct {
	Enable    bool   `json:"enable" mapstructure:"enable"`
	KeyPrefix string `json:"key_prefix" mapstructure:"key_prefix"`
}

// ScheduleCfg schedule config
type ScheduleCfg struct {
	ApiUrl   string `json:"api_url" mapstructure:"api_url" validate:"required"`
	ItemName string `json:"item_name" mapstructure:"item_name" validate:"required"`
	Schedule string `json:"schedule" mapstructure:"schedule" validate:"required"`
	Command  string `json:"command" mapstructure:"command"`
}

// InitConfig 读取 config.yaml 配置
func InitConfig(confFile string) (*Config, error) {
	viper.SetConfigType("yaml")
	if confFile != "" {
		viper.SetConfigFile(confFile)
	} else {
		viper.SetConfigName("config")
		viper.AddConfigPath(".") // 搜索路径可以设置多个，viper 会根据设置顺序依次查找
		home, _ := homedir.Dir()
		viper.AddConfigPath(home)
	}
	if err := viper.ReadInConfig(); err != nil {
		//log.Fatalf("read config failed: %v", err)
		return nil, errors.WithMessage(err, "read config file")
	}
	var configObj = &Config{}
	if err := viper.Unmarshal(configObj); err != nil {
		// if err = yaml.Unmarshal(configBytes, ConfigObj); err != nil {
		return nil, err
	}
	if configObj.Public.BackupEnable == "" {
		configObj.Public.BackupEnable = cst.BackupEnableAuto
	} else if !lo.Contains(cst.BackupEnableAllowed, configObj.Public.BackupEnable) {
		return nil, errors.Errorf("public.backup_enable value only true/false/auto, but get %s",
			configObj.Public.BackupEnable)
	} else {
		PublicConfig = configObj.Public
	}
	//logger.Debug("ConfigObj: %+v", ConfigObj)
	return configObj, nil
}
