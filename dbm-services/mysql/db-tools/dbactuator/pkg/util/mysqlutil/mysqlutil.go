// Package mysqlutil TODO
package mysqlutil

import (
	"bytes"
	"fmt"
	"os/exec"
	"regexp"
	"strings"

	"dbm-services/common/go-pubpkg/mysqlcomm"

	"github.com/pkg/errors"
)

// ExecCommandMySQLShell 执行 mysql / mysqladmin 专用 shell
// 会移除 password insecure 信息
// 如果 err 不为空，则返回 stderr 信息，否则返回 stdout 信息
//
// 如果 cmdString 执行 err==nil, 也会判断 stderr 信息如果不为空则重新封装成 error 返回
// 如果 cmdString 执行 err!=nil, 则直接返回 stderr
// 如果 cmdString 执行 err==nil, 且 stderr 为空, 则返回 stdout
func ExecCommandMySQLShell(cmdString string) (outputStr string, err error) {
	cmd := exec.Command("bash", "-c", cmdString)
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
		//err = fmt.Errorf("execute command(%s) has stderr:%s", mysqlcomm.ClearSensitiveInformation(cmdString), errStr)
		err = fmt.Errorf("run command error:%s", mysqlcomm.ClearSensitiveInformation(cmdString))
		return errStr, err
	}
	return stdout.String(), nil
}
