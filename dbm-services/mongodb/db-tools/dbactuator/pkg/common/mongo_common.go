// Package common 公共函数
package common

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
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
		if _, err := util.RunBashCmd(tarCmd, "", nil, 60*time.Second); err != nil {
			runtime.Logger.Error(fmt.Sprintf("untar install file  fail, error:%s", err))
			return fmt.Errorf("untar install file  fail, error:%s", err)
		}
		runtime.Logger.Info("unTar install package successfully")
		// 修改属主
		runtime.Logger.Info("start to execute chown command for unTar directory")
		if _, err := util.RunBashCmd(
			fmt.Sprintf("chown -R %s.%s %s", user, group, unTarPath),
			"", nil,
			60*time.Second); err != nil {
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
		if _, err := util.RunBashCmd(softLink, "", nil, 60*time.Second); err != nil {
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
			60*time.Second); err != nil {
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
	cmd := fmt.Sprintf("netstat -ntpl |grep %d | awk '{print $7}' |head -1", port)
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
	defer file.Close()
	if err != nil {
		runtime.Logger.Error("create %s file fail, error:%s", filePath, err)
		return fmt.Errorf("create %s file fail, error:%s", filePath, err)
	}
	if _, err = file.WriteString(string(fileContent)); err != nil {
		runtime.Logger.Error("%s file write content fail, error:%s", filePath, err)
		return fmt.Errorf("%s file write content  fail, error:%s", filePath, err)
	}
	runtime.Logger.Info("create %s file successfully", filePath)

	// 修改配置文件属主
	runtime.Logger.Info("start to execute chown command for %s file", filePath)
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", user, group, filePath),
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
		60*time.Second); err != nil {
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
		120*time.Second); err != nil {
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
	if _, err := util.RunBashCmd(addEtcProfile, "", nil, 60*time.Second); err != nil {
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

// CreateDBAUserGetPrimaryInfo 创建dba用户获取primary节点信息
func CreateDBAUserGetPrimaryInfo(mongoBin string, port int) (string,
	error) {
	// 超时时间
	timeout := time.After(20 * time.Second)
	for {
		select {
		case <-timeout:
			return "", fmt.Errorf("get primary info timeout")
		default:
			cmd := fmt.Sprintf(
				"%s --host %s --port %d  --quiet --eval \"rs.isMaster().primary\"", mongoBin, "127.0.0.1", port)
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
		err = db.RunCommand(context.TODO(), bson.D{{command, 1}}).Decode(&result)
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

// GetFCV 获取FCV
func GetFCV(mongoBin string, ip string, port int, username string, password string) (string, error) {
	cmd := fmt.Sprintf(
		"%s  -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"db.adminCommand( { getParameter: 1, featureCompatibilityVersion: 1 } )\" admin",
		mongoBin, username, password, ip, port)
	fcvInfo, err := util.RunBashCmd(
		cmd,
		"", nil,
		60*time.Second)
	if err != nil {
		return "", err
	}
	fcvInfo = strings.TrimSpace(fcvInfo)
	fcv := GetFcv{}
	_ = json.Unmarshal([]byte(fcvInfo), &fcv)
	return fcv.FeatureCompatibilityVersion, nil
}
