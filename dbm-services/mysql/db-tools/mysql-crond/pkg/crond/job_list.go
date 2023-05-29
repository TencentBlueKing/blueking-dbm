package crond

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"github.com/robfig/cron/v3"
)

// ListEntry TODO
func ListEntry() (res []cron.Entry) {
	for _, entry := range cronJob.Entries() {
		if _, ok := entry.Job.(*config.ExternalJob); ok {
			res = append(res, entry)
		}
	}
	return res
}

// ListDisabledJob TODO
func ListDisabledJob() (res []*config.ExternalJob) {
	DisabledJobs.Range(
		func(key, value any) bool {
			j, _ := value.(*config.ExternalJob)
			res = append(res, j)
			return true
		},
	)
	return res
}
