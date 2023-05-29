package mysql_processlist

import (
	"strings"

	"github.com/dlclark/regexp2"
	"golang.org/x/exp/slog"
)

func mysqlInject() (string, error) {
	processList, err := loadSnapShot()
	if err != nil {
		return "", err
	}

	var injects []string
	for _, p := range processList {
		pstr, err := p.JsonString()
		if err != nil {
			return "", err
		}

		slog.Debug("mysql inject check process", slog.Any("process", pstr))

		if strings.ToLower(p.User.String) == "system user" {
			continue
		}

		hasSleep, err := hasLongUserSleep(p)
		if err != nil {
			return "", err
		}
		slog.Debug("mysql inject check process", slog.Bool("has user sleep", hasSleep))

		isLongSleep := hasSleep && p.Time.Int64 > 300
		slog.Debug("mysql inject check process", slog.Bool("is long sleep", isLongSleep))

		hasComment, err := hasCommentInQuery(p)
		if err != nil {
			return "", err
		}
		slog.Debug("mysql inject check process", slog.Bool("has inline comment", hasComment))

		if isLongSleep || hasComment {
			injects = append(injects, pstr)
		}
	}
	return strings.Join(injects, ","), nil
}

func hasLongUserSleep(p *mysqlProcess) (bool, error) {
	re := regexp2.MustCompile(`User sleep`, regexp2.IgnoreCase)
	match, err := re.MatchString(p.State.String)
	if err != nil {
		slog.Error("check long user sleep", err)
		return false, err
	}

	return match, nil
}

func hasCommentInQuery(p *mysqlProcess) (bool, error) {
	re := regexp2.MustCompile(`\s+#`, regexp2.IgnoreCase)
	match, err := re.MatchString(p.Command.String)
	if err != nil {
		slog.Error("check comment in query", err)
		return false, err
	}

	return match &&
			(strings.HasPrefix(strings.ToLower(p.Command.String), "update") ||
				strings.HasPrefix(strings.ToLower(p.Command.String), "delete")),
		nil
}
