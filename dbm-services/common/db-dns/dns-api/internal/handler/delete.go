package handler

import (
	"bk-dnsapi/internal/domain/entity"
	"bk-dnsapi/internal/domain/repo/domain"
	"bk-dnsapi/pkg/tools"
	"fmt"
	"runtime/debug"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/go-mesh/openlogging"
)

// DnsBaseDelReqParam base表删除参数
type DnsBaseDelReqParam struct {
	// Appid 	int64		`json:"appid"`
	App       string `json:"app,required"`
	BkCloudId int64  `json:"bk_cloud_id"`
	Domains   []struct {
		DomainName string   `json:"domain_name"`
		Instances  []string `json:"instances,required"`
	} `json:"domains"`
}

// DelDns 删除入口
func (h *Handler) DelDns(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			openlogging.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()

	var delParam DnsBaseDelReqParam
	err := c.BindJSON(&delParam)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}

	if delParam.App == "" || len(delParam.Domains) == 0 {
		SendResponse(c,
			fmt.Errorf("param must have  [domain_name and app]"),
			Data{})
		return
	}

	var errMsg string
	var rowsAffected int64
	var domainList []string
	ipsList := [][]string{}

	dnsBase := &entity.TbDnsBase{}
	for i := 0; i < len(delParam.Domains); i++ {
		domains := delParam.Domains[i]
		if domains.DomainName != "" {
			if domains.DomainName, err = tools.CheckDomain(domains.DomainName); err != nil {
				errMsg += err.Error() + "\r\n"
				continue
			}
		} else {
			// 不允许域名和实例同时为空
			if len(domains.Instances) == 0 {
				errMsg += "domain_name and instances is empty" + "\r\n"
				continue
			}
		}
		var ips []string
		for j := 0; j < len(domains.Instances); j++ {
			ins := strings.TrimSpace(domains.Instances[j])
			if !strings.Contains(ins, "#") {
				ins += "#0"
			}
			_, _, err := tools.GetIpPortByIns(ins)
			if err != nil {
				errMsg += err.Error() + "\r\n"
				continue
			}
			ips = append(ips, ins)
		}

		domainList = append(domainList, domains.DomainName)
		ipsList = append(ipsList, ips)
	}
	if errMsg != "" {
		SendResponse(c, err, Data{})
		return
	}

	for i := 0; i < len(domainList); i++ {
		rowsNum, _ := domain.DnsDomainResource().Delete(dnsBase.TableName(), delParam.App,
			domainList[i], delParam.BkCloudId, ipsList[i])
		rowsAffected += rowsNum
	}
	_, _ = domain.DnsConfigResource().UpdateLaseUpdateTime()

	SendResponse(c, nil, Data{
		Detail:  nil,
		RowsNum: rowsAffected,
	})
}
