package mysql_errlog

import (
	"strings"

	"github.com/dlclark/regexp2"
	"golang.org/x/exp/slog"
)

func scanSnapShot(name string, pattern *regexp2.Regexp) (string, error) {
	slog.Debug("scan err log", slog.String("name", name), slog.String("pattern", pattern.String()))
	scanner, err := loadSnapShot()
	if err != nil {
		return "", err
	}

	var lines []string
	for scanner.Scan() {
		line := scanner.Text()
		err := scanner.Err()
		if err != nil {
			slog.Error("scan err log", err, slog.String("item", name))
			return "", err
		}
		slog.Debug("scan err log", slog.String("line", line))

		match, err := pattern.MatchString(line)
		if err != nil {
			slog.Error(
				"apply pattern", err,
				slog.String("item", name), slog.String("pattern", pattern.String()),
			)
		}
		slog.Debug("scan err log", slog.Any("match", match))

		if match {
			lines = append(lines, line)
		}
	}

	return strings.Join(lines, "\n"), nil
}
