package crond

import (
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"log/slog"
)

// CreateOrReplace TODO
func CreateOrReplace(j *config.ExternalJob, permanent bool) (int, error) {
	_, err := Delete(j.Name, permanent)

	if err != nil {
		var notFoundError NotFoundError
		if !errors.As(err, &notFoundError) {
			slog.Error("create or replace job",
				slog.String("error", err.Error()),
				slog.Any("job", j),
			)
			return 0, err
		}
	}

	entryID, err := Add(j, permanent)
	if err != nil {
		slog.Error("create or replace job",
			slog.String("error", err.Error()),
			slog.Any("job", j),
		)
		return 0, err
	}
	slog.Info(
		"create or replace job",
		slog.Any("job", j),
	)
	return entryID, nil
}
