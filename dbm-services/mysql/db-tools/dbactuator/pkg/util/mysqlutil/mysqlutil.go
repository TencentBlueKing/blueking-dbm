// Package mysqlutil TODO
package mysqlutil

import (
	"bytes"
	"fmt"
	"os/exec"
	"regexp"
	"strings"

	"github.com/pkg/errors"
)

// ExecCommandMySQLShell 执行 mysql / mysqladmin 专用shell
// 会移除 password insecure 信息
func ExecCommandMySQLShell(param string) (stdoutStr string, err error) {
	cmd := exec.Command("bash", "-c", param)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		return stderr.String(), errors.WithMessage(err, stderr.String())
	}
	errStr := stderr.String()
	reg := regexp.MustCompile(`(?U)\n?.*Using a password on the command line interface can be insecure.`)
	errStr = strings.TrimSpace(reg.ReplaceAllString(errStr, ""))
	if len(errStr) > 0 {
		err = fmt.Errorf("execute command(%s) has stderr:%s", ClearSensitiveInformation(param), errStr)
		return errStr, err
	}
	return stdout.String(), nil
}
