package crond

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/schedule"
	"fmt"
	"time"

	"github.com/robfig/cron/v3"
	"golang.org/x/exp/slog"
)

// Pause TODO
func Pause(name string, du time.Duration) (int, error) {
	existEntry := findEntry(name)
	if existEntry == nil {
		err := fmt.Errorf("entry %s not found", name)
		slog.Error("pause job", err)
		return 0, err
	}

	j, _ := existEntry.Job.(*config.ExternalJob)
	cronJob.Schedule(
		schedule.NewOnceSchedule(time.Now().Add(du)),
		cron.FuncJob(
			func() {
				_, _ = cronJob.AddJob(j.Schedule, j)
			},
		),
	)

	return int(existEntry.ID), nil
}
