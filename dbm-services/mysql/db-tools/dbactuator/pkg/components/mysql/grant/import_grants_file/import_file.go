package import_grants_file

import (
	"bufio"
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"os"
	"path/filepath"
	"time"
)

func (c *ImportGrantsFile) Import() (err error) {
	fp := filepath.Join(c.workDir, c.finalFilename)
	f, err := os.OpenFile(fp, os.O_RDONLY, os.ModePerm)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	conn, err := c.db.Db.Conn(context.Background())
	if err != nil {
		return err
	}
	_, err = conn.ExecContext(
		context.Background(),
		"SET sql_log_bin=0",
	)
	if err != nil {
		return err
	}
	defer func() {
		_ = conn.Close()
	}()
	logger.Info("disable binlog")

	doneCh := make(chan struct{})
	defer close(doneCh)
	counter := 1
	// 把日志放到异步打印, 要不然太多了
	go func() {
		ticker := time.NewTicker(1 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				logger.Info("%d/%d imported", counter, c.lineCount)
			case <-doneCh:
				logger.Info("%d/%d imported", counter, c.lineCount)
				return
			}
		}
	}()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		_, err = conn.ExecContext(context.Background(), line)
		if err != nil {
			logger.Error("import failed: %s", line, err.Error())
			return err
		}
		counter++
	}
	if err := scanner.Err(); err != nil {
		return err
	}

	doneCh <- struct{}{}

	return nil
}
