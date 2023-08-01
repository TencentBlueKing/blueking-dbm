package handler

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"

	"celery-service/pkg/config"
)

type InternalBase struct {
	logger *slog.Logger
}

func (i *InternalBase) SetLogger(logger *slog.Logger) {
	i.logger = logger
}

type IInternalHandler interface {
	IHandler
	SetLogger(*slog.Logger)
}

func addInternalHandler(ih IInternalHandler) {
	ih.SetLogger(slog.New(
		slog.NewTextHandler(
			io.MultiWriter(
				&lumberjack.Logger{
					Filename: filepath.Join(
						config.BaseDir, "logs",
						strings.ToLower(ih.Name()),
						fmt.Sprintf("%s.log", strings.ToLower(ih.Name()))),
					MaxSize:    100,
					MaxAge:     30,
					MaxBackups: 50,
				},
				os.Stdout,
			),
			&slog.HandlerOptions{
				AddSource: true,
			},
		),
	).With("name", ih.Name()))

	if _, ok := Handlers[ih.ClusterType()]; !ok {
		Handlers[ih.ClusterType()] = []IHandler{}
	}

	Handlers[ih.ClusterType()] = append(Handlers[ih.ClusterType()], ih)
}
