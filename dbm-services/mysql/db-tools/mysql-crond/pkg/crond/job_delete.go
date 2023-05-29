package crond

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"fmt"

	"github.com/robfig/cron/v3"
	"golang.org/x/exp/slog"
)

// Delete TODO
func Delete(name string, permanent bool) (int, error) {
	existEntry := findEntry(name)
	if existEntry != nil {
		return deleteActivate(existEntry, permanent)
	}

	if _, ok := DisabledJobs.Load(name); ok {
		return deleteDisabled(name, permanent)
	}

	err := NotFoundError(fmt.Sprintf("job %s not found", name))
	slog.Error("delete job", err)
	return 0, err
}

func deleteActivate(entry *cron.Entry, permanent bool) (int, error) {
	j, ok := entry.Job.(*config.ExternalJob)
	if !ok {
		err := fmt.Errorf("convert %v to ExternalJob failed", entry)
		slog.Error("delete activate", err)
		return 0, err
	}

	cronJob.Remove(entry.ID)
	if permanent {
		err := config.SyncDelete(j.Name)
		if err != nil {
			_, _ = cronJob.AddJob(j.Schedule, j)
			return 0, err
		}
	}
	slog.Info("delete activity success", slog.String("name", j.Name))
	return 0, nil
}

func deleteDisabled(name string, permanent bool) (int, error) {
	v, _ := DisabledJobs.LoadAndDelete(name)
	job, ok := v.(*config.ExternalJob)
	if !ok {
		err := fmt.Errorf("conver %v to ExternalJob failed", v)
		slog.Error("delete disabled", err)
		return 0, err
	}

	if permanent {
		err := config.SyncDelete(name)
		if err != nil {
			DisabledJobs.Store(name, job)
			return 0, err
		}
	}
	slog.Info("delete disabled success", slog.String("name", name))
	return 0, nil
}
