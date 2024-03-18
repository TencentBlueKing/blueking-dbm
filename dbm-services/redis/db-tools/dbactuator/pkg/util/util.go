// Package util 公共函数
package util

import (
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"net"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"syscall"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"

	"github.com/dustin/go-humanize"
	"golang.org/x/sys/unix"
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

// GetCurrentDirectory 获取当前二进制程序所在执行路径
func GetCurrentDirectory() (string, error) {
	dir, err := filepath.Abs(filepath.Dir(os.Args[0]))
	if err != nil {
		return dir, fmt.Errorf("convert absolute path failed, err: %+v", err)
	}
	dir = strings.Replace(dir, "\\", "/", -1)
	return dir, nil
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

// IsMountPoint Determine if a directory is a mountpoint, by comparing the device for the directory
// with the device for it's parent.  If they are the same, it's not a mountpoint, if they're
// different, it is.
// reference: https://github.com/cnaize/kubernetes/blob/master/pkg/util/mount/mountpoint_unix.go#L29
func IsMountPoint(file string) (bool, error) {
	stat, err := os.Stat(file)
	if err != nil {
		return false, err
	}
	rootStat, err := os.Lstat(file + "/..")
	if err != nil {
		return false, err
	}
	// If the directory has the same device as parent, then it's not a mountpoint.
	return stat.Sys().(*syscall.Stat_t).Dev != rootStat.Sys().(*syscall.Stat_t).Dev, nil
}

// FindFirstMountPoint find first mountpoint in prefer order
func FindFirstMountPoint(paths ...string) (string, error) {
	for _, path := range paths {
		if _, err := os.Stat(path); err != nil {
			if os.IsNotExist(err) {
				continue
			}
		}
		isMountPoint, err := IsMountPoint(path)
		if err != nil {
			return "", fmt.Errorf("check whether mountpoint failed, path: %s, err: %v", path, err)
		}
		if isMountPoint {
			return path, nil
		}
	}
	return "", fmt.Errorf("no available mountpoint found, choices: %#v", paths)
}

// CheckPortIsInUse 检查端口是否被占用
func CheckPortIsInUse(ip, port string) (inUse bool, err error) {
	timeout := time.Second
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(ip, port), timeout)
	if err != nil && strings.Contains(err.Error(), "connection refused") {
		return false, nil
	} else if err != nil {
		return false, fmt.Errorf("net.DialTimeout fail,err:%v", err)
	}
	if conn != nil {
		defer func(conn net.Conn) {
			_ = conn.Close()
		}(conn)
		return true, nil
	}
	return false, nil
}

// IsValidIP 判断字符串是否是一个有效IP
func IsValidIP(ipStr string) bool {
	if net.ParseIP(ipStr) == nil {
		return false
	}
	return true
}

// MkDirsIfNotExists 如果目录不存在则创建
func MkDirsIfNotExists(dirs []string) error {
	return MkDirsIfNotExistsWithPerm(dirs, 0755)
}

// MkDirsIfNotExistsWithPerm 如果目录不存在则创建，并指定文件Perm
func MkDirsIfNotExistsWithPerm(dirs []string, perm os.FileMode) error {
	for _, dir := range dirs {
		_, err := os.Stat(dir)
		if err == nil {
			continue
		}
		if os.IsNotExist(err) == true {
			err = os.MkdirAll(dir, perm)
			if err != nil {
				return fmt.Errorf("MkdirAll fail,err:%v,dir:%s", err, dirs)
			}
		}
	}
	return nil
}

// IsExecOwner owner是否可执行
func IsExecOwner(mode os.FileMode) bool {
	return mode&0100 != 0
}

// IsExecGroup grouper是否可执行
func IsExecGroup(mode os.FileMode) bool {
	return mode&0010 != 0
}

// IsExecOther other是否可执行
func IsExecOther(mode os.FileMode) bool {
	return mode&0001 != 0
}

// IsExecAny owner/grouper/other 任意一个可执行
func IsExecAny(mode os.FileMode) bool {
	return mode&0111 != 0
}

// IsExecAll owner/grouper/other 全部可执行
func IsExecAll(mode os.FileMode) bool {
	return mode&0111 == 0111
}

// LocalDirChownMysql 改变localDir的属主为mysql
func LocalDirChownMysql(localDir string) (err error) {
	cmd := fmt.Sprintf("chown -R %s.%s %s", consts.MysqlAaccount, consts.MysqlGroup, localDir)
	_, err = RunBashCmd(cmd, "", nil, 1*time.Hour)
	return
}

// LocalFileChmodAllRead 改变localFile的权限为所有人可读
func LocalFileChmodAllRead(localFile string) (err error) {
	cmd := fmt.Sprintf("chmod a+r %s", localFile)
	_, err = RunBashCmd(cmd, "", nil, 1*time.Hour)
	return
}

// HostDiskUsage 本地路径所在磁盘使用情况
type HostDiskUsage struct {
	TotalSize  uint64 `json:"ToTalSize"` // bytes
	UsedSize   uint64 `json:"UsedSize"`  // bytes
	AvailSize  uint64 `json:"AvailSize"` // bytes
	UsageRatio int    `json:"UsageRatio"`
}

// String 用于打印
func (disk *HostDiskUsage) String() string {
	ret := fmt.Sprintf("total_size=%dMB,used_size=%d,avail_size=%d,Use=%d%%",
		disk.TotalSize/1024/1024,
		disk.UsedSize/1024/1024,
		disk.AvailSize/1024/1024,
		disk.UsageRatio)
	return ret
}

// GetLocalDirDiskUsg 获取本地路径所在磁盘使用情况
// 参考:
// https://stackoverflow.com/questions/20108520/get-amount-of-free-disk-space-using-go
// http://evertrain.blogspot.com/2018/05/golang-disk-free.html
func GetLocalDirDiskUsg(localDir string) (diskUsg HostDiskUsage, err error) {
	var stat unix.Statfs_t
	if err = unix.Statfs(localDir, &stat); err != nil {
		err = fmt.Errorf("unix.Statfs fail,err:%v,localDir:%s", err, localDir)
		return
	}
	diskUsg.TotalSize = stat.Blocks * uint64(stat.Bsize)
	diskUsg.AvailSize = stat.Bavail * uint64(stat.Bsize)
	diskUsg.UsedSize = (stat.Blocks - stat.Bfree) * uint64(stat.Bsize)
	diskUsg.UsageRatio = int(diskUsg.UsedSize * 100 / diskUsg.TotalSize)
	return
}

// GetFileSize 获取文件大小(单位byte)
func GetFileSize(filename string) (size int64, err error) {
	fileInfo, err := os.Stat(filename)
	if err != nil {
		err = fmt.Errorf("file:%s os.Stat fail,err:%v", filename, err)
		return
	}
	return fileInfo.Size(), nil
}

// IntSliceInter 两个[]int 求交集
func IntSliceInter(list01, list02 []int) []int {
	m01 := make(map[int]bool)
	m02 := make(map[int]bool)
	for _, item01 := range list01 {
		m01[item01] = true
	}
	for _, item02 := range list02 {
		m02[item02] = true
	}
	ret := []int{}
	for item01 := range m01 {
		if _, ok := m02[item01]; ok == true {
			ret = append(ret, item01)
		}
	}
	sort.Ints(ret)
	return ret
}

// IntSliceToString 将[]int join,返回一个字符串
func IntSliceToString(src []int, seq string) string {
	strList := []string{}
	for _, item := range src {
		strList = append(strList, strconv.Itoa(item))
	}
	return strings.Join(strList, seq)
}

// IsDbmSysKeys 是否是dbm 系统相关的管理key,如监控、心跳key等的key
func IsDbmSysKeys(key string) bool {
	if key == "master_ip" || key == "master_port" || key == "twemproxy_mon" {
		return true
	}
	if strings.HasPrefix(key, "dbmon:") ||
		strings.HasPrefix(key, "dbha:agent:") ||
		strings.HasSuffix(key, ":timediff") ||
		strings.HasSuffix(key, ":time") ||
		strings.HasSuffix(key, ":0:dbsize") ||
		strings.HasSuffix(key, ":heartbeat") {
		return true
	}
	return false
}

// NewNotFoundErr TODO
func NewNotFoundErr() error {
	return errors.New(NotFound)
}

// AddrToIpPort 将ip:port转换为ip,port
func AddrToIpPort(addr string) (ip string, port int, err error) {
	ipPort := strings.Split(addr, ":")
	if len(ipPort) != 2 {
		err = fmt.Errorf("invalid addr:%s", addr)
		return
	}
	ip = ipPort[0]
	port, err = strconv.Atoi(ipPort[1])
	if err != nil {
		err = fmt.Errorf("invalid addr:%s,err:%v", addr, err)
		return
	}
	return
}

// ToString string
func ToString(param interface{}) string {
	ret, _ := json.Marshal(param)
	return string(ret)
}

// SizeToHumanStr 将字节大小转换为人类可读的字符串
// 如: 1024 -> 1KiB, 1024*1024 -> 1MiB, 1024*1024*1024 -> 1GiB
func SizeToHumanStr(ssize int64) string {
	if ssize >= 0 {
		return "+" + humanize.BigIBytes((&big.Int{}).SetInt64(ssize))
	}
	return "-" + humanize.BigIBytes((&big.Int{}).SetInt64(-ssize))
}
