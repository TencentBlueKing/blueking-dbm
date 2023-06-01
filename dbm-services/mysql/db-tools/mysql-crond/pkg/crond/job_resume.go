package crond

import (
	"fmt"

	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"golang.org/x/exp/slog"
)

// Resume TODO
func Resume(name string, permanent bool) (int, error) {
	if value, ok := DisabledJobs.LoadAndDelete(name); ok {
		if j, ok := value.(*config.ExternalJob); ok {
			*j.Enable = true

			entryID, err := cronJob.AddJob(j.Schedule, j)
			if err != nil {
				slog.Error("resume job", err)
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
			slog.Error("resume job", err)
			return 0, err
		}
	} else {
		err := fmt.Errorf("%s not found", name)
		slog.Error("resume job", err)
		return 0, err
	}
}
