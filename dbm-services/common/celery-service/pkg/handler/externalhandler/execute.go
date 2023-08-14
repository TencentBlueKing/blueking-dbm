package externalhandler

import (
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

func (h *Handler) execute() (string, error) {
	err := h.setupOutputStream()
	if err != nil {
		return "", err
	}

	if err := h.cmd.Start(); err != nil {
		h.logger.Error("exec start", slog.String("error", err.Error()))
		return "", errors.Errorf("exec start failed: %s", err.Error())
	}

	if err := h.cmd.Wait(); err != nil {
		h.logger.Error("exec wait", slog.String("error", err.Error()))
		return "", errors.Errorf("exec error: %s (%s)", err.Error(), h.latestStderr)
	}

	return h.latestStdout, nil
}
