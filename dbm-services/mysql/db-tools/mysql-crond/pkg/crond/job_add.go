package crond

import (
	"fmt"

	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"golang.org/x/exp/slog"
)

// Add TODO
func Add(j *config.ExternalJob, permanent bool) (int, error) {
	existEntry := findEntry(j.Name)
	if existEntry != nil {
		err := fmt.Errorf("duplicate activate job name: %s", j.Name)
		slog.Error("add job", err)
		return 0, err
	}

	if _, ok := DisabledJobs.Load(j.Name); ok {
		err := fmt.Errorf("duplicate deleted job name: %s", j.Name)
		slog.Error("add job", err)
		return 0, err
	}

	if *j.Enable {
		return addActivate(j, permanent)
	} else {
		return addDisabled(j, permanent)
	}
}

func addActivate(j *config.ExternalJob, permanent bool) (int, error) {
	entryID, err := cronJob.AddJob(j.Schedule, j)
	if err != nil {
		slog.Error("add job", err)
		return 0, err
	}
	slog.Info(
		"add job",
		slog.String("name", j.Name),
		slog.Int("entry id", int(entryID)),
	)

	if permanent {
		err := config.SyncAddJob(j)
		if err != nil {
			cronJob.Remove(entryID)
			return 0, err
		}
	}

	return int(entryID), nil
}

func addDisabled(j *config.ExternalJob, permanent bool) (int, error) {
	DisabledJobs.Store(j.Name, j)
	slog.Info(
		"add disabled job",
		slog.String("name", j.Name),
	)

	if permanent {
		err := config.SyncAddJob(j)
		if err != nil {
			DisabledJobs.Delete(j.Name)
			return 0, err
		}
	}

	return 0, nil
}
