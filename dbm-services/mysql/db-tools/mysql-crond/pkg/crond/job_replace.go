package crond

import (
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"log/slog"
)

// CreateOrReplace TODO
func CreateOrReplace(j *config.ExternalJob, permanent bool) (int, error) {
	crondMu.Lock()
	defer crondMu.Unlock()

	if j == nil {
		slog.Error("create or replace job skip nil", slog.Any("job", j))
		return 0, nil
	}
	if j.Name == "" {
		slog.Error("create or replace job skip empty", slog.Any("job", j))
		return 0, nil
	}

	_, err := delete_(j.Name, permanent)

	if err != nil {
		var notFoundError NotFoundError
		if !errors.As(err, &notFoundError) {
			slog.Error(
				"create or replace job",
				slog.String("error", err.Error()),
				slog.Any("job", j),
			)
			return 0, nil
		}
	}

	entryID, err := add(j, permanent)
	if err != nil {
		slog.Error(
			"create or replace job",
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
