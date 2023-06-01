package client

import (
	"encoding/json"
	"fmt"
	"net/http"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// RemoteConfigClient TODO
type RemoteConfigClient struct {
	Client
}

// NewRemoteConfigClient create new RemoteConfigClient instance
func NewRemoteConfigClient(conf *config.APIConfig, cloudId int) (*RemoteConfigClient, error) {
	c, err := NewAPIClient(conf, constvar.DBConfigName, cloudId)
	return &RemoteConfigClient{c}, err
}

// BatchGetConfigItem the batch api for get configure item
func (c *RemoteConfigClient) BatchGetConfigItem(
	confFile string, confType string, confNames string,
	levelName string, levelValues []string, namespace string,
) (map[string]interface{}, error) {
	res := make(map[string]interface{})
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"conf_file":      confFile,
		"conf_name":      confNames,
		"conf_type":      confType,
		"level_name":     levelName,
		"level_values":   levelValues,
		"namespace":      namespace,
	}

	log.Logger.Debugf("BatchGetConfigItem param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.BKConfigBatchUrl, ""), req, nil)

	if err != nil {
		return nil, err
	}

	if response.Code != 0 {
		cmdbErr := fmt.Errorf("%s failed, return code:%d, msg:%s",
			util.AtWhere(), response.Code, response.Msg)
		return nil, cmdbErr
	}

	err = json.Unmarshal(response.Data, &res)
	if err != nil {
		return nil, err
	}

	return res, nil
}

// GetConfigItem support get configure item from dbconfig server
func (c *RemoteConfigClient) GetConfigItem(
	app string, confFile string, confType string,
	confName string, levelName string, levelValue string, namespace string,
) ([]map[string]interface{}, error) {
	res := make([]map[string]interface{}, 0)
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"bk_biz_id":      app,
		"conf_file":      confFile,
		"conf_type":      confType,
		"conf_name":      confName,
		"level_name":     levelName,
		"level_value":    levelValue,
		"namespace":      namespace,
		"format":         "map",
	}

	log.Logger.Debugf("BatchGetConfigItem param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.BKConfigQueryUrl, ""), req, nil)

	if err != nil {
		return nil, err
	}

	if response.Code != 0 {
		cmdbErr := fmt.Errorf("%s failed, return code:%d, msg:%s",
			util.AtWhere(), response.Code, response.Msg)
		log.Logger.Errorf(cmdbErr.Error())
		return nil, cmdbErr
	}

	err = json.Unmarshal(response.Data, &res)
	if err != nil {
		cmdbErr := fmt.Errorf("%s unmarshal failed,err:%s,response:%v",
			util.AtWhere(), err.Error(), response)
		log.Logger.Errorf(cmdbErr.Error())
		return nil, cmdbErr
	}
	return res, nil
}
