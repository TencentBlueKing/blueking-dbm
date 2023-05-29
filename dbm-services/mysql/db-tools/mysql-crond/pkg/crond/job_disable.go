package crond

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"
	"fmt"

	"golang.org/x/exp/slog"
)

// Disable TODO
func Disable(name string, permanent bool) (int, error) {
	existEntry := findEntry(name)
	if existEntry == nil {
		err := fmt.Errorf("entry %s not found", name)
		slog.Error("delete job", err)
		return 0, err
	}

	j, ok := existEntry.Job.(*config.ExternalJob)
	if !ok {
		err := fmt.Errorf("convert %v to ExternalJob failed", existEntry)
		slog.Error("disable job", err)
		return 0, err
	}
	*j.Enable = false

	cronJob.Remove(existEntry.ID)
	slog.Info(
		"disable job",
		slog.String("name", name),
		slog.Int("entry id", int(existEntry.ID)),
	)

	DisabledJobs.Store(j.Name, j)

	if permanent {
		err := config.SyncJobEnable(name, false)
		if err != nil {
			*j.Enable = true
			// 本来就是错误处理, 这里再出错也不知道咋办了
			// 但是想来也不太可能出错
			_, _ = cronJob.AddJob(j.Schedule, j)
			DisabledJobs.Delete(j.Name)
			return 0, err
		}
	}

	return int(existEntry.ID), nil
}
