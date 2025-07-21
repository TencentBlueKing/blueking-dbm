package impl

import (
	"time"

	"github.com/avast/retry-go/v4"
)

// SQLResultRow
/*
{
	COLNAME1: COLVALUE1,
	COLNAME2: COLVALUE2,
}
*/
type SQLResultRow map[string]interface{}

// SQLResultRows
/*
[
	{...}, # row1
	{...}, # row2
]
*/
type SQLResultRows []SQLResultRow

var retryOpts []retry.Option

var queryCmds = []string{
	"use",
	"explain",
	"select",
	"show",
	"desc",
}
var retryAbleErrNum []uint16

func init() {
	retryOpts = []retry.Option{
		retry.RetryIf(IsRetryAbleError),
		retry.Attempts(3),
		retry.Delay(1 * time.Second),
		retry.DelayType(retry.FixedDelay),
	}

	retryAbleErrNum = []uint16{
		1130, // ERROR 1130 (HY000): Host is not allowed to connect
		1045, // ERROR 1045 (28000): Access denied for user
	}
}
