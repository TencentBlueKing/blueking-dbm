package client

import (
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
)

// CmDBClient client to request cmdb
type CmDBClient struct {
	Client
}

// NewCmDBClient init an new cmdb client to request
func NewCmDBClient(conf *config.APIConfig, cloudId int) (*CmDBClient, error) {
	c, err := NewAPIClient(conf, constvar.CmDBName, cloudId)
	return &CmDBClient{c}, err
}

// GetDBInstanceInfoByIp fetch instance info from cmdb by ip
func (c *CmDBClient) GetDBInstanceInfoByIp(ip string) ([]interface{}, error) {
	var res []interface{}
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"addresses":      []string{ip},
	}

	response, err := c.DoNew(
		http.MethodPost, c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CmDBInstanceUrl, ""), req, nil)
	if err != nil {
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &res)
	if err != nil {
		return nil, err
	}
	return res, nil
}

// GetDBInstanceInfoByCity detect running, available status instance
func (c *CmDBClient) GetDBInstanceInfoByCity(area string) ([]interface{}, error) {
	areaId, err := strconv.Atoi(area)
	if err != nil {
		log.Logger.Errorf("city is invalid, city:%s", area)
		return nil, err
	}

	req := map[string]interface{}{
		"db_cloud_token":   c.Conf.BKConf.BkToken,
		"bk_cloud_id":      c.CloudId,
		"logical_city_ids": []int{areaId},
		"statuses":         []string{constvar.RUNNING, constvar.AVAILABLE},
	}

	response, err := c.DoNew(
		http.MethodPost, c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CmDBInstanceUrl, ""), req, nil)
	if err != nil {
		return nil, err
	}
	if response.Code != 0 {
		return nil, fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}

	var res []interface{}
	err = json.Unmarshal(response.Data, &res)
	if err != nil {
		return nil, err
	}

	return res, nil
}

// SwapMySQLRole swap mysql master and slave's cmdb info
func (c *CmDBClient) SwapMySQLRole(masterIp string, masterPort int, slaveIp string, slavePort int) error {
	payloads := []map[string]interface{}{
		{
			"instance1": map[string]interface{}{
				"ip":   masterIp,
				"port": masterPort,
			},
			"instance2": map[string]interface{}{
				"ip":   slaveIp,
				"port": slavePort,
			},
		},
	}

	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"payloads":       payloads,
	}
	log.Logger.Debugf("SwapMySQLRole param:%v", req)

	response, err := c.DoNew(
		http.MethodPost, c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CmDBSwapRoleUrl, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	return nil
}

// SwapRedisRole swap redis master and slave's role info
func (c *CmDBClient) SwapRedisRole(domain string, masterIp string,
	masterPort int, slaveIp string, slavePort int) error {
	payload := map[string]interface{}{
		"master": map[string]interface{}{
			"ip":   masterIp,
			"port": masterPort,
		},
		"slave": map[string]interface{}{
			"ip":   slaveIp,
			"port": slavePort,
		},
		"domain": domain,
	}

	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"payload":        payload,
	}

	log.Logger.Debugf("SwapRedisRole param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CmDBRedisSwapUrl, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed,return code:%d,msg:%s",
			util.AtWhere(), response.Code, response.Msg)
	}
	return nil
}

// UpdateDBStatus update instance's status
func (c *CmDBClient) UpdateDBStatus(ip string, port int, status string) error {
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"payloads": []map[string]interface{}{
			{
				"ip":     ip,
				"port":   port,
				"status": status,
			},
		},
	}

	log.Logger.Debugf("UpdateDBStatus param:%v", req)

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CmDBUpdateStatusUrl, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	return nil
}

// GetEntryDetail get cluster's entry(domain) info
func (c *CmDBClient) GetEntryDetail(
	cluster string,
) (map[string]interface{}, error) {
	res := make(map[string]interface{})
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"domains":        []string{cluster},
	}

	log.Logger.Debugf("GetEntryDetail param:%v", req)
	response, err := c.DoNew(
		http.MethodPost, c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CmDBEntryDetailUrl, ""), req, nil,
	)

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
