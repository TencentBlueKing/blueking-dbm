// Package api TODO
package api

import (
	"bytes"
	"dnsReload/config"
	"dnsReload/dao"
	"dnsReload/logger"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
)

// QueryForwardIp 根据dns ip 查询forward ip
func QueryForwardIp(ip string) string {
	forward_ip := config.GetConfig("forward_ip")
	return forward_ip
}

// BkapiAuthor TODO
type BkapiAuthor struct {
	BkAppCode   string `json:"bk_app_code"`
	BkAppSecret string `json:"bk_app_secret"`
}

// ApiResp TODO
type ApiResp struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    struct {
		Detail  []dao.TbDnsBase
		RowsNum int `json:"rowsNum"`
	}
}

// QueryAllDomainPost TODO
// POST方法 查询所有域名记录
func QueryAllDomainPost() ([]dao.TbDnsBase, error) {
	queryBody := make(map[string]string)
	queryBody["db_cloud_token"] = config.GetConfig("db_cloud_token")
	queryBody["bk_cloud_id"] = config.GetConfig("bk_cloud_id")
	logger.Info.Printf(fmt.Sprintf("body query params is ['%+v']", queryBody))

	bodyData, err := json.Marshal(queryBody)
	if err != nil {
		return nil, err
	}

	bk_url := config.GetConfig("bk_dns_api_url")
	req, err := http.NewRequest("POST", bk_url+"/apis/proxypass/dns/domain/all/", bytes.NewBuffer(bodyData))
	if err != nil {
		return nil, err
	}

	req.Header.Add("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var data ApiResp
	json.Unmarshal(body, &data)
	return data.Data.Detail, nil
}
