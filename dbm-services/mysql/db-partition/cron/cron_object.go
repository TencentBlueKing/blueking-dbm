package cron

// Daily TODO
const Daily = "daily"

// Retry TODO
const Retry = "retry"

// PartitionJob TODO
type PartitionJob struct {
	CronType    string `json:"cron_type"`
	ZoneOffset  int    `json:"zone_offset"`
	ZoneName    string `json:"zone_name"`
	CronDate    string `json:"cron_date"`
	Hour        string `json:"hour"`
	ClusterType string `json:"cluster_type"`
}
