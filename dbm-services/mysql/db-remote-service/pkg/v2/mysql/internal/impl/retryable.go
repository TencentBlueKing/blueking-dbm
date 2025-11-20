package impl

import (
	"errors"
	"slices"

	"github.com/go-sql-driver/mysql"
)

func IsRetryAbleError(err error) bool {
	var me *mysql.MySQLError
	if errors.As(err, &me) && slices.Index(retryAbleErrNum, me.Number) >= 0 {
		return true
	}
	return false
}
