package impl

import (
	"errors"
	"slices"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/go-sql-driver/mysql"
)

// retryAbleErrNum 这些错误码遇到时业务 SQL 会自动重试. 主要覆盖 ACL 锁相关的瞬时认证失败.
var retryAbleErrNum = []uint16{
	1130, // ERROR 1130 (HY000): Host is not allowed to connect
	1045, // ERROR 1045 (28000): Access denied for user
}

// retryOpts DoSQL 用的统一 retry 配置. 只对 retryAbleErrNum 里的错误码重试.
var retryOpts = []retry.Option{
	retry.RetryIf(IsRetryAbleError),
	retry.Attempts(3),
	retry.Delay(1 * time.Second),
	retry.DelayType(retry.FixedDelay),
}

// IsRetryAbleError 判断是否是"可以安全重试"的 mysql 错误.
func IsRetryAbleError(err error) bool {
	var me *mysql.MySQLError
	if errors.As(err, &me) && slices.Index(retryAbleErrNum, me.Number) >= 0 {
		return true
	}
	return false
}
