package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// NameServiceClient client to request name service
type NameServiceClient struct {
	Client
}

// DomainRes api response result
type DomainRes struct {
	Detail  []DomainInfo `json:"detail"`
	RowsNum int          `json:"rowsNum"`
}

// DomainInfo domain detail info struct
type DomainInfo struct {
	App            string    `json:"app"`
	DnsStr         string    `json:"dns_str"`
	DomainName     string    `json:"domain_name"`
	DomainType     int       `json:"domain_type"`
	Ip             string    `json:"ip"`
	LastChangeTime time.Time `json:"last_change_time"`
	Manager        string    `json:"manager"`
	Port           int       `json:"port"`
	Remark         string    `json:"remark"`
	StartTime      time.Time `json:"start_time"`
	Status         string    `json:"status"`
	Uid            int       `json:"uid"`
}

// NewNameServiceClient create new PolarisClbGWClient instance
func NewNameServiceClient(conf *config.APIConfig, cloudId int) *NameServiceClient {
	c := NewAPIClient(conf, constvar.DnsName, cloudId)
	return &NameServiceClient{c}
}

// GetDomainInfoByIp get domain info from dns by ip
func (c *NameServiceClient) GetDomainInfoByIp(ip string) ([]DomainInfo, error) {
	var res DomainRes
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"ip":             []string{ip},
	}
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.GetDomainInfoUrl, ""), req, nil)
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
	return res.Detail, nil
}

// GetDomainInfoByDomain get address info from dns by domain
func (c *NameServiceClient) GetDomainInfoByDomain(domainName string) ([]DomainInfo, error) {
	var res DomainRes
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"domain_name":    []string{domainName},
	}

	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.GetDomainInfoUrl, ""), req, nil)
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
	return res.Detail, nil
}

// DeleteDomain delete address from domain for dns
func (c *NameServiceClient) DeleteDomain(domainName string, app string, ip string, port int) error {
	var data DomainRes
	addr := fmt.Sprintf("%s#%d", ip, port)
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"app":            app,
		"domains": []map[string]interface{}{
			map[string]interface{}{
				"domain_name": domainName,
				"instances": []string{
					addr,
				},
			},
		},
	}

	log.Logger.Debugf("DeleteDomain param:%v", req)

	response, err := c.DoNew(http.MethodDelete,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.DeleteDomainUrl, ""), req, nil)
	if err != nil {
		return err
	}
	if response.Code != 0 {
		return fmt.Errorf("%s failed, return code:%d, msg:%s", util.AtWhere(), response.Code, response.Msg)
	}
	err = json.Unmarshal(response.Data, &data)
	if err != nil {
		return err
	}
	if data.RowsNum != 1 {
		return fmt.Errorf("rowsAffected = %d, delete domain %s failed. ip:%s, port:%d, app:%s",
			data.RowsNum, domainName, ip, port, app)
	}
	return nil
}

// PolarisClbGWResp the response format for polaris and clb
type PolarisClbGWResp struct {
	Ips []string `json:"ips,omitempty"`
}

// ClbDeRegister un-register address to clb
func (c *NameServiceClient) ClbDeRegister(
	region string, lbid string, listenid string, addr string) error {
	req := map[string]interface{}{
		"region":         region,
		"loadbalancerid": lbid,
		"listenerid":     listenid,
		"ips":            []string{addr},
	}

	log.Logger.Debugf("ClbDeRegister param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CLBDeRegisterUrl, ""),
		req, nil)
	if err != nil {
		log.Logger.Errorf("ClbDeRegister failed,%s", err.Error())
		return err
	}

	log.Logger.Debugf("ClbDeRegister:%v", response)
	return nil
}

// ClbGetTargets  get target address from clb
func (c *NameServiceClient) ClbGetTargets(
	region string, lbid string, listenid string,
) ([]string, error) {
	req := map[string]interface{}{
		"region":         region,
		"loadbalancerid": lbid,
		"listenerid":     listenid,
	}

	log.Logger.Debugf("ClbDeRegister param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.CLBGetTargetsUrl, ""),
		req, nil)
	if err != nil {
		log.Logger.Errorf("ClbGetTargets failed,%s", err.Error())
		return nil, err
	}

	log.Logger.Debugf("ClbGet Response:%v", response)
	var gwResp PolarisClbGWResp
	err = json.Unmarshal(response.Data, &gwResp)
	if err != nil {
		log.Logger.Errorf("ClbGetTargets failed,%s", err.Error())
		return make([]string, 0), err
	}
	return gwResp.Ips, nil
}

// GetPolarisTargets get target address from polaris
func (c *NameServiceClient) GetPolarisTargets(servicename string) ([]string, error) {
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"servicename":    servicename,
	}

	log.Logger.Debugf("GetPolarisTargets param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.PolarisTargetsUrl, ""),
		req, nil)
	if err != nil {
		return nil, err
	}

	var gwResp PolarisClbGWResp
	err = json.Unmarshal(response.Data, &gwResp)
	if err != nil {
		log.Logger.Errorf("ClbGetTargets failed,%s", err.Error())
		return make([]string, 0), err
	}

	return gwResp.Ips, nil
}

// PolarisUnBindTarget unbind address from polaris
func (c *NameServiceClient) PolarisUnBindTarget(
	servicename string, servertoken string, addr string) error {
	req := map[string]interface{}{
		"db_cloud_token": c.Conf.BKConf.BkToken,
		"bk_cloud_id":    c.CloudId,
		"servicename":    servicename,
		"servicetoken":   servertoken,
		"ips":            []string{addr},
	}

	log.Logger.Debugf("PolarisUnBindTarget param:%v", req)
	response, err := c.DoNew(http.MethodPost,
		c.SpliceUrlByPrefix(c.Conf.UrlPre, constvar.PolarisUnBindUrl, ""),
		req, nil)
	if err != nil {
		log.Logger.Errorf("PolarisUnBindTarget failed,%s", err.Error())
		return err
	}
	log.Logger.Debugf("PolarisUnBindTarget response:%v", response)
	return nil
}
