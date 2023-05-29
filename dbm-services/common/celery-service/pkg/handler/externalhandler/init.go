package externalhandler

import (
	"log/slog"

	"celery-service/pkg/log"
)

var logger *slog.Logger

func init() {
	logger = log.GetLogger("root")
}
