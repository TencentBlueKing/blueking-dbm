package rotate

import (
	"dbm-services/common/reverseapi/pkg"
	"fmt"
	"os"
	"path/filepath"
	"strconv"

	gyaml "github.com/ghodss/yaml"
	"github.com/mitchellh/go-homedir"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/logger"
	meta "dbm-services/common/reverseapi/define/mysql"
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
	// MaxOldDaysToUpload 多久时间以内的 binlog 才上传到备份系统
	// 一般在 rotatebinlog 第一次部署，或者很久没有运行时重新运行会用到，默认 7 天
	MaxOldDaysToUpload int `json:"max_old_days_to_upload" mapstructure:"max_old_days_to_upload"`
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

func initConfigDefault() {
	viper.SetDefault("public.max_binlog_total_size", "2000g")
	viper.SetDefault("public.backup_enable", "auto")
	viper.SetDefault("public.max_old_days_to_upload", 7)
}

// InitConfig 读取 main.yaml 配置
func InitConfig(confFile string) (*Config, error) {
	initConfigDefault()
	configObj, err := ReadMainConfig(confFile)
	if err != nil {
		return nil, err
	}

	servers, err := readInstanceConfig(confFile)
	if err != nil {
		return nil, err
	} else {
		// merge servers to main config
		servers = append(servers, configObj.Servers...)
		servers = deduplicateServers(servers)
		configObj.Servers = servers
	}
	if configObj.Public.MaxOldDaysToUpload == 0 {
		configObj.Public.MaxOldDaysToUpload = 7
	}
	//logger.Debug("ConfigObj: %+v", ConfigObj)
	return configObj, nil
}

// ReadMainConfig read main.yaml, not include instance config
func ReadMainConfig(mainConfFile string) (*Config, error) {
	viper.SetConfigType("yaml")
	if mainConfFile != "" {
		viper.SetConfigFile(mainConfFile)
	} else {
		viper.SetConfigName("main")
		//viper.SetConfigName("config")
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
		return nil, errors.Errorf("public.backup_enable value only %s, but get %s",
			cst.BackupEnableAllowed, configObj.Public.BackupEnable)
	} else {
		PublicConfig = configObj.Public
	}

	if len(configObj.Servers) > 0 {
		// remove servers section to separated instance config file
		for _, serverConfig := range configObj.Servers {
			yamlData, err := gyaml.Marshal(serverConfig) // use json tag
			if err != nil {
				return nil, err
			}
			serverConfigFile := filepath.Join(filepath.Dir(mainConfFile),
				fmt.Sprintf("server.%d.yaml", serverConfig.Port))
			if err := os.WriteFile(serverConfigFile, yamlData, 0644); err != nil {
				return nil, err
			}
		}
		configObj.Servers = nil
		yamlData, err := gyaml.Marshal(configObj) // use json tag
		if err != nil {
			return nil, err
		}
		if err := os.WriteFile(mainConfFile, yamlData, 0644); err != nil {
			return nil, err
		}
	}
	return configObj, nil
}

func readInstanceConfig(mainConfFile string) ([]*ServerObj, error) {
	// search server.<port>.yaml
	serverConfigName := "server.*.yaml"
	serverConfigPath := filepath.Join(filepath.Dir(mainConfFile), serverConfigName)
	files, err := filepath.Glob(serverConfigPath)
	if err != nil {
		logger.Error("search InstanceConfig '%s' failed: %v", serverConfigName, err)
		return nil, err
	} else {
		logger.Info("found config servers:%v", files)
	}
	var servers []*ServerObj
	for _, f := range files {
		s := ServerObj{}
		viperServer := viper.New()
		viperServer.SetConfigType("yaml")
		viperServer.SetConfigFile(f)
		if err = viperServer.ReadInConfig(); err != nil {
			logger.Error("readInstanceConfig %s read failed: %v", f, err)
			continue
		}
		if err = viperServer.Unmarshal(&s); err != nil {
			logger.Error("readInstanceConfig %s unmarshal failed: %v", f, err)
			continue
		}
		if instInfo, err := pkg.GetSelfInfo(s.Host, s.Port); err == nil {
			logger.Info("use role from common_config:%s, config:%s", instInfo.InstanceInnerRole, s.Tags.DBRole)
			if instInfo.AccessLayer == meta.AccessLayerStorage && instInfo.InstanceInnerRole != "" {
				s.Tags.DBRole = instInfo.InstanceInnerRole
			}
		} else {
			logger.Warn("get instance info from common_config failed: %v", err)
		}
		servers = append(servers, &s)
	}
	return servers, nil
}

func deduplicateServers(servers []*ServerObj) []*ServerObj {
	return lo.UniqBy(servers, func(item *ServerObj) string {
		return item.Host + ":" + strconv.Itoa(item.Port)
	})
}
