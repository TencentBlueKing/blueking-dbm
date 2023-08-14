package internalhandler

import (
	"celery-service/pkg/handler/internalhandler/democounter"
)

var handlers []interface{}

func InternalHandlers() []interface{} {
	handlers = append(handlers, []interface{}{
		democounter.NewHandler(),
	}...)

	return handlers
}
