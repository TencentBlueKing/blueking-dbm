package mysql_errlog

import (
	"fmt"
	"strings"

	"github.com/dlclark/regexp2"
)

func init() {
	mysqlNoticePattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"slave SQL thread was killed"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

}

func mysqlNotice() (string, error) {
	return scanSnapShot(nameMySQLErrNotice, mysqlNoticePattern)
}
