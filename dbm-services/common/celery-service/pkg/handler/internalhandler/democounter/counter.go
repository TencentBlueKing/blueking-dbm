package democounter

import (
	"context"
	"encoding/json"
	"time"

	"github.com/pkg/errors"
	"golang.org/x/exp/slog"

	"celery-service/pkg/log"
)

type Handler struct {
	logger *slog.Logger
}

func (h *Handler) ClusterType() string {
	return "TendbHA"
}

func (h *Handler) Name() string {
	return "Counter"
}

// Worker
/*
当工作可能耗时很长, 或者需要循环很多次时
需要在需要的位置监听 ctx.Done 来响应调用方的终止信号
否则任务一旦启动, 就只能等到完成或者出错
*/
func (h *Handler) Worker(body []byte, ctx context.Context) (string, error) {
	var postArg struct {
		Counter int `json:"counter"`
	}

	err := json.Unmarshal(body, &postArg)
	if err != nil {
		h.logger.Error("unmarshal post arg", slog.String("error", err.Error()))
		return "", err
	}

	for i := 0; i < postArg.Counter; i++ {
		select {
		case <-ctx.Done():
			err := errors.Errorf("canceled")
			h.logger.Error("worker", slog.String("error", err.Error()))
			return "", err
		default:
			h.logger.Info("demo", slog.Time("time", time.Now()), slog.Int("i", i))
			time.Sleep(1 * time.Second)
		}
	}
	return "hello world", nil
}

func NewHandler() *Handler {
	return &Handler{
		logger: log.GetLogger("demo"),
	}
}
