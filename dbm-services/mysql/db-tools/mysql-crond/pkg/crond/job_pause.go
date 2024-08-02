package crond

import (
	"log/slog"
	"time"

	"github.com/pkg/errors"
	"github.com/robfig/cron/v3"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/schedule"
)

// Pause TODO
func Pause(name string, du time.Duration) (int, error) {
	existEntry := findEntry(name)
	if existEntry == nil {
		err := errors.WithMessagef(api.NotFoundError, "entry %s from active jobs", name)
		slog.Error("pause job", slog.String("error", err.Error()))
		return 0, err
	}

	j, _ := existEntry.Job.(*config.ExternalJob)
	cronJob.Remove(existEntry.ID)
	slog.Info(
		"disable job",
		slog.String("name", name),
		slog.Int("entry id", int(existEntry.ID)),
	)

	scheduleJob, err := config.NewScheduleJob(j, cronJob, &DisabledJobs)
	if err != nil {
		return 0, err
	}
	scheduleJobId := cronJob.Schedule(
		schedule.NewOnceSchedule(time.Now().Add(du)),
		scheduleJob,
	)
	*j.Enable = false
	j.JobID = scheduleJobId
	DisabledJobs.Store(name, j)
	cronJob.Schedule(
		schedule.NewOnceSchedule(time.Now().Add(du)),
		cron.FuncJob(
			func() {
				slog.Error("pause resume job will remove cron", slog.Int("entry", int(j.JobID)))
				cronJob.Remove(scheduleJobId)
			},
		),
	)

	return int(existEntry.ID), nil
}
