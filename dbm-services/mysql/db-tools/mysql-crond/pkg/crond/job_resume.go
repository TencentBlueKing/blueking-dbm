package crond

import (
	"fmt"
	"log/slog"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
)

// Resume enable / resume form disabled list
// if not found from disabled list, return error
func Resume(name string, permanent bool) (int, error) {
	if value, ok := DisabledJobs.LoadAndDelete(name); ok {
		if j, ok := value.(*config.ExternalJob); ok {
			if j.JobID > 0 {
				slog.Error("resume job will remove cron", slog.Int("entry", int(j.JobID)))
				cronJob.Remove(j.JobID)
			}
			*j.Enable = true
			entryID, err := cronJob.AddJob(j.Schedule, j)
			if err != nil {
				slog.Error("resume job", slog.String("error", err.Error()))
				return 0, err
			}

			slog.Info(
				"resume job",
				slog.String("name", name),
				slog.Int("entry id", int(entryID)),
			)

			if permanent {
				err := config.SyncJobEnable(name, true)
				if err != nil {
					cronJob.Remove(entryID)
					*j.Enable = false
					DisabledJobs.Store(name, j)
					return 0, err
				}
			}
			return int(entryID), nil
		} else {
			err := fmt.Errorf("conver %v to ExternalJob failed", value)
			slog.Error("resume job", slog.String("error", err.Error()))
			return 0, err
		}
	} else {
		err := errors.WithMessagef(api.NotFoundError, "entry %s from disabled list", name)
		slog.Error("resume job", slog.String("error", err.Error()))
		return 0, err
	}
}
