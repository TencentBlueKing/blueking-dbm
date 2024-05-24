package model

import "github.com/spf13/viper"

// BkRepo 蓝鲸介质中心信息
var BkRepo BkRepoConfig

// InitBkRepo 初始化介质中心信息
func InitBkRepo() {
	BkRepo = BkRepoConfig{
		PublicBucket: viper.GetString("bkrepo.public_bucket"),
		Project:      viper.GetString("bkrepo.project"),
		User:         viper.GetString("bkrepo.username"),
		Pwd:          viper.GetString("bkrepo.password"),
		EndPointUrl:  viper.GetString("bkrepo.endpoint_url"),
	}
}

// BkRepoConfig 蓝鲸介质中心
type BkRepoConfig struct {
	Project      string `yaml:"project"`
	PublicBucket string `yaml:"publicBucket"`
	User         string `yaml:"user"`
	Pwd          string `yaml:"pwd"`
	EndPointUrl  string `yaml:"endpointUrl"`
}
