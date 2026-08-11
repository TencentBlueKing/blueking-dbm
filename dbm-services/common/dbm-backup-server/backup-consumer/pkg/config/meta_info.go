package config

// KafkaMeta bkmonitor kafka from data_id
type KafkaMeta struct {
	ClusterConfig struct {
		DomainName string `json:"domain_name"`
		Port       int    `json:"port"`
	} `json:"cluster_config"`
	StorageConfig struct {
		Topic     string `json:"topic"`
		Partition int    `json:"partition"`
	} `json:"storage_config"`
	AuthInfo struct {
		Username string `json:"username"`
		Password string `json:"password"`
		// SaslMechanisms like SCRAM-SHA-512
		SaslMechanisms string `json:"sasl_mechanisms"`
		// SecurityProtocol like SASL_PLAINTEXT
		SecurityProtocol string `json:"security_protocol"`
	} `json:"auth_info"`
}

// BkDataConfig bklog collectors
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
