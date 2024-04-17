// Package util TODO
package util

import (
	"bytes"
	"fmt"
	"hash/crc32"
	"net"
	"os/exec"
	"reflect"
	"runtime"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"

	"github.com/pkg/errors"
)

const (
	tcpDialTimeout = 3 * time.Second
)

// AtWhere return the parent function name.
func AtWhere() string {
	pc, _, _, ok := runtime.Caller(1)
	if ok {
		fileName, line := runtime.FuncForPC(pc).FileLine(pc)
		result := strings.Index(fileName, "/tenjob/")
		if result > 1 {
			preStr := fileName[0:result]
			fileName = strings.Replace(fileName, preStr, "", 1)
		}
		//		method := runtime.FuncForPC(pc).Name()
		//		return fmt.Sprintf("%s [%s] line:%d", fileName, method, line)

		return fmt.Sprintf("%s:%d", fileName, line)
	} else {
		return "Method not Found!"
	}
}

// HasElem check whether element exist info slice
// if exists, return true
func HasElem(elem interface{}, slice interface{}) bool {
	defer func() {
		if err := recover(); err != nil {
			log.Logger.Errorf("HasElem error %s at  %s", err, AtWhere())
		}
	}()
	arrV := reflect.ValueOf(slice)
	if arrV.Kind() == reflect.Slice || arrV.Kind() == reflect.Array {
		for i := 0; i < arrV.Len(); i++ {
			// XXX - panics if slice element points to an unexported struct field
			// see https://golang.org/pkg/reflect/#Value.Interface
			if reflect.DeepEqual(arrV.Index(i).Interface(), elem) {
				return true
			}
		}
	}
	return false
}

// HostCheck TODO
func HostCheck(host string) bool {
	_, err := net.DialTimeout("tcp", host, time.Duration(tcpDialTimeout))
	if err != nil {
		log.Logger.Error(err.Error())
		return false
	}
	return true
}

// CRC32 TODO
func CRC32(str string) uint32 {
	return crc32.ChecksumIEEE([]byte(str))
}

// CheckRedisErrIsAuthFail check if the return error of
//
//	redis api is authentication failure,
//	this function support four type server and two status.
//
// server type: rediscache tendisplus twemproxy and predixy
// status: api lack password and the password is invalid
func CheckRedisErrIsAuthFail(err error) bool {
	errInfo := err.Error()
	if strings.Contains(errInfo, constvar.RedisPasswordInvalid) {
		// this case is the status of the password is invalid,
		//  rediscache tendisplus twemproxy and predixy match this case
		return true
	} else if strings.Contains(errInfo, constvar.RedisPasswordLack) {
		// this case is the status of lack password,
		//	rediscache tendisplus twemproxy match this case, predixy un-match
		return true
	} else if strings.Contains(errInfo, constvar.PredixyPasswordLack) {
		// this case is the status of lack password
		//  predixy match this case
		return true
	} else {
		return false
	}
}

// CheckSSHErrIsAuthFail check if the the return error of ssh api
//
//	is authentication failure.
func CheckSSHErrIsAuthFail(err error) bool {
	errInfo := err.Error()
	// ssh lack password or password is invalid will return the same error
	if strings.Contains(errInfo, constvar.SSHPasswordLackORInvalid) {
		return true
	} else {
		return false
	}
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

// IntSlice2String 效果：[]int{1,2,3,4} -> "1,2,3,4"
func IntSlice2String(elements []int, sep string) string {
	elemStr := ""
	if len(elements) > 0 {
		for i, elem := range elements {
			if i == (len(elements) - 1) {
				elemStr += fmt.Sprintf("%d", elem)
				break
			}
			elemStr += fmt.Sprintf("%d%s", elem, sep)
		}
	}
	return elemStr
}
