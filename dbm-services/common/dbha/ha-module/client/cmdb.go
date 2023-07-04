package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// CmDBClient client to request cmdb
type CmDBClient struct {
	Client
}

// DBInstanceInfoRequest fetch instances list from cmdb by ip
type DBInstanceInfoRequest struct {
	DBCloudToken string   `json:"db_cloud_token"`
	BKCloudID    int      `json:"bk_cloud_id"`
	Addresses    []string `json:"addresses"`
}

// DBInstanceInfoByCityRequest fetch instances list from cmdb by city and status
type DBInstanceInfoByCityRequest struct {
	DBCloudToken   string   `json:"db_cloud_token"`
	BKCloudID      int      `json:"bk_cloud_id"`
	LogicalCityIDs []int    `json:"logical_city_ids"`
	Statuses       []string `json:"statuses"`
}

// DBInstanceInfo instance info
type DBInstanceInfo struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
}

// SwapMySQLRolePayload mysql instance need to swap role
type SwapMySQLRolePayload struct {
	Instance1 DBInstanceInfo `json:"instance1"`
	Instance2 DBInstanceInfo `json:"instance2"`
}

// SwapMySQLRoleRequest swap mysql instance's role in cmdb
type SwapMySQLRoleRequest struct {
	DBCloudToken string                 `json:"db_cloud_token"`
	BKCloudID    int                    `json:"bk_cloud_id"`
	Payloads     []SwapMySQLRolePayload `json:"payloads"`
}

// SwapRedisRolePayload redis instance need to swap role
type SwapRedisRolePayload struct {
	Master DBInstanceInfo `json:"master"`
	Slave  DBInstanceInfo `json:"slave"`
	Domain string         `json:"domain"`
}

// SwapRedisRoleRequest swap redis instance's role in cmdb
type SwapRedisRoleRequest struct {
	DBCloudToken string                 `json:"db_cloud_token"`
	BKCloudID    int                    `json:"bk_cloud_id"`
	Payloads     []SwapRedisRolePayload `json:"payloads"`
}

// UpdateInstanceStatusPayload update instance status
type UpdateInstanceStatusPayload struct {
	IP     string `json:"ip"`
	Port   int    `json:"port"`
	Status string `json:"status"`
}

// UpdateInstanceStatusRequest update instance status request
type UpdateInstanceStatusRequest struct {
	DBCloudToken string                        `json:"db_cloud_token"`
	BKCloudID    int                           `json:"bk_cloud_id"`
	Payloads     []UpdateInstanceStatusPayload `json:"payloads"`
}

type GetClusterDetailByDomainRequest struct {
	DBCloudToken string   `json:"db_cloud_token"`
	BKCloudID    int      `json:"bk_cloud_id"`
	Domains      []string `json:"domains"`
}

// NewCmDBClient init an new cmdb client to request
func NewCmDBClient(conf *config.APIConfig, cloudId int) (*CmDBClient, error) {
	c, err := NewAPIClient(conf, constvar.CmDBName, cloudId)
	return &CmDBClient{c}, err
}

// GetDBInstanceInfoByIp fetch instance info from cmdb by ip
func (c *CmDBClient) GetDBInstanceInfoByIp(ip string) ([]interface{}, error) {
	var res []interface{}
	req := DBInstanceInfoRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Addresses:    []string{ip},
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

	req := DBInstanceInfoByCityRequest{
		DBCloudToken:   c.Conf.BKConf.BkToken,
		BKCloudID:      c.CloudId,
		LogicalCityIDs: []int{areaId},
		Statuses:       []string{constvar.RUNNING, constvar.AVAILABLE},
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
	payload := SwapMySQLRolePayload{
		Instance1: DBInstanceInfo{
			IP:   masterIp,
			Port: masterPort,
		},
		Instance2: DBInstanceInfo{
			IP:   slaveIp,
			Port: slavePort,
		},
	}

	req := SwapMySQLRoleRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Payloads:     []SwapMySQLRolePayload{payload},
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
	payload := SwapRedisRolePayload{
		Master: DBInstanceInfo{
			IP:   masterIp,
			Port: masterPort,
		},
		Slave: DBInstanceInfo{
			IP:   slaveIp,
			Port: slavePort,
		},
		Domain: domain,
	}

	req := SwapRedisRoleRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Payloads:     []SwapRedisRolePayload{payload},
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
	req := UpdateInstanceStatusRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Payloads: []UpdateInstanceStatusPayload{
			{
				IP:     ip,
				Port:   port,
				Status: status,
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
func (c *CmDBClient) GetEntryDetail(cluster string) (map[string]interface{}, error) {
	res := make(map[string]interface{})
	req := GetClusterDetailByDomainRequest{
		DBCloudToken: c.Conf.BKConf.BkToken,
		BKCloudID:    c.CloudId,
		Domains:      []string{cluster},
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
