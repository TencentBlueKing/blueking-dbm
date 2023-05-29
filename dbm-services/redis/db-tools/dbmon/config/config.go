// Package config 配置包
package config

import (
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/spf13/viper"
)

// ConfServerItem servers配置项
type ConfServerItem struct {
	BkBizID       string `json:"bk_biz_id" mapstructure:"bk_biz_id"`
	BkCloudID     int64  `json:"bk_cloud_id" mapstructure:"bk_cloud_id"`
	App           string `json:"app" mapstructure:"app"`
	AppName       string `json:"app_name" mapstructure:"app_name"`
	ClusterDomain string `json:"cluster_domain" mapstructure:"cluster_domain"`
	ClusterName   string `json:"cluster_name" mapstructure:"cluster_name"`
	ClusterType   string `json:"cluster_type" mapstructure:"cluster_type"`
	MetaRole      string `json:"meta_role" mapstructure:"meta_role"`
	ServerIP      string `json:"server_ip" mapstructure:"server_ip"`
	ServerPorts   []int  `json:"server_ports" mapstructure:"server_ports"`
	Shard         string `json:"shard" mapstructure:"shard"`
}

// ConfRedisFullBackup 全备配置
type ConfRedisFullBackup struct {
	ToBackupSystem   string `json:"to_backup_system" mapstructure:"to_backup_system"`
	Cron             string `json:"cron" mapstructure:"cron"`
	OldFileLeftDay   int    `json:"old_file_left_day" mapstructure:"old_file_left_day"`
	TarSplit         bool   `json:"tar_split" mapstructure:"tar_split"`
	TarSplitPartSize string `json:"tar_split_part_size" mapstructure:"tar_split_part_size"`
}

// ConfRedisBinlogBackup binlog备份配置
type ConfRedisBinlogBackup struct {
	ToBackupSystem string `json:"to_backup_system" mapstructure:"to_backup_system"`
	Cron           string `json:"cron" mapstructure:"cron"`
	OldFileLeftDay int    `json:"old_file_left_day" mapstructure:"old_file_left_day"`
}

// ConfRedisHeartbeat 心跳配置
type ConfRedisHeartbeat struct {
	Cron string `json:"cron" mapstructure:"cron"`
}

// ConfRedisKeyLifeCycle Key统计 大key/热key，key模式
type ConfRedisKeyLifeCycle struct {
	StatDir string `json:"stat_dir" mapstructure:"stat_dir"`
	Cron    string `json:"cron" mapstructure:"cron"`

	HotKeyConf ConfKeyStat    `json:"hotkey_conf" mapstructure:"hotkey_conf"`
	BigKeyConf ConfBigKeyStat `json:"bigkey_conf" mapstructure:"bigkey_conf"`
}

// ConfRedisMonitor redis本地监控配置
type ConfRedisMonitor struct {
	BkMonitorEventDataID  int64  `json:"bkmonitor_event_data_id" mapstructure:"bkmonitor_event_data_id"`
	BkMonitorEventToken   string `json:"bkmonitor_event_token" mapstructure:"bkmonitor_event_token"`
	BkMonitorMetricDataID int64  `json:"bkmonitor_metric_data_id" mapstructure:"bkmonitor_metric_data_id"`
	BkMonitorMetircToken  string `json:"bkmonitor_metirc_token" mapstructure:"bkmonitor_metirc_token"`
	Cron                  string `json:"cron" mapstructure:"cron"`
}

// Configuration 配置
type Configuration struct {
	ReportSaveDir     string                `json:"report_save_dir" mapstructure:"report_save_dir"`
	ReportLeftDay     int                   `json:"report_left_day" mapstructure:"report_left_day"`
	HttpAddress       string                `json:"http_address" mapstructure:"http_address"`
	GsePath           string                `json:"gsepath" mapstructure:"gsepath"`
	RedisFullBackup   ConfRedisFullBackup   `json:"redis_fullbackup" mapstructure:"redis_fullbackup"`
	RedisBinlogBackup ConfRedisBinlogBackup `json:"redis_binlogbackup" mapstructure:"redis_binlogbackup"`
	RedisHeartbeat    ConfRedisHeartbeat    `json:"redis_heartbeat" mapstructure:"redis_heartbeat"`
	KeyLifeCycle      ConfRedisKeyLifeCycle `json:"redis_keylife" mapstructure:"redis_keylife"`
	RedisMonitor      ConfRedisMonitor      `json:"redis_monitor" mapstructure:"redis_monitor"`
	Servers           []ConfServerItem      `json:"servers" mapstructure:"servers"`
	InstConfig        InstConfigList        `json:"inst_config,omitempty" mapstructure:"inst_config"`
}

// String string
func (c *Configuration) String() string {
	tmp, _ := json.Marshal(c)
	return string(tmp)
}

// GlobalConf 全局配置
// 如果配置文件被修改,会重新加载配置文件更新全局配置
var GlobalConf *Configuration

func loadConfigFile() {
	conf := Configuration{}
	err := viper.Unmarshal(&conf)
	if err != nil {
		log.Panicf("viper.Unmarshal fail,err:%v,configFile:%s", err, viper.ConfigFileUsed())
		return
	}
	if conf.RedisFullBackup.OldFileLeftDay == 0 {
		conf.RedisFullBackup.OldFileLeftDay = 3 // 默认全备保留天数
	}
	if conf.RedisBinlogBackup.OldFileLeftDay == 0 {
		conf.RedisBinlogBackup.OldFileLeftDay = 3 // 默认binlog保留天数
	}
	if conf.ReportLeftDay == 0 {
		conf.ReportLeftDay = 15
	}
	if conf.GsePath == "" {
		conf.GsePath = "/usr/local/gse_bkte"
	}
	fmt.Println(conf.String())
	GlobalConf = &conf
}

// InitConfig reads in config file and ENV variables if set.
func InitConfig(cfgFile string) {
	if cfgFile != "" {
		_, err := os.Stat(cfgFile)
		if err != nil {
			log.Panicf("os.Stat %s fail,err:%v", cfgFile, err)
		}

		// Use config file from the flag.
		viper.SetConfigFile(cfgFile)
		viper.SetConfigType("yaml")
		// If a config file is found, read it in.
		err = viper.ReadInConfig()
		if err == nil {
			fmt.Println("Using config file:", viper.ConfigFileUsed())
		} else {
			log.Panicf("viper.ReadInConfig fail,err:%v,configFile:%s", err, viper.ConfigFileUsed())
		}
		// viper.WatchConfig()
		// viper.OnConfigChange(func(e fsnotify.Event) {
		// 	fmt.Printf("Config file changed:%s event:%s\n", e.Name, e.String())
		// 	loadConfigFile()
		// })
		loadConfigFile()
	} else {
		log.Panicf("--config not pass?")
	}

	// read in environment variables that match
	viper.AutomaticEnv()
}
