package rotatebinlog

import (
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/backup"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"

	"github.com/mitchellh/mapstructure"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"gopkg.in/yaml.v2"
)

func (c *MySQLRotateBinlogComp) GenerateRuntimeConfig() (err error) {
	for k, val := range c.Params.Configs.BackupClient {
		if k == "ibs" {
			ibsClient := backup.IBSBackupClient{}
			if reflect.TypeOf(val).Kind() == reflect.Map {
				// backup_client.ibs 返回的是 json map,比如 {"enable": true,"ibs_mode": "hdfs","with_md5": true,"file_tag": "INCREMENT_BACKUP","tool_path": "backup_client"}
				if err := mapstructure.Decode(val, &ibsClient); err != nil {
					return errors.Wrapf(err, "fail to decode backup_client.ibs value:%v", val)
				} else {
					c.Params.Configs.BackupClient[k] = ibsClient
				}
			} else {
				// backup_client.ibs 返回的是 string, 比如：{\"enable\": true,\"ibs_mode\": \"hdfs\",\"with_md5\": true,\"file_tag\": \"INCREMENT_BACKUP\",\"tool_path\": \"backup_client\"}
				if err := json.Unmarshal([]byte(cast.ToString(val)), &ibsClient); err != nil {
					return errors.Wrapf(err, "fail to parse backup_client.ibs value:%v", val)
				} else {
					c.Params.Configs.BackupClient[k] = ibsClient
				}
			}
		} else {
			mapObj := make(map[string]interface{})
			if reflect.TypeOf(val).Kind() == reflect.Map {
				mapObj = val.(map[string]interface{})
			} else if err := json.Unmarshal([]byte(cast.ToString(val)), &mapObj); err != nil {
				return errors.Wrapf(err, "fail to parse backup_client value:%v", val)
			}
			c.Params.Configs.BackupClient[k] = mapObj
		}
	}
	yamlData, err := yaml.Marshal(c.Params.Configs) // use json tag
	if err != nil {
		return err
	}
	c.configFile = filepath.Join(c.installPath, "config.yaml")
	if err := os.WriteFile(c.configFile, yamlData, 0644); err != nil {
		return err
	}
	return nil
}
