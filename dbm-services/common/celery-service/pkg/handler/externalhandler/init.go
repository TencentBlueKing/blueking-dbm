package externalhandler

import (
	"golang.org/x/exp/slog"

	"celery-service/pkg/log"
)

var logger *slog.Logger

func init() {
	logger = log.GetLogger("root")
}
