package externalhandler

import (
	"bufio"
	"io"

	"golang.org/x/exp/slog"
)

func (h *Handler) setupOutputStream() error {
	stdout, err := h.cmd.StdoutPipe()
	if err != nil {
		h.logger.Error("open stdout pipe", slog.String("error", err.Error()))
		return err
	}

	stderr, err := h.cmd.StderrPipe()
	if err != nil {
		h.logger.Error("open stderr pipe", slog.String("error", err.Error()))
		return err
	}

	go func(r io.Reader) {
		scanner := bufio.NewScanner(r)
		scanner.Split(bufio.ScanLines)
		for scanner.Scan() {
			h.latestStdout = scanner.Text()
			h.logger.Info("stream output", slog.String("stdout", h.latestStdout))
		}
	}(stdout)

	go func(r io.Reader) {
		scanner := bufio.NewScanner(r)
		scanner.Split(bufio.ScanLines)
		for scanner.Scan() {
			h.latestStderr = scanner.Text()
			h.logger.Error("stream output", slog.String("stderr", h.latestStderr))
		}
	}(stderr)

	return nil
}
