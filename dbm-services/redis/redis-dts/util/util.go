// Package util TODO
package util

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"

	"go.uber.org/zap"
)

// NotFound error
const NotFound = "not found"

// NewNotFound ..
func NewNotFound() error {
	return errors.New(NotFound)
}

// IsNotFoundErr ..
func IsNotFoundErr(err error) bool {
	if err.Error() == NotFound {
		return true
	}
	return false
}

// MkDirIfNotExists 如果目录不存在则创建
func MkDirIfNotExists(dir string) error {
	_, err := os.Stat(dir)
	if err == nil {
		return nil
	}
	if os.IsNotExist(err) == true {
		err = os.MkdirAll(dir, 0750)
		if err != nil {
			return fmt.Errorf("MkdirAll fail,err:%v,dir:%s", err, dir)
		}
	}
	return nil
}

// CurrentExecutePath 当前可执行文件所在目录
func CurrentExecutePath() (string, error) {
	path01, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("os.Executable fail,err:%v", err)
	}
	return filepath.Dir(path01), nil
}

// GetLocalIP 获得本地ip
func GetLocalIP() (string, error) {
	var localIP string
	var err error
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return localIP, fmt.Errorf("GetLocalIP net.InterfaceAddrs fail,err:%v", err)
	}
	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				localIP = ipnet.IP.String()
				return localIP, nil
			}
		}
	}
	return localIP, fmt.Errorf("can't find local ip")
}

// FileLineCounter 计算文件行数
// 参考: https://stackoverflow.com/questions/24562942/golang-how-do-i-determine-the-number-of-lines-in-a-file-efficiently
func FileLineCounter(filename string) (lineCnt uint64, err error) {
	_, err = os.Stat(filename)
	if err != nil && os.IsNotExist(err) == true {
		return 0, fmt.Errorf("file:%s not exists", filename)
	}
	file, err := os.Open(filename)
	if err != nil {
		return 0, fmt.Errorf("file:%s open fail,err:%v", filename, err)
	}
	defer file.Close()
	reader01 := bufio.NewReader(file)
	buf := make([]byte, 32*1024)
	lineCnt = 0
	lineSep := []byte{'\n'}

	for {
		c, err := reader01.Read(buf)
		lineCnt += uint64(bytes.Count(buf[:c], lineSep))

		switch {
		case err == io.EOF:
			return lineCnt, nil

		case err != nil:
			return lineCnt, fmt.Errorf("file:%s read fail,err:%v", filename, err)
		}
	}
}

// CheckProcessAlive :通过kill 0检查进程是否存在
// https://stackoverflow.com/questions/15204162/check-if-a-process-exists-in-go-way
func CheckProcessAlive(pid int) (isAlive bool, err error) {
	process, err := os.FindProcess(pid)
	if err != nil {
		return false, fmt.Errorf("failed to find process,err:%v,pid:%d", err, pid)
	}
	err = process.Signal(syscall.Signal(0))
	if err != nil {
		// 进程不存在
		return false, nil
	}
	return true, nil
}

// KillProcess 杀死进程
func KillProcess(pid int) error {
	process, err := os.FindProcess(pid)
	if err != nil {
		return fmt.Errorf("Fail to find process,err:%v,pid:%d", err, pid)
	}
	err = process.Kill()
	if err != nil {
		return fmt.Errorf("Fail to kill process,err:%v pid:%d", err, pid)
	}
	return nil
}

// CheckPortIsInUse 检查端口是否被占用
func CheckPortIsInUse(ip, port string) (inUse bool, err error) {
	timeout := 3 * time.Second
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(ip, port), timeout)
	if err != nil && strings.Contains(err.Error(), "connection refused") {
		return false, nil
	} else if err != nil {
		return false, fmt.Errorf("net.DialTimeout fail,err:%v", err)
	}
	if conn != nil {
		defer conn.Close()
		return true, nil
	}
	return false, nil
}

// GetANotUsePort 获取一个进程未使用的端口
func GetANotUsePort(ip string, startPort, step int) (dstPort int, err error) {
	var inUse bool
	dstPort = startPort
	for {
		inUse, err = CheckPortIsInUse(ip, strconv.Itoa(dstPort))
		if err != nil {
			return 0, err
		}
		if inUse == false {
			return
		}
		dstPort = dstPort + step
	}
}

// GetPidThatUsePort 获取使用指定端口的进程的pid,
// 可能获取不成功,pid返回为"" or - 的情况
func GetPidThatUsePort(port int, logger *zap.Logger) (pid string, err error) {
	ret, err := RunLocalCmd("bash",
		[]string{"-c", fmt.Sprintf("netstat -ntlp|grep %d|awk '{print $7}'|awk -F / '{print $1}'", port)},
		"", nil, 30*time.Second, logger)
	if err != nil && strings.Contains(err.Error(), "Not all processes could be identified") == false {
		return "", err
	}
	pids := strings.Fields(ret)
	if len(pids) == 0 {
		return "", nil
	}
	return pids[0], nil
}

// IsDbDNS function to check is db domain
// for example:
// gamedb.test.spider.db
// gamedb.test.spider.db.
// gamedb.test.spider.db#20000
// gamedb.test.spider.db.#20000
func IsDbDNS(domainName string) bool {
	domainName = strings.TrimSpace(domainName)
	var pattern = `^((\w|-)+)\.((\w|-)+)\.((\w|-)+)\.db\.*#(\d+)|((\w|-)+)\.((\w|-)+)\.((\w|-)+)\.db:(\d+)|((\w|-)+)\.((\w|-)+)\.((\w|-)+)\.db\.*$`
	reg01 := regexp.MustCompile(pattern)
	idDNS := reg01.MatchString(domainName)
	if idDNS {
		return true
	}
	return false
}

// LookupDbDNSIPs nsloopup domain
func LookupDbDNSIPs(addr01 string) (addrs []string, err error) {
	addr01 = strings.TrimSpace(addr01)
	list01 := strings.Split(addr01, ":")
	if len(list01) != 2 {
		err = fmt.Errorf("target addr[%s] format not corret", addr01)
		return
	}
	ipPart := list01[0]
	portPart := list01[1]
	if IsDbDNS(ipPart) {
		uniqMap := make(map[string]bool)
		var idx int
		for idx = 0; idx < 1000; idx++ {
			ips, err := net.LookupIP(ipPart)
			if err != nil {
				err = fmt.Errorf("target addr[%s] could not get ips,err:%v\n", addr01, err)
				return addrs, err
			}
			for _, ip01 := range ips {
				ip02 := ip01
				if _, ok := uniqMap[ip02.String()]; ok == false {
					addrs = append(addrs, fmt.Sprintf("%s:%s", ip02.String(), portPart))
					uniqMap[ip02.String()] = true
				}
			}
			time.Sleep(1 * time.Microsecond)
		}
		return addrs, nil
	}
	addrs = []string{addr01}
	return
}

// ToString string
func ToString(param interface{}) string {
	if param == nil {
		return ""
	}
	ret, _ := json.Marshal(param)
	return string(ret)
}

// GetFileSize get file size
func GetFileSize(f string) (int64, error) {
	fd, err := os.Stat(f)
	if err != nil {
		return 0, err
	}
	return fd.Size(), nil
}

// IsFileExistsInCurrDir (TendisDTSServer可执行文件)同目录下,文件是否存在
func IsFileExistsInCurrDir(file string) (fullPath string, err error) {
	currentPath, err := CurrentExecutePath()
	if err != nil {
		return "", err
	}

	fullPath = filepath.Join(currentPath, file)
	_, err = os.Stat(fullPath)
	if err != nil && os.IsNotExist(err) == true {
		err = fmt.Errorf("%s not exists,err:%v", file, err)
		return "", err
	}
	return fullPath, nil
}

// IsToolExecutableInCurrDir (TendisDTSServer可执行文件)同目录下,工具是否存在,是否可执行
func IsToolExecutableInCurrDir(tool string) (fullPath string, err error) {
	fullPath, err = IsFileExistsInCurrDir(tool)
	if err != nil {
		return "", err
	}
	_, err = os.Stat(fullPath)
	if err != nil && os.IsPermission(err) == true {
		err = os.Chmod(fullPath, 0774)
		if err != nil {
			err = fmt.Errorf("%s os.Chmod 0774 fail,err:%v", fullPath, err)
			return fullPath, err
		}
	}
	return
}
