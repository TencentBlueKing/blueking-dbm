package mysql_errlog

import (
	"fmt"
	"strings"

	"github.com/dlclark/regexp2"
)

func init() {
	mysqlCriticalExcludePattern = regexp2.MustCompile(
		fmt.Sprintf(
			`^(?!.*(?:(%s)))`,
			strings.Join(
				[]string{
					"checkpoint",
					"server_errno=2013",
					"sort aborted",
					"restarting transaction",
					"slave SQL thread was killed",
					`\[Warning\]`,
				},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)
}

func mysqlCritical() (string, error) {
	return scanSnapShot(nameMySQLErrCritical, mysqlCriticalExcludePattern)
}
