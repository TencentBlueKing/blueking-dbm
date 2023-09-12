package cron

// Daily TODO
const Daily = "daily"

// Retry TODO
const Retry = "retry"

// Heartbeat TODO
const Heartbeat = "heartbeat"

// PartitionJob TODO
type PartitionJob struct {
	CronType   string
	ZoneOffset int
	ZoneName   string
	CronDate   string
	Hour       string
}
