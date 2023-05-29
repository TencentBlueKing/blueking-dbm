package crond

import (
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"golang.org/x/exp/slog"
)

// CreateOrReplace TODO
func CreateOrReplace(j *config.ExternalJob, permanent bool) (int, error) {
	_, err := Delete(j.Name, permanent)

	if err != nil {
		if _, ok := err.(NotFoundError); !ok {
			slog.Error("create or replace job", err, slog.Any("job", j))
			return 0, err
		}
	}

	entryID, err := Add(j, permanent)
	if err != nil {
		slog.Error("create or replace job", err, slog.Any("job", j))
		return 0, err
	}
	return entryID, nil
}
