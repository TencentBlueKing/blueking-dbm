package config

type runtimeConfig struct {
	BkmApiInfo `yaml:",inline" json:",inline"`
	BkDataId   int `yaml:"bk_data_id"`
	// BkCollectorName collector_config_name_en
	BkCollectorName string `yaml:"bk_collector_name"`

	AltBroker *string `yaml:"alt_broker"`
	ClientId  string  `yaml:"client_id"`
	GroupId   string  `yaml:"group_id"`
	Dsn       struct {
		User                   string  `yaml:"user"`
		Password               string  `yaml:"password"`
		Address                string  `yaml:"address"`
		Database               string  `yaml:"database"`
		Charset                string  `yaml:"charset"`
		Table                  *string `yaml:"table"`
		ConnectionPerPartition int     `yaml:"connection_per_partition"`
	} `yaml:"dsn"`
	Log *LogConfig `yaml:"log"`
}

type BkmApiInfo struct {
	BkAppCode   string `yaml:"bk_app_code" json:"bk_app_code"`
	BkAppSecret string `yaml:"bk_app_secret" json:"bk_app_secret"`
	BkBizId     int    `yaml:"bk_biz_id" json:"bk_biz_id"`
	BkUsername  string `yaml:"bk_username" json:"bk_username"`
	// BkTicket    string `yaml:"bk_ticket" json:"bk_ticket"`
	// BkToken     string `yaml:"bk_token" json:"bk_token"`
	// BkmonitorApiUrl https://bk-monitor.xxx.com/prod/
	BkmonitorApiUrl string `yaml:"bkmonitor_api_url" json:"bkmonitor_api_url"`
	BklogApiUrl     string `yaml:"bklog_api_url" json:"bklog_api_url"`
}
