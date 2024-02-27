// Package config 配置包
package config

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

func init() {

}

// BkDbmLabel bk dbm label for Instance
type BkDbmLabel struct {
	BkCloudID     int64  `json:"bk_cloud_id" mapstructure:"bk_cloud_id" yaml:"bk_cloud_id"`
	BkBizID       int    `json:"bk_biz_id" mapstructure:"bk_biz_id" yaml:"bk_biz_id" yaml:"bk_biz_id"`
	App           string `json:"app" mapstructure:"app" yaml:"app"`
	AppName       string `json:"app_name" mapstructure:"-" yaml:"app_name"`
	ClusterDomain string `json:"cluster_domain" mapstructure:"cluster_domain" yaml:"cluster_domain"`
	ClusterId     int64  `json:"cluster_id" mapstructure:"cluster_id" yaml:"cluster_id"`
	ClusterName   string `json:"cluster_name" mapstructure:"cluster_name" yaml:"cluster_name"`
	ClusterType   string `json:"cluster_type" mapstructure:"cluster_type" yaml:"cluster_type"`
	RoleType      string `json:"role_type" mapstructure:"role_type" yaml:"role_type"` // shardsvr,mongos,configsvr
	MetaRole      string `json:"meta_role" mapstructure:"meta_role" yaml:"meta_role"` // m0,m1,backup...|mongos
	ServerIP      string `json:"server_ip" mapstructure:"server_ip" yaml:"server_ip"`
	ServerPort    int    `json:"server_port" mapstructure:"server_port" yaml:"server_port" yaml:"server_port"`
	SetName       string `json:"set_name" mapstructure:"set_name" yaml:"set_name" yaml:"set_name"`
}

// ParseBkDbmLabel 解析BkDbmLabel, 允许为空
func ParseBkDbmLabel(labels string) (*BkDbmLabel, error) {
	if labels == "" {
		return &BkDbmLabel{}, nil
	}

	var v = &BkDbmLabel{}
	if err := json.Unmarshal([]byte(labels), v); err != nil {
		return nil, err
	} else {
		return v, nil
	}
}

// ConfServerItem servers配置项
type ConfServerItem struct {
	BkDbmLabel `yaml:",inline" json:",inline" mapstructure:",squash"`
	UserName   string `yaml:"username" json:"username" mapstructure:"username"`
	Password   string `yaml:"password" json:"password" mapstructure:"password"`
}

// Addr return ip:port
func (c *ConfServerItem) Addr() string {
	return fmt.Sprintf("%s:%d", c.ServerIP, c.ServerPort)
}

// BkMonitorData 注册在Bk的Event.
type BkMonitorData struct {
	DataID int64  `yaml:"data_id" json:"data_id" mapstructure:"data_id"`
	Token  string `yaml:"token" json:"token" mapstructure:"token"`
}

// BkMonitorBeatConfig bkmonitorbeat配置
type BkMonitorBeatConfig struct {
	AgentAddress string        `yaml:"agent_address" json:"agent_address" mapstructure:"agent_address"`
	BeatPath     string        `yaml:"beat_path" json:"beat_path" mapstructure:"beat_path"`
	EventConfig  BkMonitorData `yaml:"event_config"  json:"event_config" mapstructure:"event_config"`
	MetricConfig BkMonitorData `yaml:"metric_config" json:"metric_config" mapstructure:"metric_config"`
}

// Configuration 配置
type Configuration struct {
	ReportSaveDir            string              `yaml:"report_save_dir" json:"report_save_dir" mapstructure:"report_save_dir"`
	ReportLeftDay            int                 `yaml:"report_left_day"  json:"report_left_day" mapstructure:"report_left_day"`
	BackupClientStrorageType string              `yaml:"backup_client_storage_type"  json:"backup_client_storage_type" mapstructure:"backup_client_storage_type"`
	HttpAddress              string              `yaml:"http_address"  json:"http_address" mapstructure:"http_address"`
	BkMonitorBeat            BkMonitorBeatConfig `yaml:"bkmonitorbeat"  json:"bkmonitorbeat" mapstructure:"bkmonitorbeat"`
	Servers                  []ConfServerItem    `yaml:"servers" json:"servers" mapstructure:"servers"`
	LoadTime                 string              `yaml:"-" json:"-" mapstructure:"-"`
}

// String string
func (c *Configuration) String() string {
	tmp, _ := json.Marshal(c)
	return string(tmp)
}

// GlobalConf 全局配置
// 如果配置文件被修改,会重新加载配置文件更新全局配置
// todo 是否需要将静态配置和动态配置分开？
var GlobalConf *Configuration

func _loadConfigFile() (*Configuration, error) {
	conf := Configuration{
		LoadTime: time.Now().Format(time.RFC3339),
	}
	err := viper.Unmarshal(&conf)
	if err != nil {
		return nil, errors.Wrap(err, fmt.Sprintf("viper.Unmarshal fail,err:%v,configFile:%s", err, viper.ConfigFileUsed()))
	}
	if conf.BkMonitorBeat.BeatPath == "" {
		return nil, errors.New("bk_monitor_beat.beat_path error")
	}
	if conf.BackupClientStrorageType == "" {
		conf.BackupClientStrorageType = "cos"
	}
	if conf.ReportLeftDay == 0 {
		conf.ReportLeftDay = 15
	}
	return &conf, nil
}

func loadConfigFile(first bool) {
	conf, err := _loadConfigFile()
	if err != nil {
		if first {
			log.Fatalf("loadConfigFile fail,err:%v", err)
		} else {
			log.Printf("loadConfigFile fail,err:%v", err)
			return
		}
	}
	GlobalConf = conf
}

// InitConfig reads in config file and ENV variables if set.
func InitConfig(cfgFile string) {
	var err error
	viper.SetConfigFile(cfgFile)
	viper.SetConfigType("yaml")
	if err = viper.ReadInConfig(); err != nil {
		log.Fatal(err) // 读取配置文件失败致命错误
	}

	fmt.Printf("Using config file: %s\n", viper.ConfigFileUsed())
	/* Read Config File && Watch file change event */
	loadConfigFile(true)
	viper.OnConfigChange(func(e fsnotify.Event) {
		log.Printf("Config file changed: %s", e.Name)
		loadConfigFile(false)
	})
	viper.WatchConfig()
	viper.AutomaticEnv()
}
