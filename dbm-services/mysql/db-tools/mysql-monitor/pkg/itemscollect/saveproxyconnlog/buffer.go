package saveproxyconnlog

import (
	"context"
	"log/slog"

	"github.com/jmoiron/sqlx"
)

const defaultBatchSize = 100 // 默认批量写入大小

// batchWrite 将条目列表分批写入后端 MySQL
// 每批最多 batchSize 条
func batchWrite(ctx context.Context, conn *sqlx.Conn, entries []*ConnLogEntry, proxyIP string, batchSize int) error {
	if len(entries) == 0 {
		return nil
	}

	if batchSize <= 0 {
		batchSize = defaultBatchSize
	}

	total := len(entries)
	for i := 0; i < total; i += batchSize {
		end := i + batchSize
		if end > total {
			end = total
		}

		batch := entries[i:end]
		if err := batchInsert(ctx, conn, batch, proxyIP); err != nil {
			slog.Error("batch write failed",
				slog.String("error", err.Error()),
				slog.Int("batch_start", i),
				slog.Int("batch_end", end),
			)
			return err
		}
	}

	slog.Info("batch write completed", slog.Int("total", total))
	return nil
}
