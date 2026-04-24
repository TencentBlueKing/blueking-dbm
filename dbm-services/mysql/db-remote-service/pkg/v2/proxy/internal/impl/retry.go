package impl

import (
	"errors"
	"slices"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/go-sql-driver/mysql"
)

var retryAbleErrNum = []uint16{
	1130, // ERROR 1130 (HY000): Host is not allowed to connect
	1045, // ERROR 1045 (28000): Access denied for user
}

var retryOpts = []retry.Option{
	retry.RetryIf(IsRetryAbleError),
	retry.Attempts(3),
	retry.Delay(1 * time.Second),
	retry.DelayType(retry.FixedDelay),
}

func IsRetryAbleError(err error) bool {
	var me *mysql.MySQLError
	if errors.As(err, &me) && slices.Index(retryAbleErrNum, me.Number) >= 0 {
		return true
	}
	return false
}
