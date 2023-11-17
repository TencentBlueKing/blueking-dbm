package common

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

func getConfFileName(port int) string {
	return filepath.Join(consts.ExporterConfDir, fmt.Sprintf("%d.conf", port))
}

// setExporterConfig 写入ExporterConfig文件
// 目录固定:. consts.ExporterConfDir
// 文件名称:. $port.conf
// 文件已经存在, 覆盖.
// 文件写入失败，报错.

// WriteExporterConfigFile TODO
func WriteExporterConfigFile(port int, data interface{}) (err error) {
	var fileData []byte
	var confFile string
	err = util.MkDirsIfNotExists([]string{consts.ExporterConfDir})
	if err != nil {
		return err
	}
	confFile = getConfFileName(port)
	fileData, _ = json.Marshal(data)
	err = ioutil.WriteFile(confFile, fileData, 0755)
	if err != nil {
		return err
	}
	util.LocalDirChownMysql(consts.ExporterConfDir)
	return nil
}

// DeleteExporterConfigFile 删除Exporter配置文件.
func DeleteExporterConfigFile(port int) (err error) {
	var confFile string
	confFile = getConfFileName(port)
	return os.Remove(confFile)
}

// CreateLocalExporterConfigFile 创建本地Exporter配置文件.
func CreateLocalExporterConfigFile(ip string, port int, metaRole, password string) (err error) {
	addr := map[string]string{}
	var key, val string
	if password == "" {
		// 从本地配置文件获取密码
		if metaRole == consts.MetaRoleRedisMaster ||
			metaRole == consts.MetaRoleRedisSlave {
			password, err = myredis.GetRedisPasswdFromConfFile(port)
		} else if metaRole == consts.MetaRolePredixy ||
			metaRole == consts.MetaRoleTwemproxy {
			password, err = myredis.GetProxyPasswdFromConfFlie(port, metaRole)
		}
		if err != nil {
			mylog.Logger.Error("get password from local conf file failed,err:%v,ip:%s,port:%d,metaRole:%s",
				err, ip, port, metaRole)
			return err
		}
	}
	if metaRole == consts.MetaRoleRedisMaster ||
		metaRole == consts.MetaRoleRedisSlave {
		key = fmt.Sprintf("redis://%s:%d", ip, port)
		val = password
		addr[key] = val
	} else if metaRole == consts.MetaRolePredixy {
		key = fmt.Sprintf("%s:%d", ip, port)
		val = password
		addr[key] = val
	} else if metaRole == consts.MetaRoleTwemproxy {
		key = fmt.Sprintf("%s:%d", ip, port)
		val = password
		addr[key] = val
		key = fmt.Sprintf("%s:%d:stat", ip, port)
		val = fmt.Sprintf("%s:%d", ip, port+1000)
		addr[key] = val
	}
	err = WriteExporterConfigFile(port, addr)
	if err != nil {
		mylog.Logger.Error("WriteExporterConfigFile %d failed,err:%v", port, err)
	}
	return nil
}
