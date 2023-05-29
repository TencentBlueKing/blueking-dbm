package crond

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"github.com/robfig/cron/v3"
)

func findEntry(name string) *cron.Entry {
	for _, entry := range ListEntry() {
		if j, ok := entry.Job.(*config.ExternalJob); !ok {
			continue
		} else {
			if j.Name == name {
				return &entry
			}
		}
	}
	return nil
}
