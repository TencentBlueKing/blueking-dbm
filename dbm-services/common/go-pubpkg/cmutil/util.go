// Package cmutil TODO
package cmutil

import (
	"time"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// RetryConfig TODO
type RetryConfig struct {
	Times     int           // 重试次数
	DelayTime time.Duration // 每次重试间隔
}

// RetriesExceeded TODO
// retries exceeded
const RetriesExceeded = "retries exceeded"

// Retry 重试
// 第 0 次也需要 delay 再运行
func Retry(r RetryConfig, f func() error) (err error) {
	for i := 0; i < r.Times; i++ {
		time.Sleep(r.DelayTime)
		if err = f(); err == nil {
			return nil
		}
		logger.Warn("第%d次重试,函数错误:%s", i, err.Error())
	}
	if err != nil {
		return errors.Wrap(err, RetriesExceeded)
	}
	return
}
