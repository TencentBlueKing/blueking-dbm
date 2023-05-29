package handler

import (
	"context"
	"encoding/json"
	"log/slog"
	"slices"

	"github.com/pkg/errors"

	"celery-service/pkg/handler/externalhandler"
	"celery-service/pkg/handler/internalhandler"
	"celery-service/pkg/log"
)

var logger *slog.Logger

type IHandler interface {
	ClusterType() string
	Name() string
	Worker([]byte, context.Context) (string, error)
	Enable() bool
	EmptyParam() json.RawMessage
}

var Handlers = make(map[string][]IHandler)

func InitHandlers() error {
	logger = log.GetLogger("root")

	for _, eh := range externalhandler.ExternalHandlers() {
		if eh.Name() == "root" {
			err := errors.Errorf("task name can't be 'root'")
			logger.Error("register external handler", slog.String("error", err.Error()))
			return err
		}

		if _, ok := Handlers[eh.ClusterType()]; !ok {
			Handlers[eh.ClusterType()] = []IHandler{}
		}

		if slices.ContainsFunc(Handlers[eh.ClusterType()], func(i IHandler) bool {
			return eh.Name() == i.Name()
		}) {
			err := errors.Errorf("duplicate task found: %s/%s", eh.ClusterType(), eh.Name())
			logger.Error("register external handler", slog.String("error", err.Error()))
			return err
		}

		Handlers[eh.ClusterType()] = append(Handlers[eh.ClusterType()], eh)
	}

	for _, ii := range internalhandler.InternalHandlers() {
		ih, ok := ii.(IHandler)
		if !ok {
			err := errors.Errorf("%v can't cast to IHandler", ii)
			logger.Error("register internal handler", slog.String("error", err.Error()))
			return err
		}

		if ih.Name() == "root" {
			err := errors.Errorf("task name can't be 'root'")
			logger.Error("register internal handler", slog.String("error", err.Error()))
			return err
		}

		if _, ok := Handlers[ih.ClusterType()]; !ok {
			Handlers[ih.ClusterType()] = []IHandler{}
		}

		if slices.ContainsFunc(Handlers[ih.ClusterType()], func(i IHandler) bool {
			return ih.Name() == i.Name()
		}) {
			err := errors.Errorf("duplicate task found: %s/%s", ih.ClusterType(), ih.Name())
			logger.Error("register internal handler", slog.String("error", err.Error()))
			return err
		}

		Handlers[ih.ClusterType()] = append(Handlers[ih.ClusterType()], ih)
	}

	return nil
}
