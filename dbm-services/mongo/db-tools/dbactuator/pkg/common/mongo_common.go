package common

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"
)

// UnTarAndCreateSoftLinkAndChown 解压目录，创建软链接并修改属主
func UnTarAndCreateSoftLinkAndChown(runtime *jobruntime.JobGenericRuntime, binDir string, installPackagePath string,
	unTarPath string,
	installPath string, user string, group string) error {
	// 解压安装包
	if !util.FileExists(unTarPath) {
		// 解压到/usr/local目录下
		runtime.Logger.Info("start to unTar install package")
		tarCmd := fmt.Sprintf("tar -zxf %s -C %s", installPackagePath, binDir)
		if _, err := util.RunBashCmd(tarCmd, "", nil, 10*time.Second); err != nil {
			runtime.Logger.Error(fmt.Sprintf("untar install file  fail, error:%s", err))
			return fmt.Errorf("untar install file  fail, error:%s", err)
		}
		runtime.Logger.Info("unTar install package successfully")
		// 修改属主
		runtime.Logger.Info("start to execute chown command for unTar directory")
		if _, err := util.RunBashCmd(
			fmt.Sprintf("chown -R %s.%s %s", user, group, unTarPath),
			"", nil,
			10*time.Second); err != nil {
			runtime.Logger.Error(fmt.Sprintf("chown untar directory fail, error:%s", err))
			return fmt.Errorf("chown untar directory fail, error:%s", err)
		}
		runtime.Logger.Info("execute chown command for unTar directory successfully")
	}

	// 创建软链接
	if !util.FileExists(installPath) {
		// 创建软链接
		runtime.Logger.Info("start to create soft link")
		softLink := fmt.Sprintf("ln -s %s %s", unTarPath, installPath)
		if _, err := util.RunBashCmd(softLink, "", nil, 10*time.Second); err != nil {
			runtime.Logger.Error(
				fmt.Sprintf("install directory create softLink fail, error:%s", err))
			return fmt.Errorf("install directory create softLink fail, error:%s", err)
		}
		runtime.Logger.Info("create soft link successfully")

		// 修改属主
		runtime.Logger.Info("start to execute chown command for softLink directory")
		if _, err := util.RunBashCmd(
			fmt.Sprintf("chown -R %s.%s %s", user, group, installPath),
			"", nil,
			10*time.Second); err != nil {
			runtime.Logger.Error(fmt.Sprintf("chown softlink directory fail, error:%s", err))
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
	getVersion, err := util.RunBashCmd(cmd, "", nil, 10*time.Second)
	getVersion = strings.Replace(getVersion, "\n", "", -1)
	if err != nil {
		return "", err
	}
	return getVersion, nil
}

// CheckMongoService 检查mongo服务是否存在
func CheckMongoService(port int) (bool, string, error) {
	cmd := fmt.Sprintf("netstat -ntpl |grep %d | awk '{print $7}' |head -1", port)
	result, err := util.RunBashCmd(cmd, "", nil, 10*time.Second)
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

// CreateConfFileAndKeyFileAndDbTypeFileAndChown 创建配置文件，key文件，dbType文件并授权
func CreateConfFileAndKeyFileAndDbTypeFileAndChown(runtime *jobruntime.JobGenericRuntime, authConfFilePath string,
	authConfFileContent []byte, user string, group string, noAuthConfFilePath string, noAuthConfFileContent []byte,
	keyFilePath string, keyFileContent string, dbTypeFilePath string, instanceType string,
	defaultPerm os.FileMode) error {
	// 创建Auth配置文件
	runtime.Logger.Info("start to create auth config file")
	authConfFile, err := os.OpenFile(authConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, defaultPerm)
	defer authConfFile.Close()
	if err != nil {
		runtime.Logger.Error(fmt.Sprintf("create auth config file fail, error:%s", err))
		return fmt.Errorf("create auth config file fail, error:%s", err)
	}
	if _, err = authConfFile.WriteString(string(authConfFileContent)); err != nil {
		runtime.Logger.Error(fmt.Sprintf("auth config file write content fail, error:%s", err))
		return fmt.Errorf("auth config file write content  fail, error:%s", err)
	}
	runtime.Logger.Info("create auth config file successfully")

	// 修改配置文件属主
	runtime.Logger.Info("start to execute chown command for auth config file")
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", user, group, authConfFilePath),
		"", nil,
		10*time.Second); err != nil {
		runtime.Logger.Error(fmt.Sprintf("chown auth config file fail, error:%s", err))
		return fmt.Errorf("chown auth config file fail, error:%s", err)
	}
	runtime.Logger.Info("start to execute chown command for auth config file successfully")

	// 创建NoAuth配置文件
	runtime.Logger.Info("start to create no auth config file")
	noAuthConfFile, err := os.OpenFile(noAuthConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, defaultPerm)
	defer noAuthConfFile.Close()
	if err != nil {
		runtime.Logger.Error(fmt.Sprintf("create no auth config file fail, error:%s", err))
		return fmt.Errorf("create no auth config file fail, error:%s", err)
	}
	if _, err = noAuthConfFile.WriteString(string(noAuthConfFileContent)); err != nil {
		runtime.Logger.Error(fmt.Sprintf("auth no config file write content fail, error:%s", err))
		return fmt.Errorf("auth no config file write content  fail, error:%s", err)
	}
	runtime.Logger.Info("create no auth config file successfully")

	// 修改配置文件属主
	runtime.Logger.Info("start to execute chown command for no auth config file")
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", user, group, noAuthConfFilePath),
		"", nil,
		10*time.Second); err != nil {
		runtime.Logger.Error(fmt.Sprintf("chown no auth config file fail, error:%s", err))
		return fmt.Errorf("chown no auth config file fail, error:%s", err)
	}
	runtime.Logger.Info("execute chown command for no auth config file successfully")

	// 创建key文件
	runtime.Logger.Info("start to create key file")
	keyFile, err := os.OpenFile(keyFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0600)
	defer keyFile.Close()
	if err != nil {
		runtime.Logger.Error(fmt.Sprintf("create key file fail, error:%s", err))
		return fmt.Errorf("create key file fail, error:%s", err)
	}
	key := GetMd5(keyFileContent)
	if _, err = keyFile.WriteString(key); err != nil {
		runtime.Logger.Error(fmt.Sprintf("key file write content fail, error:%s", err))
		return fmt.Errorf("key file write content fail, error:%s", err)
	}
	runtime.Logger.Info("create key file successfully")

	// 修改key文件属主
	runtime.Logger.Info("start to execute chown command for key file")
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", user, group, keyFilePath),
		"", nil,
		10*time.Second); err != nil {
		runtime.Logger.Error(fmt.Sprintf("chown key file fail, error:%s", err))
		return fmt.Errorf("chown key file fail, error:%s", err)
	}
	runtime.Logger.Info("execute chown command for key file successfully")

	// 创建dbType文件
	runtime.Logger.Info("start to create dbType file")
	dbTypeFile, err := os.OpenFile(dbTypeFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, defaultPerm)
	defer dbTypeFile.Close()
	if err != nil {
		runtime.Logger.Error(fmt.Sprintf("create dbType file fail, error:%s", err))
		return fmt.Errorf("create dbType file fail, error:%s", err)
	}
	if _, err = dbTypeFile.WriteString(instanceType); err != nil {
		runtime.Logger.Error(fmt.Sprintf("dbType file write content fail, error:%s", err))
		return fmt.Errorf("dbType file write content fail, error:%s", err)
	}
	runtime.Logger.Info("create dbType file successfully")

	// 修改dbType文件属主
	runtime.Logger.Info("start to execute chown command for dbType file")
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", user, group, dbTypeFilePath),
		"", nil,
		10*time.Second); err != nil {
		runtime.Logger.Error(fmt.Sprintf("chown dbType file fail, error:%s", err))
		return fmt.Errorf("chown dbType file fail, error:%s", err)
	}
	runtime.Logger.Info("execute chown command for dbType file successfully")

	return nil

}

// StartMongoProcess 启动进程
func StartMongoProcess(binDir string, port int, user string, auth bool) error {
	// 启动服务
	var cmd string
	cmd = fmt.Sprintf("su %s -c \"%s %d %s\"", user,
		filepath.Join(binDir, "mongodb", "bin", "start_mongo.sh"),
		port, "noauth")
	if auth == true {
		cmd = fmt.Sprintf("su  %s -c \"%s %d\"", user,
			filepath.Join(binDir, "mongodb", "bin", "start_mongo.sh"),
			port)
	}
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		return err
	}
	return nil
}

// ShutdownMongoProcess 关闭进程
func ShutdownMongoProcess(user string, instanceType string, binDir string, dbpathDir string, port int) error {
	var cmd string
	cmd = fmt.Sprintf("su %s -c \"%s --shutdown --dbpath %s\"",
		user, filepath.Join(binDir, "mongodb", "bin", "mongod"), dbpathDir)
	if instanceType == "mongos" {
		cmd = fmt.Sprintf("ps -ef|grep mongos |grep -v grep|grep %d|awk '{print $2}' | xargs kill -2", port)
	}
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		return err
	}
	return nil
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
	runtime.Logger.Info(addEtcProfile)
	if _, err := util.RunBashCmd(addEtcProfile, "", nil, 10*time.Second); err != nil {
		runtime.Logger.Error(fmt.Sprintf("binary path add in /etc/profile, error:%s", err))
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
				10*time.Second)
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
	timeout := time.After(20 * time.Second)
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
				10*time.Second)
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
		10*time.Second)
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
		10*time.Second); err != nil {
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
		10*time.Second)
	if err != nil {
		return false, fmt.Errorf("get user info fail, error:%s", err)
	}
	if strings.Contains(result, checkUsername) == true {
		return true, nil
	}

	return false, nil
}

// GetNodeInfo 获取mongod节点信息   _id int state int hidden bool  priority int
func GetNodeInfo(mongoBin string, ip string, port int, username string, password string,
	sourceIP string, sourcePort int) (bool, int, int, bool, int, []map[string]string, error) {
	source := strings.Join([]string{sourceIP, strconv.Itoa(sourcePort)}, ":")
	cmdStatus := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"rs.status().members\"",
		mongoBin, username, password, ip, port)
	cmdConf := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"rs.conf().members\"",
		mongoBin, username, password, ip, port)

	// 获取状态
	result1, err := util.RunBashCmd(
		cmdStatus,
		"", nil,
		10*time.Second)
	if err != nil {
		return false, 0, 0, false, 0, nil, fmt.Errorf("get members status info fail, error:%s", err)
	}
	result1 = strings.Replace(result1, " ", "", -1)
	result1 = strings.Replace(result1, "\n", "", -1)
	result1 = strings.Replace(result1, "NumberLong(", "", -1)
	result1 = strings.Replace(result1, "Timestamp(", "", -1)
	result1 = strings.Replace(result1, "ISODate(", "", -1)
	result1 = strings.Replace(result1, ",1)", "", -1)
	result1 = strings.Replace(result1, ",3)", "", -1)
	result1 = strings.Replace(result1, ",2)", "", -1)
	result1 = strings.Replace(result1, ",6)", "", -1)
	result1 = strings.Replace(result1, ",0)", "", -1)
	result1 = strings.Replace(result1, ")", "", -1)

	// 获取配置
	result2, err := util.RunBashCmd(
		cmdConf,
		"", nil,
		10*time.Second)
	if err != nil {
		return false, 0, 0, false, 0, nil, fmt.Errorf("get members conf info fail, error:%s", err)
	}
	result2 = strings.Replace(result2, " ", "", -1)
	result2 = strings.Replace(result2, "\n", "", -1)
	result2 = strings.Replace(result2, "NumberLong(", "", -1)
	result2 = strings.Replace(result2, "Timestamp(", "", -1)
	result2 = strings.Replace(result2, "ISODate(", "", -1)
	result2 = strings.Replace(result2, ",1)", "", -1)
	result2 = strings.Replace(result2, ")", "", -1)

	var statusSlice []map[string]interface{}
	var confSlice []map[string]interface{}
	if err = json.Unmarshal([]byte(result1), &statusSlice); err != nil {
		return false, 0, 0, false, 0, nil, fmt.Errorf("get members status info json.Unmarshal fail, error:%s", err)
	}
	if err = json.Unmarshal([]byte(result2), &confSlice); err != nil {
		return false, 0, 0, false, 0, nil, fmt.Errorf("get members conf info json.Unmarshal fail, error:%s", err)
	}

	// 格式化配置信息
	var memberInfo []map[string]string
	for _, v := range statusSlice {
		member := make(map[string]string)
		member["name"] = v["name"].(string)
		member["state"] = fmt.Sprintf("%1.0f", v["state"])
		for _, k := range confSlice {
			if k["host"].(string) == member["name"] {
				member["hidden"] = strconv.FormatBool(k["hidden"].(bool))
				break
			}
		}
		memberInfo = append(memberInfo, member)
	}

	var id int
	var state int
	var hidden bool
	var priority int
	flag := false
	for _, key := range statusSlice {
		if key["name"].(string) == source {
			id, _ = strconv.Atoi(fmt.Sprintf("%1.0f", key["_id"]))
			state, _ = strconv.Atoi(fmt.Sprintf("%1.0f", key["state"]))
			flag = true
			break
		}
	}
	for _, key := range confSlice {
		if key["host"].(string) == source {
			hidden = key["hidden"].(bool)
			priority, _ = strconv.Atoi(fmt.Sprintf("%1.0f", key["priority"]))
			break
		}
	}
	return flag, id, state, hidden, priority, memberInfo, nil

}

// AuthRsStepDown 主备切换
func AuthRsStepDown(mongoBin string, ip string, port int, username string, password string) (bool, error) {
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"rs.stepDown()\"",
		mongoBin, username, password, ip, port)
	_, _ = util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second)
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
		10*time.Second)
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
		10*time.Second)
	if err != nil {
		return "", err
	}
	result = strings.Replace(result, "\n", "", -1)
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
		10*time.Second)
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
		10*time.Second)
	if err != nil {
		return err
	}
	return nil
}
