package common

import (
	"dbm-services/mongo/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
)

func getConfFileName(port int) string {
	return filepath.Join(consts.ExporterConfDir, fmt.Sprintf("%d.conf", port))
}

// setExporterConfig 写入ExporterConfig文件
// 目录固定:. consts.ExporterConfDir
// 文件名称:. $port.conf
// 文件已经存在, 覆盖.
// 文件写入失败，报错.

// WriteExporterConfigFile 写exporter配置文件
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
