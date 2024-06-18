package mysqlerrlog

import (
	"fmt"
	"strings"

	"github.com/dlclark/regexp2"
)

func init() {
	mysqldRestartPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{
					"mysqld_safe mysqld restarted",
				},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)
}
func mysqldRestart() (string, error) {
	return scanSnapShot(nameMySQLDRestart, mysqldRestartPattern)
}
