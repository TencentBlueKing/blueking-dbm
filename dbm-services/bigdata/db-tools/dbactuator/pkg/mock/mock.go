// Package mock TODO
/*
 * @Description:  dbactuator 执行获取一些mock 参数
 */
package mock

import (
	"bytes"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
)

const (
	// MOCK_URL TODO
	MOCK_URL = "http://127.0.0.1:8080/bkconfig/v1/confitem/query"
)

// ApiRsp TODO
type ApiRsp struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// MockMysqlRotateConfigs TODO
func MockMysqlRotateConfigs() string {
	pbstr := []byte(`{
		"bk_biz_id": "0",
		"level_name": "plat",
		"level_value": "0",
		"conf_file": "main.conf",
		"conf_type": "MysqlRotate",
		"namespace": "tendbha",
		"format": "map."
	}`)
	s := query(pbstr)
	logger.Info(s)
	return s
}

// MockMysqlDbBackupConfigs TODO
/**
 * @description: 获取测试环境的备份配置
 * @return {*}
 */
func MockMysqlDbBackupConfigs() string {
	pbstr := []byte(`{
		"bk_biz_id":"0",
		"level_name":"plat",
		"level_value":"0",
		"conf_file":"dbbackup.conf,local_backup_config_not_upload",
		"conf_type":"MysqlBackup",
		"namespace":"tendbha",
		"format":"map"
	}`)
	return query(pbstr)
}

// MockMysqlMonitorData TODO
func MockMysqlMonitorData() string {
	pbstr := []byte(`{
		"bk_biz_id":"0",
		"level_name":"plat",
		"level_value":"0",
		"conf_file":"db_monitor,global_status",
		"conf_type":"MysqlMasterMonitor",
		"namespace":"tendbha",
		"format":"map."
	}`)
	return query(pbstr)
}

// MockProxyMonitorData TODO
func MockProxyMonitorData() string {
	pbstr := []byte(`{
	"bk_biz_id":"0",
    "level_name":"plat",
    "level_value":"0",
    "conf_file":"proxy_monitor,warn_receiver,xml_server",
    "conf_type":"MysqlProxyMonitor",
    "namespace":"tendbha",
    "format":"map"
	}`)
	return query(pbstr)
}

func query(pbstr []byte) string {
	req, err := http.NewRequest(http.MethodPost, MOCK_URL, bytes.NewBuffer(pbstr))
	if err != nil {
		fmt.Println("new request failed", err.Error())
		return ""
	}
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println(err)
		return ""
	}
	defer resp.Body.Close()
	pb, _ := ioutil.ReadAll(resp.Body)
	var d ApiRsp
	if err = json.Unmarshal(pb, &d); err != nil {
		fmt.Println("unmarshal", err)
		return ""
	}
	return string(d.Data)
}
