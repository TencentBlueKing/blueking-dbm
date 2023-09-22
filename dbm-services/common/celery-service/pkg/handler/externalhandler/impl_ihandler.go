package externalhandler

import (
	"context"
	"encoding/json"
	"log/slog"
	"os/exec"
	"strings"

	"celery-service/pkg/log"
)

type Handler struct {
	item         *externalItem
	bin          string
	args         []string
	cmd          *exec.Cmd
	ctx          context.Context
	latestStdout string
	latestStderr string
	logger       *slog.Logger
}

func (h *Handler) ClusterType() string {
	return h.item.ClusterType
}

func (h *Handler) Name() string {
	return h.item.Name
}

func (h *Handler) Worker(body []byte, ctx context.Context) (string, error) {
	var postArgs []string
	if len(body) > 0 {
		if err := json.Unmarshal(body, &postArgs); err != nil {
			h.logger.Error("unmarshal body", slog.String("error", err.Error()))
			return "", err
		}
	}
	h.logger.Info("external handler", slog.Any("post args", postArgs))

	var cmdArgs []string
	switch h.bin {
	case "sh", "bash":
		cmdArgs = []string{
			"-c",
			strings.Join(mergeSlices(h.args, postArgs), " "),
		}
	default:
		cmdArgs = mergeSlices(h.args, postArgs)
	}

	h.cmd = exec.CommandContext(ctx, h.bin, cmdArgs...)
	h.logger.Info("generate cmd", slog.Any("command", h.cmd))

	return h.execute()
}

func (h *Handler) Enable() bool {
	return true
}

func (h *Handler) EmptyParam() json.RawMessage {
	empty, _ := json.Marshal([]string{})
	return empty
}

func newHandler(item *externalItem) *Handler {
	bin, args := splitBinArgs(item)

	return &Handler{
		item:   item,
		bin:    bin,
		args:   args,
		logger: log.GetLogger(item.Name),
	}
}
