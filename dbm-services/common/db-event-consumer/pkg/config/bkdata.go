package config

type BkDataConfig struct {
	CollectorConfigId     int    `json:"collector_config_id"`
	CollectorConfigName   string `json:"collector_config_name"`
	CollectorConfigNameEn string `json:"collector_config_name_en"`
	TargetObjectType      string `json:"target_object_type"`
	BkDataId              int    `json:"bk_data_id"`
	BkDataName            string `json:"bk_data_name"`
	TableId               string `json:"table_id"`
	BkDataDataId          int    `json:"bkdata_data_id"`
}
