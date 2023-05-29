// Package config TODO
package config

import (
	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"path"

	"github.com/spf13/viper"
)

// GAppConfig TODO
var GAppConfig = AppConfig{}

// AppConfig TODO
type AppConfig struct {
	ListenAddr     string       `yaml:"listenAddr"`
	BkRepo         BkRepoConfig `yaml:"bkrepo"`
	Bcs            BcsConfig    `yaml:"bcs"`
	MirrorsAddress []ImgConfig  `yaml:"mirrorsAddress"`
	Image          Images
	DbConf         DbConfig `yaml:"dbconf"`
	Debug          bool     `yaml:"debug"`
	RulePath       string   `yaml:"rulePath"`
	SpiderRulePath string   `yaml:"spiderRulePath"`
}

// BkRepoConfig TODO
type BkRepoConfig struct {
	Project      string `yaml:"project"`
	PublicBucket string `yaml:"publicBucket"`
	User         string `yaml:"user"`
	Pwd          string `yaml:"pwd"`
	EndPointUrl  string `yaml:"endpointUrl"`
}

// Images TODO
type Images struct {
	Tendb57Img string // 5.7版本对应的镜像
	Tendb56Img string // 5.6版本对应的镜像
	Tendb80Img string // 8.0版本对应的镜像
	TdbCtlImg  string // tdbctl 对应版本镜像
	SpiderImg  string // spider 镜像
}

// BcsConfig TODO
type BcsConfig struct {
	EndpointUrl string `yaml:"endpointUrl"`
	ClusterId   string `yaml:"clusterId"`
	Token       string `yaml:"token"`
	NameSpace   string `yaml:"namespace"`
	Timeout     int    `yaml:"timeout"`
}

// DbConfig TODO
type DbConfig struct {
	User string `yaml:"user"`
	Pwd  string `yaml:"pwd"`
	Name string `yaml:"name"`
	Host string `yaml:"host"`
	Port int    `yaml:"port"`
}

// ImgConfig TODO
type ImgConfig struct {
	Version string `yaml:"version"`
	Image   string `yaml:"image"`
}

func init() {
	viper.AutomaticEnv()
	// bkrepo
	viper.BindEnv("bkrepo_project", "BKREPO_PROJECT")
	viper.BindEnv("bkrepo_public_bucket", "BKREPO_PUBLIC_BUCKET")
	viper.BindEnv("bkrepo_username", "BKREPO_USERNAME")
	viper.BindEnv("bkrepo_password", "BKREPO_PASSWORD")
	viper.BindEnv("bkrepo_endpoint_url", "BKREPO_ENDPOINT_URL")
	// bcs
	viper.BindEnv("bcs_base_url", "BCS_BASE_URL")
	viper.BindEnv("bcs_token", "BCS_TOKEN")
	viper.BindEnv("bcs_cluster_id", "BCS_CLUSTER_ID")
	viper.BindEnv("bcs_namespace", "BCS_NAMESPACE")
	// db conf
	viper.BindEnv("db_user", "DB_USER")
	viper.BindEnv("db_password", "DB_PASSWORD")
	viper.BindEnv("db_host", "DB_HOST")
	viper.BindEnv("db_port", "DB_PORT")
	viper.BindEnv("dbsimulation_db", "DBSIMULATION_DB")
	viper.BindEnv("debug", "DEBUG")
	// img conf
	viper.BindEnv("mirrors_addr", "MIRRORS_ADDR")
	viper.BindEnv("mysql56", "MYSQL56")
	viper.BindEnv("mysql57", "MYSQL57")
	viper.BindEnv("mysql80", "MYSQL80")
	viper.BindEnv("spider_img", "SPIDER_IMG")
	viper.BindEnv("tdbctl_img", "TDBCTL_IMG")

	GAppConfig.ListenAddr = "0.0.0.0:80"
	if viper.GetString("LISTEN_ADDR") != "" {
		GAppConfig.ListenAddr = viper.GetString("LISTEN_ADDR")
	}
	GAppConfig.Debug = viper.GetBool("DEBUG")
	GAppConfig.BkRepo = BkRepoConfig{
		PublicBucket: viper.GetString("BKREPO_BUCKET"),
		Project:      viper.GetString("BKREPO_PROJECT"),
		User:         viper.GetString("BKREPO_USERNAME"),
		Pwd:          viper.GetString("BKREPO_PASSWORD"),
		EndPointUrl:  viper.GetString("BKREPO_ENDPOINT_URL"),
	}
	GAppConfig.Bcs = BcsConfig{
		NameSpace:   viper.GetString("BCS_NAMESPACE"),
		EndpointUrl: viper.GetString("BCS_BASE_URL"),
		ClusterId:   viper.GetString("BCS_CLUSTER_ID"),
		Token:       viper.GetString("BCS_TOKEN"),
		Timeout:     10,
	}
	GAppConfig.DbConf = DbConfig{
		User: viper.GetString("DB_USER"),
		Pwd:  viper.GetString("DB_PASSWORD"),
		Host: viper.GetString("DB_HOST"),
		Port: viper.GetInt("DB_PORT"),
		Name: viper.GetString("DBSIMULATION_DB"),
	}
	mirroraddr := viper.GetString("MIRRORS_ADDR")
	if !util.IsEmpty(mirroraddr) {
		mysql56 := viper.GetString("MYSQL56")
		mysql57 := viper.GetString("MYSQL57")
		mysql80 := viper.GetString("MYSQL80")
		spiderImg := viper.GetString("SPIDER_IMG")
		tdbctlImg := viper.GetString("TDBCTL_IMG")
		if !util.IsEmpty(mysql56) {
			GAppConfig.Image.Tendb56Img = path.Join(mirroraddr, mysql56)
		}
		if !util.IsEmpty(mysql57) {
			GAppConfig.Image.Tendb57Img = path.Join(mirroraddr, mysql57)
		}
		if !util.IsEmpty(mysql80) {
			GAppConfig.Image.Tendb80Img = path.Join(mirroraddr, mysql80)
		}
		if !util.IsEmpty(spiderImg) {
			GAppConfig.Image.SpiderImg = path.Join(mirroraddr, spiderImg)
		}
		if !util.IsEmpty(tdbctlImg) {
			GAppConfig.Image.TdbCtlImg = path.Join(mirroraddr, tdbctlImg)
		}
	}
	if err := loadConfig(); err != nil {
		logger.Error("load config file failed:%s", err.Error())
	}
	for _, v := range GAppConfig.MirrorsAddress {
		switch v.Version {
		case "5.6":
			GAppConfig.Image.Tendb56Img = v.Image
		case "5.7":
			GAppConfig.Image.Tendb57Img = v.Image
		case "8.0":
			GAppConfig.Image.Tendb80Img = v.Image
		case "spider":
			GAppConfig.Image.SpiderImg = v.Image
		case "tdbctl":
			GAppConfig.Image.TdbCtlImg = v.Image
		}
	}
	logger.Info("app config %v", GAppConfig)
}

// loadConfig 加载配置文件
func loadConfig() (err error) {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("$HOME/conf")
	viper.AddConfigPath("./conf")
	if err = viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); ok {
			logger.Error("config file not found,maybe read by env")
			return nil
		}
		return err
	}
	if err = viper.Unmarshal(&GAppConfig); err != nil {
		return err
	}
	logger.Debug("load config is: %v", GAppConfig)
	return
}
