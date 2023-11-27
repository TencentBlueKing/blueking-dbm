// Package util TODO
package util

import (
	"bytes"
	"fmt"
	"log/slog"
	"os/exec"
	"reflect"
	"regexp"
	"strings"

	"github.com/pkg/errors"
)

// HasElem 元素是否在数组中存在
func HasElem(elem interface{}, slice interface{}) bool {
	defer func() {
		if err := recover(); err != nil {
			slog.Error("HasElem error", err)
		}
	}()
	arrV := reflect.ValueOf(slice)
	if arrV.Kind() == reflect.Slice || arrV.Kind() == reflect.Array {
		for i := 0; i < arrV.Len(); i++ {
			// XXX - panics if slice element points to an unexported struct field
			// see https://golang.org/pkg/reflect/#Value.Interface
			if arrV.Index(i).Interface() == elem {
				return true
			}
		}
	}
	return false
}

// SplitName TODO
// //切分用户传过来的IP字符串列表等
// //切分规则：
// //把\r+|\s+|;+|\n+|,+这些分隔符，转成字符串数组
// //返回字符串数组
func SplitName(input string) ([]string, error) {
	result := []string{}
	if reg, err := regexp.Compile(`\r+|\s+|;+|\n+`); err != nil {
		return result, err
	} else {
		// 若返回正确的正则表达式，则将分隔符换为 ,
		input = reg.ReplaceAllString(input, ",")
	}
	if reg, err := regexp.Compile(`^,+|,+$`); err != nil {
		return result, err
	} else {
		input = reg.ReplaceAllString(input, "")
	}
	if reg, err := regexp.Compile(`,+`); err != nil {
		return result, err
	} else {
		input = reg.ReplaceAllString(input, ",")
	}
	result = strings.Split(input, ",")
	return result, nil
}

// ExecShellCommand 执行 shell 命令
// 如果有 err, 返回 stderr; 如果没有 err 返回的是 stdout
func ExecShellCommand(isSudo bool, param string) (stdoutStr string, err error) {
	if isSudo {
		param = "sudo " + param
	}
	cmd := exec.Command("bash", "-c", param)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		return stderr.String(), errors.WithMessage(err, stderr.String())
	}

	if len(stderr.String()) > 0 {
		err = fmt.Errorf("execute shell command(%s) error:%s", param, stderr.String())
		return stderr.String(), err
	}

	return stdout.String(), nil
}
