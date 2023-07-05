// Package util TODO
package util

import (
	"errors"
	"fmt"
	"hash/crc32"
	"net"
	"reflect"
	"runtime"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
)

// LocalIp component local ip
var LocalIp string

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

// HasElem TODO
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

// GetMonIp TODO
func GetMonIp() (string, error) {
	addr, err := net.InterfaceAddrs()

	if err != nil {
		return "", err
	}

	for _, address := range addr {
		// 检查ip地址判断是否回环地址
		if inet, ok := address.(*net.IPNet); ok && !inet.IP.IsLoopback() {
			if inet.IP.To4() != nil {
				return inet.IP.String(), nil
			}

		}
	}

	return "", errors.New("can not find the client ip address")
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
