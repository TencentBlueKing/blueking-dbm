// Package common 公共函数
package common

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	stderrors "errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
)

const mongoShutdownPollInterval = 500 * time.Millisecond

// isErrNoSuchProcess reports whether err means the target PID no longer exists (syscall.Kill ESRCH).
// Uses errno checks plus a string fallback for environments where errors.Is does not match as expected.
func isErrNoSuchProcess(err error) bool {
	if err == nil {
		return false
	}
	if stderrors.Is(err, syscall.ESRCH) {
		return true
	}
	var errno syscall.Errno
	if stderrors.As(err, &errno) && errno == syscall.ESRCH {
		return true
	}
	return strings.Contains(strings.ToLower(err.Error()), "no such process")
}

// UnTarAndCreateSoftLinkAndChown 解压目录，创建软链接并修改属主
func UnTarAndCreateSoftLinkAndChown(runtime *jobruntime.JobGenericRuntime, binDir string, installPackagePath string,
	unTarPath string,
	installPath string, user string, group string) error {
	// 解压安装包
	if !util.FileExists(unTarPath) {
		// 解压到/usr/local目录下
		runtime.Logger.Info("start to unTar install package")
		tarCmd := fmt.Sprintf("tar -zxf %s -C %s", installPackagePath, binDir)
		if _, err := util.RunBashCmd(tarCmd, "", nil, 60*time.Second); err != nil {
			runtime.Logger.Error("untar install file  fail, error:%s", err)
			return fmt.Errorf("untar install file  fail, error:%s", err)
		}
		runtime.Logger.Info("unTar install package successfully")
		// 修改属主
		runtime.Logger.Info("start to execute chown command for unTar directory")
		if _, err := util.RunBashCmd(
			fmt.Sprintf("chown -R %s:%s %s", user, group, unTarPath),
			"", nil,
			60*time.Second); err != nil {
			runtime.Logger.Error("chown untar directory fail, error:%s", err)
			return fmt.Errorf("chown untar directory fail, error:%s", err)
		}
		runtime.Logger.Info("execute chown command for unTar directory successfully")
	}

	// 创建软链接
	if !util.FileExists(installPath) {
		// 创建软链接
		runtime.Logger.Info("start to create soft link")
		softLink := fmt.Sprintf("ln -s %s %s", unTarPath, installPath)
		if _, err := util.RunBashCmd(softLink, "", nil, 60*time.Second); err != nil {
			runtime.Logger.Error("install directory create softLink fail, error:%s", err)
			return fmt.Errorf("install directory create softLink fail, error:%s", err)
		}
		runtime.Logger.Info("create soft link successfully")

		// 修改属主
		runtime.Logger.Info("start to execute chown command for softLink directory")
		if _, err := util.RunBashCmd(
			fmt.Sprintf("chown -R %s:%s %s", user, group, installPath),
			"", nil,
			60*time.Second); err != nil {
			runtime.Logger.Error("chown softlink directory fail, error:%s", err)
			return fmt.Errorf("chown softlink directory fail, error:%s", err)
		}
		runtime.Logger.Info("execute chown command for softLink directory successfully")

	}

	return nil
}

// GetMd5 获取md5值
func GetMd5(str string) string {
	h := md5.New()
	h.Write([]byte(str))
	return hex.EncodeToString(h.Sum(nil))
}

// CheckMongoVersion 检查mongo版本
func CheckMongoVersion(binDir string, mongoName string) (string, error) {
	cmd := fmt.Sprintf("%s -version |grep -E 'db version|mongos version'| awk -F \" \" '{print $3}' |sed 's/v//g'",
		filepath.Join(binDir, "mongodb", "bin", mongoName))
	getVersion, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	getVersion = strings.Replace(getVersion, "\n", "", -1)
	if strings.Contains(getVersion, "-") {
		getVersion = strings.Split(getVersion, "-")[0]
	}
	if err != nil {
		return "", err
	}
	return getVersion, nil
}

// CheckMongoService 检查mongo服务是否存在
func CheckMongoService(port int) (bool, string, error) {
	// netstat prints "Not all processes could be identified..." to stderr when not root; ignore it.
	// Match LISTEN rows and local :port (any bind: 127.0.0.1, eth, ::1); avoid matching remote port in ESTABLISHED or 128017.
	cmd := fmt.Sprintf(
		"netstat -ntpl 2>/dev/null | grep LISTEN | grep -E ':%d[[:space:]]' | awk '{print $7}' | head -1", port)
	result, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		return false, "", err
	}
	if strings.Contains(result, "mongos") {
		return true, "mongos", nil
	}
	if strings.Contains(result, "mongod") {
		return true, "mongod", nil
	}
	return false, "", nil
}

// CreateFileAndChown 创建Auth配置文件并修改属主
func CreateFileAndChown(runtime *jobruntime.JobGenericRuntime, filePath string,
	fileContent []byte, user string, group string, defaultPerm os.FileMode) error {
	runtime.Logger.Info("start to create %s file", filePath)
	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, defaultPerm)
	if err != nil {
		runtime.Logger.Error("create %s file fail, error:%s", filePath, err)
		return fmt.Errorf("create %s file fail, error:%s", filePath, err)
	}
	defer file.Close()
	if _, err = file.WriteString(string(fileContent)); err != nil {
		runtime.Logger.Error("%s file write content fail, error:%s", filePath, err)
		return fmt.Errorf("%s file write content  fail, error:%s", filePath, err)
	}
	runtime.Logger.Info("create %s file successfully", filePath)

	// 修改配置文件属主
	runtime.Logger.Info("start to execute chown command for %s file", filePath)
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s:%s %s", user, group, filePath),
		"", nil,
		60*time.Second); err != nil {
		runtime.Logger.Error("chown %s file fail, error:%s", filePath, err)
		return fmt.Errorf("chown %s file fail, error:%s", filePath, err)
	}
	runtime.Logger.Info("execute chown command for %s file successfully", filePath)
	return nil
}

// CreateConfKeyDbTypeAndChown 创建配置文件，key文件，dbType文件并授权
func CreateConfKeyDbTypeAndChown(runtime *jobruntime.JobGenericRuntime, authConfFilePath string,
	authConfFileContent []byte, user string, group string, noAuthConfFilePath string, noAuthConfFileContent []byte,
	keyFilePath string, keyFileContent string, dbTypeFilePath string, instanceType string,
	defaultPerm os.FileMode) error {
	// 创建Auth配置文件
	if err := CreateFileAndChown(runtime, authConfFilePath, authConfFileContent, user, group,
		defaultPerm); err != nil {
		return err
	}
	// 创建NoAuth配置文件
	if err := CreateFileAndChown(runtime, noAuthConfFilePath, noAuthConfFileContent, user,
		group, defaultPerm); err != nil {
		return err
	}
	// 创建key文件
	key := GetMd5(keyFileContent)
	if err := CreateFileAndChown(runtime, keyFilePath, []byte(key), user, group, 0600); err != nil {
		return err
	}
	// 创建dbType文件
	if err := CreateFileAndChown(runtime, dbTypeFilePath, []byte(instanceType), user, group, defaultPerm); err != nil {
		return err
	}

	return nil
}

// StartMongoProcess 启动进程
func StartMongoProcess(binDir string, port int, user string, auth bool) error {
	// 根据实例类型选择 mongod/mongos 启动，避免把 mongos 配置交给 mongod 解析。
	confName := "noauth.conf"
	if auth {
		confName = "mongo.conf"
	}
	// GetMongoDataDir returns base data root (/data1 or /data), and this function
	// consistently appends mongodata/<port>/... to avoid path-construction drift.
	dataDir := consts.GetMongoDataDir()
	confPath := filepath.Join(dataDir, "mongodata", strconv.Itoa(port), confName)
	binName := "mongod"
	dbTypePath := filepath.Join(dataDir, "mongodata", strconv.Itoa(port), "dbtype")
	if content, err := os.ReadFile(dbTypePath); err == nil {
		dbType := strings.TrimSpace(string(content))
		if dbType == "mongos" {
			binName = "mongos"
		}
	}
	mongoBin := filepath.Join(binDir, "mongodb", "bin", binName)
	cmd := fmt.Sprintf(
		"su %s -c '. /etc/profile >/dev/null 2>&1; if command -v numactl >/dev/null 2>&1; then numactl --interleave=all %s -f %s; else %s -f %s; fi'",
		user, mongoBin, confPath, mongoBin, confPath,
	)
	if _, err := mycmd.New("bash", "-c", cmd).Run3(300*time.Second, nil, nil); err != nil {
		return err
	}
	return nil
}

// ShutdownMongoProcess 关闭进程.
// 统一使用SIGTERM(15)做graceful shutdown；超时后仅在force=true时升级SIGKILL(9)。
// log 使用原子任务的 runtime.Logger（可为 nil，此时不写诊断日志）。
func ShutdownMongoProcess(log *logger.Logger, port int, timeout time.Duration, force bool) error {
	var info, warn, errLog func(string, ...interface{})
	if log != nil {
		info = log.Info
		warn = log.Warn
		errLog = log.Error
	} else {
		info = func(string, ...interface{}) {}
		warn = func(string, ...interface{}) {}
		errLog = func(string, ...interface{}) {}
	}

	if timeout <= 0 {
		timeout = 30 * time.Second
	}

	listenPID0, err := getPidByPort(port)
	if err != nil {
		errLog("ShutdownMongoProcess: port=%d initial getPidByPort failed: %v", port, err)
		return errors.Wrapf(err, "check TCP LISTEN on port %d before shutdown", port)
	}
	if listenPID0 == 0 {
		info("ShutdownMongoProcess: port=%d no TCP LISTEN, nothing to stop", port)
		return nil
	}

	pid, procName, err := GetMongoPidAndNameByPort(port)
	if err != nil {
		errLog(
			"ShutdownMongoProcess: port=%d resolve mongo process failed (listenPid=%d): %v",
			port, listenPID0, err)
		return err
	}
	if pid == 0 {
		info("ShutdownMongoProcess: port=%d listener released before SIGTERM (race), nothing to stop", port)
		return nil
	}

	info(
		"ShutdownMongoProcess: port=%d listenPid=%d mongoPid=%d proc=%q gracefulTimeout=%s force=%v",
		port, listenPID0, pid, procName, timeout, force)

	// kill -15 pid, graceful shutdown
	if err := syscall.Kill(pid, syscall.SIGTERM); err != nil {
		if stderrors.Is(err, syscall.ESRCH) {
			warn(
				"ShutdownMongoProcess: port=%d kill -TERM pid=%d already gone (ESRCH), wait for port release",
				port, pid)
		} else {
			errLog("ShutdownMongoProcess: port=%d kill -TERM pid=%d failed: %v", port, pid, err)
			return errors.Wrapf(err, "kill -15 pid %d for port %d", pid, port)
		}
	} else {
		info("ShutdownMongoProcess: port=%d sent SIGTERM to pid=%d (%s)", port, pid, procName)
	}

	waitErr := waitPortRelease(port, timeout)
	if waitErr == nil {
		info("ShutdownMongoProcess: port=%d released after graceful shutdown", port)
		return nil
	}
	warn("ShutdownMongoProcess: port=%d graceful wait failed: %v", port, waitErr)

	if !force {
		curListen, errCur := getPidByPort(port)
		if errCur != nil {
			errLog(
				"ShutdownMongoProcess: port=%d non-force exit, getPidByPort after timeout failed: %v",
				port, errCur)
		} else {
			errLog(
				"ShutdownMongoProcess: port=%d non-force exit after %s, still TCP LISTEN pid=%d",
				port, timeout, curListen)
		}
		return fmt.Errorf("graceful shutdown timeout for port %d after %s", port, timeout)
	}

	// Listener may exit between waitPortRelease timing out and SIGKILL; skip kill if nothing listens.
	listenPID, err := getPidByPort(port)
	if err != nil {
		errLog("ShutdownMongoProcess: port=%d getPidByPort before SIGKILL failed: %v", port, err)
		return errors.Wrapf(err, "getPidByPort %d before kill -9", port)
	}
	if listenPID == 0 {
		info("ShutdownMongoProcess: port=%d no listener before SIGKILL (race), done", port)
		return nil
	}

	// Re-resolve the listener: PID captured at SIGTERM may already have exited while the port still
	// looks busy (slow shutdown / proc timing); SIGKILL on a stale PID returns ESRCH / "no such process".
	killPid, killProcName, err := GetMongoPidAndNameByPort(port)
	if err != nil {
		warn(
			"ShutdownMongoProcess: port=%d re-resolve mongo pid before SIGKILL failed (listenPid=%d): %v",
			port, listenPID, err)
		listenPIDVerify, errV := getPidByPort(port)
		if errV != nil {
			errLog("ShutdownMongoProcess: port=%d verify getPidByPort failed: %v", port, errV)
			return errors.Wrapf(errV, "getPidByPort %d verifying after GetMongoPidAndNameByPort fail", port)
		}
		if listenPIDVerify == 0 {
			info("ShutdownMongoProcess: port=%d listener cleared during re-resolve, done", port)
			return nil
		}
		errLog(
			"ShutdownMongoProcess: port=%d still listenPid=%d after re-resolve error, returning error",
			port, listenPIDVerify)
		return err
	}
	if killPid == 0 {
		info("ShutdownMongoProcess: port=%d no mongo listener before SIGKILL (race), done", port)
		return nil
	}

	info(
		"ShutdownMongoProcess: port=%d sending SIGKILL to pid=%d (%s) (listenPid was %d)",
		port, killPid, killProcName, listenPID)

	if err := syscall.Kill(killPid, syscall.SIGKILL); err != nil {
		if isErrNoSuchProcess(err) {
			warn(
				"ShutdownMongoProcess: port=%d kill -9 pid=%d (%s): %v (process gone, re-check port)",
				port, killPid, killProcName, err)
			listenPID2, err2 := getPidByPort(port)
			if err2 != nil {
				errLog("ShutdownMongoProcess: port=%d getPidByPort after kill -9 ESRCH failed: %v",
					port, err2)
				return errors.Wrapf(err2, "getPidByPort %d after kill -9 noSuchProcess", port)
			}
			if listenPID2 == 0 {
				info("ShutdownMongoProcess: port=%d cleared after stale SIGKILL", port)
				return nil
			}
			errLog(
				"ShutdownMongoProcess: port=%d kill -9 target exited but port still held by pid=%d",
				port, listenPID2)
			return fmt.Errorf(
				"kill -9 pid %d (%s) for port %d: process already exited but listener pid %d still on port",
				killPid, killProcName, port, listenPID2)
		}
		errLog(
			"ShutdownMongoProcess: port=%d kill -9 pid=%d (%s) failed: %v",
			port, killPid, killProcName, err)
		return errors.Wrapf(err, "kill -9 pid %d (%s) for port %d", killPid, killProcName, port)
	}
	info("ShutdownMongoProcess: port=%d sent SIGKILL to pid=%d (%s)", port, killPid, killProcName)

	if waitKillErr := waitPortRelease(port, 10*time.Second); waitKillErr != nil {
		lastPid, errLast := getPidByPort(port)
		if errLast != nil {
			errLog(
				"ShutdownMongoProcess: port=%d still busy after SIGKILL, final getPidByPort failed: %v",
				port, errLast)
		} else {
			errLog(
				"ShutdownMongoProcess: port=%d still busy after SIGKILL (wait err=%v), listenPid=%d",
				port, waitKillErr, lastPid)
		}
		return fmt.Errorf("port %d still has TCP LISTEN after graceful timeout (%s) and kill -9: %w", port, timeout, waitKillErr)
	}
	info("ShutdownMongoProcess: port=%d released after SIGKILL", port)
	return nil
}

// GetMongoPidAndNameByPort returns pid and /proc comm name for mongod/mongos TCP LISTEN on port
// (any local bind: 127.0.0.1, eth*, ::1, from /proc/net/tcp + tcp6 via portHasTCPListenIPv4 / getPidByPort).
// Returns (0, "", nil) when no listener on port; error if listener exists but pid cannot be resolved or process is not mongod/mongos.
func GetMongoPidAndNameByPort(port int) (int, string, error) {
	busy, err := portHasTCPListenIPv4(port)
	if err != nil {
		return 0, "", errors.Wrapf(err, "check TCP LISTEN on port %d", port)
	}
	if !busy {
		return 0, "", nil
	}
	pid, err := getPidByPort(port)
	if err != nil {
		return 0, "", errors.Wrapf(err, "get pid by port %d", port)
	}
	if pid == 0 {
		return 0, "", fmt.Errorf("port %d has TCP LISTEN but listening pid could not be resolved", port)
	}

	processName, err := os.ReadFile(fmt.Sprintf("/proc/%d/comm", pid))
	if err != nil {
		return 0, "", errors.Wrapf(err, "read process name from /proc/%d/comm", pid)
	}
	processNameStr := strings.TrimSpace(string(processName))
	if !strings.Contains(processNameStr, "mongod") && !strings.Contains(processNameStr, "mongos") {
		return 0, "", fmt.Errorf("port %d occupied by non-mongo process %q (pid=%d)", port, processNameStr, pid)
	}
	return pid, processNameStr, nil
}

// waitPortRelease waits until no TCP LISTEN on port (both tcp/tcp6).
// Uses ListenSocketInodes (portHasTCPListenIPv4) so we still see listeners when inode→pid resolution
// returns 0 (e.g. cannot read other users' /proc/*/fd); do not treat that as "port free".
func waitPortRelease(port int, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for {
		busy, err := portHasTCPListenIPv4(port)
		if err != nil {
			return errors.Wrapf(err, "check TCP LISTEN on port %d after shutdown", port)
		}
		if !busy {
			return nil
		}
		if time.Now().After(deadline) {
			listenPID, _ := getPidByPort(port)
			return fmt.Errorf("port %d still has TCP LISTEN (pid %d) after %s", port, listenPID, timeout)
		}
		time.Sleep(mongoShutdownPollInterval)
	}
}

// AddPathToProfile 把可执行文件路径写入/etc/profile
func AddPathToProfile(runtime *jobruntime.JobGenericRuntime, binDir string) error {
	runtime.Logger.Info("start to add binary path in /etc/profile")
	etcProfilePath := "/etc/profile"
	addEtcProfile := fmt.Sprintf(`
if ! grep -i %s: %s; 
then 
echo "export PATH=%s:\$PATH" >> %s 
fi`, filepath.Join(binDir, "mongodb", "bin"), etcProfilePath, filepath.Join(binDir, "mongodb", "bin"), etcProfilePath)
	runtime.Logger.Info("%s", addEtcProfile)
	if _, err := util.RunBashCmd(addEtcProfile, "", nil, 60*time.Second); err != nil {
		runtime.Logger.Error("binary path add in /etc/profile, error:%s", err)
		return fmt.Errorf("binary path add in /etc/profile, error:%s", err)
	}
	runtime.Logger.Info("add binary path in /etc/profile successfully")
	return nil
}

// AuthGetPrimaryInfo 获取primary节点信息
func AuthGetPrimaryInfo(mongoBin string, username string, password string, ip string, port int) (string,
	error) {
	// 超时时间
	timeout := time.After(20 * time.Second)
	for {
		select {
		case <-timeout:
			return "", fmt.Errorf("get primary info timeout")
		default:
			cmd := fmt.Sprintf(
				"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"rs.isMaster().primary\"",
				mongoBin, username, password, ip, port)
			result, err := util.RunBashCmd(
				cmd,
				"", nil,
				60*time.Second)
			if err != nil {
				return "", err
			}
			if strings.Replace(result, "\n", "", -1) == "" {
				time.Sleep(1 * time.Second)
				continue
			}
			primaryInfo := strings.Replace(result, "\n", "", -1)
			return primaryInfo, nil
		}
	}
}

// NoAuthGetPrimaryInfo 获取primary节点信息
func NoAuthGetPrimaryInfo(mongoBin string, ip string, port int) (string, error) {
	// 超时时间
	timeout := time.After(60 * time.Second)
	for {
		select {
		case <-timeout:
			return "", fmt.Errorf("get primary info timeout")
		default:
			cmd := fmt.Sprintf(
				"%s --host %s --port %d --quiet --eval \"rs.isMaster().primary\"",
				mongoBin, ip, port)
			result, err := util.RunBashCmd(
				cmd,
				"", nil,
				60*time.Second)
			if err != nil {
				return "", err
			}
			if strings.Replace(result, "\n", "", -1) == "" {
				time.Sleep(1 * time.Second)
				continue
			}
			primaryInfo := strings.Replace(result, "\n", "", -1)
			return primaryInfo, nil
		}

	}
}

// InitiateReplicasetGetPrimaryInfo 复制集初始化时判断
func InitiateReplicasetGetPrimaryInfo(mongoBin string, ip string, port int) (string, error) {
	cmd := fmt.Sprintf(
		"%s --host %s --port %d --quiet --eval \"rs.isMaster().primary\"",
		mongoBin, ip, port)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return "", err
	}
	primaryInfo := strings.Replace(result, "\n", "", -1)
	return primaryInfo, nil
}

// RemoveFile 删除文件
func RemoveFile(filePath string) error {
	cmd := fmt.Sprintf("rm -rf %s", filePath)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second); err != nil {
		return err
	}
	return nil
}

// CreateFile 创建文件
func CreateFile(path string) error {
	installLockFile, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}
	defer installLockFile.Close()
	return nil
}

// AuthCheckUser 检查user是否存在
func AuthCheckUser(mongoBin string, username string, password string, ip string, port int, authDb string,
	checkUsername string) (bool, error) {
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"db.getMongo().getDB('%s').getUser('%s')\"",
		mongoBin, username, password, ip, port, authDb, checkUsername)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return false, fmt.Errorf("get user info fail, error:%s", err)
	}
	if strings.Contains(result, checkUsername) == true {
		return true, nil
	}

	return false, nil
}

// GetNodeInfo24 2.4获取mongod节点信息
func GetNodeInfo24(mongoBin string, ip string, port int, username string, password string) (
	bson.A, bson.A, error) {
	var statusSlice bson.A
	var confSlice bson.A
	evalScript := "printjson(rs.status().members)"
	cmdStatus := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\"",
		mongoBin, username, password, ip, port, evalScript)
	evalScript = "printjson(rs.conf().members)"
	cmdConf := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\"",
		mongoBin, username, password, ip, port, evalScript)

	// 获取状态
	result1, err := util.RunBashCmd(
		cmdStatus,
		"", nil,
		60*time.Second)
	if err != nil {
		return statusSlice, confSlice, fmt.Errorf("get members status info fail, error:%s", err)
	}
	for _, replaceStr := range []string{" ", "\n", "NumberLong(", "Timestamp(", "ISODate(", ",1)", ",3)", ",2)", ",6)",
		",0)", ")"} {
		result1 = strings.Replace(result1, replaceStr, "", -1)
	}
	// 获取配置
	result2, err := util.RunBashCmd(
		cmdConf,
		"", nil,
		60*time.Second)
	if err != nil {
		return statusSlice, confSlice, fmt.Errorf("get members conf info fail, error:%s", err)
	}
	for _, replaceStr := range []string{" ", "\n", "NumberLong(", "Timestamp(", "ISODate(", ",1)", ")"} {
		result2 = strings.Replace(result2, replaceStr, "", -1)
	}

	if err = json.Unmarshal([]byte(result1), &statusSlice); err != nil {
		return statusSlice, confSlice, fmt.Errorf("get members status info json.Unmarshal fail, error:%s", err)
	}
	if err = json.Unmarshal([]byte(result2), &confSlice); err != nil {
		return statusSlice, confSlice, fmt.Errorf("get members conf info json.Unmarshal fail, error:%s", err)
	}
	return statusSlice, confSlice, nil
}

// GetNodeInfo26 2.6及以上获取mongod节点信息   _id int state int hidden bool  priority int
func GetNodeInfo26(ip string, port int, username string, password string) (
	bson.A, bson.A, error) {
	var statusSlice bson.A
	var confSlice bson.A
	// 设置mongodb连接参数
	clientOptions := options.Client().ApplyURI(fmt.Sprintf("mongodb://%s:%s@%s:%d",
		username, url.QueryEscape(password), ip, port))
	// 连接mongodb
	client, err := mongo.Connect(context.TODO(), clientOptions)
	if err != nil {
		return nil, nil, fmt.Errorf("create mongodb connnect fail, error:%s", err)
	}
	// 关闭连接
	defer client.Disconnect(context.TODO())
	// 切换到admin数据库
	db := client.Database("admin")
	// 获取数据
	for _, command := range []string{"replSetGetStatus", "replSetGetConfig"} {
		var result bson.M
		err = db.RunCommand(context.TODO(), bson.D{{Key: command, Value: 1}}).Decode(&result)
		if err != nil {
			return statusSlice, confSlice, fmt.Errorf("get %s info fail, error:%s", command, err)
		}
		if command == "replSetGetStatus" {
			statusSlice = result["members"].(bson.A)
		} else {
			confSlice = result["config"].(bson.M)["members"].(bson.A)
		}
	}
	return statusSlice, confSlice, nil
}

// GetCurrentNodeInfo 获取MongoDB当前节点信息
func GetCurrentNodeInfo(mainDbVersion float64, statusSlice bson.A, confSlice bson.A, source string) (bool, int, int,
	bool, int) {
	var id int
	var state int
	var hidden bool
	var priority int
	flag := false
	for _, key := range statusSlice {
		var statusInfo map[string]interface{}
		var nodeState int
		if mainDbVersion < 2.6 {
			statusInfo = key.(map[string]interface{})
			nodeState, _ = strconv.Atoi(fmt.Sprintf("%1.0f", statusInfo["state"]))
		} else {
			infoMap := map[string]interface{}(key.(bson.M))
			statusInfo = infoMap
			nodeState = int(statusInfo["state"].(int32))
		}
		if statusInfo["name"].(string) == source {
			id, _ = strconv.Atoi(fmt.Sprintf("%1.0f", statusInfo["_id"]))
			state = nodeState
			flag = true
			break
		}
	}
	for _, key := range confSlice {
		var confInfo map[string]interface{}
		if mainDbVersion < 2.6 {
			confInfo = key.(map[string]interface{})
		} else {
			infoMap := map[string]interface{}(key.(bson.M))
			confInfo = infoMap
		}
		if confInfo["host"].(string) == source {
			value, ok := confInfo["hidden"]
			if ok {
				hidden = value.(bool)
			} else {
				hidden = false
			}
			value, ok = confInfo["priority"]
			if ok {
				priority, _ = strconv.Atoi(fmt.Sprintf("%1.0f", value))
			} else {
				priority = 1
			}
			break
		}
	}
	return flag, id, state, hidden, priority
}

// GetNodeInfo 获取mongod节点信息   _id int state int hidden bool  priority int
func GetNodeInfo(mongoBin string, ip string, port int, username string, password string,
	sourceIP string, sourcePort int) (bool, int, int, bool, int, []map[string]string, error) {
	var statusSlice bson.A
	var confSlice bson.A
	var memberInfo []map[string]string
	source := strings.Join([]string{sourceIP, strconv.Itoa(sourcePort)}, ":")
	// 检查db版本
	binDir, _ := filepath.Abs(filepath.Join(mongoBin, "../../.."))
	dbVersion, err := CheckMongoVersion(binDir, "mongod")
	if err != nil {
		return false, 0, 0, false, 0, memberInfo, fmt.Errorf("get db version fail, error:%s", err)
	}
	mainDbVersion, _ := strconv.ParseFloat(strings.Join(strings.Split(dbVersion, ".")[0:2], "."), 64)
	if mainDbVersion < 2.6 {
		statusSlice, confSlice, err = GetNodeInfo24(mongoBin, ip, port, username, password)
		if err != nil {
			return false, 0, 0, false, 0, memberInfo, fmt.Errorf("get db info fail, error:%s", err)
		}
	} else {
		statusSlice, confSlice, err = GetNodeInfo26(ip, port, username, password)
		if err != nil {
			return false, 0, 0, false, 0, memberInfo, fmt.Errorf("get db info fail, error:%s", err)
		}
	}
	// 获取副本集成员信息
	for _, v := range statusSlice {
		member := make(map[string]string)
		var statusInfo map[string]interface{}
		if mainDbVersion < 2.6 {
			statusInfo = v.(map[string]interface{})
			member["state"] = fmt.Sprintf("%1.0f", statusInfo["state"])
		} else {
			infoMap := map[string]interface{}(v.(bson.M))
			statusInfo = infoMap
			member["state"] = fmt.Sprintf("%d", statusInfo["state"])
		}
		member["name"] = statusInfo["name"].(string)

		for _, k := range confSlice {
			var confInfo map[string]interface{}
			if mainDbVersion < 2.6 {
				confInfo = k.(map[string]interface{})
			} else {
				infoMap := map[string]interface{}(k.(bson.M))
				confInfo = infoMap
			}
			if confInfo["host"].(string) == member["name"] {
				value, ok := confInfo["hidden"]
				if ok {
					member["hidden"] = strconv.FormatBool(value.(bool))
				} else {
					member["hidden"] = strconv.FormatBool(false)
				}
				break
			}
		}
		memberInfo = append(memberInfo, member)
	}
	// 获取当前节点信息
	flag, id, state, hidden, priority := GetCurrentNodeInfo(mainDbVersion, statusSlice, confSlice, source)

	return flag, id, state, hidden, priority, memberInfo, nil
}

// AuthRsStepDown 主备切换
func AuthRsStepDown(mongoBin string, ip string, port int, username string, password string) (bool, error) {
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"rs.stepDown()\" >> /dev/null",
		mongoBin, username, password, ip, port)
	_, _ = util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	time.Sleep(time.Second * 3)
	primaryInfo, err := AuthGetPrimaryInfo(mongoBin, username, password, ip, port)
	if err != nil {
		return false, err
	}
	if primaryInfo == strings.Join([]string{ip, strconv.Itoa(port)}, ":") {
		return false, nil
	}

	return true, nil
}

// NoAuthRsStepDown 主备切换
func NoAuthRsStepDown(mongoBin string, ip string, port int) (bool, error) {
	cmd := fmt.Sprintf(
		"%s  --host %s --port %d --authenticationDatabase=admin --quiet --eval \"rs.stepDown()\"",
		mongoBin, ip, port)
	_, _ = util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	time.Sleep(time.Second * 3)
	primaryInfo, err := NoAuthGetPrimaryInfo(mongoBin, ip, port)
	if err != nil {
		return false, err
	}
	if primaryInfo == strings.Join([]string{ip, strconv.Itoa(port)}, ":") {
		return false, nil
	}
	return true, nil
}

// CheckBalancer 检查balancer的值
func CheckBalancer(mongoBin string, ip string, port int, username string, password string) (string,
	error) {
	cmd := fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"sh.getBalancerState()\"",
		mongoBin, username, password, ip, port)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return "", err
	}
	result = strings.Replace(result, "\n", "", -1)
	return result, nil
}

// CheckBalancerRunning 检查balancer是否正在运行
func CheckBalancerRunning(mongoBin string, ip string, port int, username string, password string) (string,
	error) {
	cmd := fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"sh.isBalancerRunning()\"",
		mongoBin, username, password, ip, port)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return "", err
	}
	result = strings.Replace(result, "\n", "", -1)
	return result, nil
}

// GetShardChunkNum 获取每个分片的chunk数量
func GetShardChunkNum(mongoBin string, ip string, port int, username string, password string) (string,
	error) {
	cmd := fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval '%s'",
		mongoBin, username, password, ip, port,
		"db.getSiblingDB(\"config\").chunks.aggregate([{ $group: { _id: \"$shard\", count: { $sum: 1 } } }]).forEach(printjson)")
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return "", err
	}
	return result, nil
}

// GetProfilingLevel 获取profile级别
func GetProfilingLevel(mongoBin string, ip string, port int, username string, password string,
	dbName string) (int, error) {
	cmd := fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"db.getMongo().getDB('%s').getProfilingLevel()\"",
		mongoBin, username, password, ip, port, dbName)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return -1, err
	}
	intResult, _ := strconv.Atoi(result)
	return intResult, nil
}

// SetProfilingLevel 设置profile级别
func SetProfilingLevel(mongoBin string, ip string, port int, username string, password string,
	dbName string, level int) error {
	cmd := fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"db.getMongo().getDB('%s').setProfilingLevel(%d)\"",
		mongoBin, username, password, ip, port, dbName, level)
	_, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return err
	}
	return nil
}

// GetShardInfo 获取shard信息
func GetShardInfo(mongoBin string, ip string, port int, username string, password string) (string, error) {
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --quiet --authenticationDatabase=admin --eval \"db.getMongo().getDB('config').shards.find().forEach(printjson)\" admin",
		mongoBin, username, password, ip, port)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return "", err
	}
	result = strings.Replace(result, "\n", "", -1)
	return result, nil
}
