package handler

import (
	"bk-dnsapi/internal/domain/entity"
	"bk-dnsapi/internal/domain/repo/domain"
	"bk-dnsapi/pkg/logger"
	"bk-dnsapi/pkg/tools"
	"encoding/json"
	"fmt"
	"runtime/debug"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
	"github.com/pkg/errors"
)

// 以下为域名管理(新功能页面)使用的接口，路径带 /v2。
// 与原 /domain 接口的区别：会同步维护域名管理人、更新人、更新时间(tb_dns_domain_info)，原接口行为不变

// recoverPanic 统一处理 panic
func recoverPanic(c *gin.Context) {
	if r := recover(); r != nil {
		logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
		SendResponse(c, fmt.Errorf("panic error:%v", r), Data{})
	}
}

// opContext 构造写操作的操作上下文：操作人取请求参数，客户端IP取请求来源IP
func opContext(c *gin.Context, operator string) domain.OpContext {
	return domain.OpContext{Operator: operator, ClientIp: c.ClientIP()}
}

// DnsMgrPutReqParam 新增域名参数
type DnsMgrPutReqParam struct {
	App       string `json:"app,required"`
	BkCloudId int64  `json:"bk_cloud_id"`
	// Operator 操作人，记为域名更新人和操作日志的操作人；不传则取域名管理人
	Operator string `json:"operator"`
	Domains  []struct {
		DomainName string   `json:"domain_name"`
		Instances  []string `json:"instances,required"`
		Manager    string   `json:"manager"`
		Remark     string   `json:"remark"`
		// DomainType 维护方式。0:集群托管 1:自主维护；传字符串按 0 处理
		DomainType FlexDomainType `json:"domain_type"`
	} `json:"domains"`
}

// AddDnsV2 添加域名
func (h *Handler) AddDnsV2(c *gin.Context) {
	defer recoverPanic(c)

	var addParam DnsMgrPutReqParam
	if err := c.BindJSON(&addParam); err != nil {
		SendResponse(c, err, Data{})
		return
	}
	logger.Info(fmt.Sprintf("add dns v2 begin, param [%+v]", addParam))

	var errMsg string
	var dnsBaseList []*entity.TbDnsBase
	for i := 0; i < len(addParam.Domains); i++ {
		domains := addParam.Domains[i]
		var err error
		if domains.DomainName, err = tools.CheckDomain(domains.DomainName); err != nil {
			errMsg += err.Error() + "\r\n"
			continue
		}
		if domains.Manager == "" {
			domains.Manager = "DBAManager"
		}
		for j := 0; j < len(domains.Instances); j++ {
			ins := strings.TrimSpace(domains.Instances[j])
			// 支持ip格式，默认端口为0
			if !strings.Contains(ins, "#") {
				ins += "#0"
			}
			ip, port, err := tools.GetIpPortByIns(ins)
			if err != nil {
				errMsg += err.Error() + "\r\n"
				continue
			}
			dnsBaseList = append(dnsBaseList, &entity.TbDnsBase{
				App:            addParam.App,
				DomainName:     domains.DomainName,
				Ip:             ip,
				Port:           port,
				StartTime:      time.Now(),
				LastChangeTime: time.Now(),
				Manager:        domains.Manager,
				Remark:         domains.Remark,
				DomainType:     int64(domains.DomainType),
				Status:         "1",
				BkCloudId:      addParam.BkCloudId,
			})
		}
	}
	if errMsg != "" {
		SendResponse(c, errors.New(errMsg), Data{})
		return
	}
	info, _ := json.Marshal(dnsBaseList)
	logger.Info(fmt.Sprintf("add v2 insert begin exec, param [%+v]", string(info)))

	rowsAffected, err := domain.DnsDomainMgrResource().Insert(dnsBaseList, opContext(c, addParam.Operator))
	_, _ = domain.DnsConfigResource().UpdateLaseUpdateTime()
	SendResponse(c, err, Data{RowsNum: rowsAffected})
}

// DnsMgrDelReqParam 删除域名参数
type DnsMgrDelReqParam struct {
	App       string `json:"app,required"`
	BkCloudId int64  `json:"bk_cloud_id"`
	// Operator 操作人，记为域名的更新人；不传则记为 system
	Operator string `json:"operator"`
	Domains  []struct {
		DomainName string   `json:"domain_name"`
		Instances  []string `json:"instances,required"`
	} `json:"domains"`
}

// DelDnsV2 删除域名
func (h *Handler) DelDnsV2(c *gin.Context) {
	defer recoverPanic(c)

	var delParam DnsMgrDelReqParam
	if err := c.BindJSON(&delParam); err != nil {
		SendResponse(c, err, Data{})
		return
	}
	if delParam.App == "" || len(delParam.Domains) == 0 {
		SendResponse(c, fmt.Errorf("param must have  [domain_name and app]"), Data{})
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
			var err error
			if domains.DomainName, err = tools.CheckDomain(domains.DomainName); err != nil {
				errMsg += err.Error() + "\r\n"
				continue
			}
		} else if len(domains.Instances) == 0 {
			// 不允许域名和实例同时为空
			errMsg += "domain_name and instances is empty" + "\r\n"
			continue
		}
		var ips []string
		for j := 0; j < len(domains.Instances); j++ {
			ins := strings.TrimSpace(domains.Instances[j])
			if !strings.Contains(ins, "#") {
				ins += "#0"
			}
			if _, _, err := tools.GetIpPortByIns(ins); err != nil {
				errMsg += err.Error() + "\r\n"
				continue
			}
			ips = append(ips, ins)
		}
		domainList = append(domainList, domains.DomainName)
		ipsList = append(ipsList, ips)
	}
	if errMsg != "" {
		SendResponse(c, errors.New(errMsg), Data{})
		return
	}

	for i := 0; i < len(domainList); i++ {
		rowsNum, err := domain.DnsDomainMgrResource().Delete(dnsBase.TableName(), delParam.App,
			domainList[i], delParam.BkCloudId, ipsList[i], opContext(c, delParam.Operator))
		if err != nil {
			logger.Error(fmt.Sprintf("delete domain[%s] failed: %v", domainList[i], err))
			SendResponse(c, err, Data{RowsNum: rowsAffected})
			return
		}
		rowsAffected += rowsNum
	}
	_, _ = domain.DnsConfigResource().UpdateLaseUpdateTime()
	SendResponse(c, nil, Data{Detail: nil, RowsNum: rowsAffected})
}

// parseKeepInstances 解析“更新后应保留的实例”列表，格式 ip#port，只传 ip 时端口为 0。
// 去掉空白、重复项，保持顺序；格式错误时在 errMsg 中累加原因
func parseKeepInstances(raw []string, errMsg *string) []domain.DomainInstance {
	var rs []domain.DomainInstance
	seen := map[domain.DomainInstance]bool{}
	for _, r := range raw {
		ins := strings.TrimSpace(r)
		if ins == "" {
			continue
		}
		if !strings.Contains(ins, "#") {
			ins += "#0"
		}
		ip, port, err := tools.GetIpPortByIns(ins)
		if err != nil {
			*errMsg += err.Error() + "\r\n"
			continue
		}
		k := domain.DomainInstance{Ip: ip, Port: port}
		if seen[k] {
			continue
		}
		seen[k] = true
		rs = append(rs, k)
	}
	return rs
}

// syncResultRows 统计同步结果中变更的实例数（新增+删除）
func syncResultRows(rs []domain.SyncDomainResult) (n int64) {
	for _, r := range rs {
		n += int64(len(r.Added) + len(r.Removed))
	}
	return n
}

// maxRemarkLen tb_dns_base.remark 的列长度
const maxRemarkLen = 128

// checkRemark 校验备注长度（按字符计），返回错误原因，合法返回空串。remark 为 nil 表示没传，不校验
func checkRemark(remark *string) string {
	if remark != nil && utf8.RuneCountInString(*remark) > maxRemarkLen {
		return fmt.Sprintf("remark is too long, max %d characters\r\n", maxRemarkLen)
	}
	return ""
}

// DnsMgrPostReqParam 更新单个域名参数
type DnsMgrPostReqParam struct {
	App        string `json:"app,required"`
	BkCloudId  int64  `json:"bk_cloud_id"`
	DomainName string `json:"domain_name,required"`
	// Instances 更新后该域名应保留的 ip#port 列表。不在列表中的现有实例会被删除，列表中新增的会被添加。
	// 不传或为空表示实例不变，此时 manager、remark 至少传一个
	Instances []string `json:"instances"`
	// Operator 操作人，记为域名的更新人；不传则记为 system
	Operator string `json:"operator"`
	// Manager 域名管理人，多个用英文逗号分隔；不传则不修改
	Manager string `json:"manager"`
	// Remark 域名备注（保存在 tb_dns_domain_info）；不传则不修改，传空串表示清空
	Remark *string `json:"remark"`
}

// UpdateDnsV2 更新域名：按保留实例列表同步，或只更新管理人、备注
func (h *Handler) UpdateDnsV2(c *gin.Context) {
	defer recoverPanic(c)

	var updateParam DnsMgrPostReqParam
	if err := c.BindJSON(&updateParam); err != nil {
		SendResponse(c, err, Data{})
		return
	}
	var errMsg, manager string
	var err error
	if updateParam.DomainName, err = tools.CheckDomain(updateParam.DomainName); err != nil {
		errMsg += err.Error() + "\r\n"
	}
	if manager, err = domain.ParseManagerParam(updateParam.Manager); err != nil {
		errMsg += err.Error() + "\r\n"
	}
	instances := parseKeepInstances(updateParam.Instances, &errMsg)
	errMsg += checkRemark(updateParam.Remark)
	if len(instances) == 0 && manager == "" && updateParam.Remark == nil && errMsg == "" {
		errMsg += "instances, manager and remark are all empty, nothing to update\r\n"
	}
	if errMsg != "" {
		SendResponse(c, errors.New(errMsg), Data{})
		return
	}

	rs, err := domain.DnsDomainMgrResource().SyncDomains(updateParam.App, updateParam.BkCloudId,
		[]domain.SyncDomainParam{{DomainName: updateParam.DomainName, Instances: instances, Manager: manager,
			Remark: updateParam.Remark}},
		opContext(c, updateParam.Operator))
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	_, _ = domain.DnsConfigResource().UpdateLaseUpdateTime()
	SendResponse(c, nil, Data{Detail: rs, RowsNum: syncResultRows(rs)})
}

// DnsMgrBatchPostReqParam 批量更新参数
type DnsMgrBatchPostReqParam struct {
	App       string `json:"app,required"`
	BkCloudId int64  `json:"bk_cloud_id"`
	// Operator 操作人，记为域名的更新人；不传则记为 system
	Operator string `json:"operator"`
	// Domains 要更新的域名，整批在一个事务里，任意一个失败全部回滚；同一域名不能重复出现
	Domains []struct {
		DomainName string `json:"domain_name,required"`
		// Instances 更新后该域名应保留的 ip#port 列表。不传或为空表示实例不变，此时 manager、remark 至少传一个
		Instances []string `json:"instances"`
		// Manager 域名管理人，多个用英文逗号分隔；不传则不修改
		Manager string `json:"manager"`
		// Remark 域名备注（保存在 tb_dns_domain_info）；不传则不修改，传空串表示清空
		Remark *string `json:"remark"`
	} `json:"domains,required"`
}

// UpdateBatchDnsV2 批量更新：每个域名按保留实例列表同步，或只更新管理人、备注
func (h *Handler) UpdateBatchDnsV2(c *gin.Context) {
	defer recoverPanic(c)

	var updateParam DnsMgrBatchPostReqParam
	if err := c.BindJSON(&updateParam); err != nil {
		SendResponse(c, err, Data{})
		return
	}
	if len(updateParam.Domains) == 0 {
		SendResponse(c, errors.New("domains is empty"), Data{})
		return
	}
	var errMsg string
	var params []domain.SyncDomainParam
	seen := map[string]bool{}
	for _, d := range updateParam.Domains {
		name, err := tools.CheckDomain(d.DomainName)
		if err != nil {
			errMsg += err.Error() + "\r\n"
			continue
		}
		if seen[name] {
			errMsg += fmt.Sprintf("domain[%s] is duplicated\r\n", name)
			continue
		}
		seen[name] = true
		manager, err := domain.ParseManagerParam(d.Manager)
		if err != nil {
			errMsg += err.Error() + "\r\n"
		}
		var insErr string
		instances := parseKeepInstances(d.Instances, &insErr)
		errMsg += insErr
		remarkErr := checkRemark(d.Remark)
		if remarkErr != "" {
			errMsg += fmt.Sprintf("domain[%s]: %s", name, remarkErr)
		}
		if len(instances) == 0 && manager == "" && d.Remark == nil && insErr == "" && err == nil && remarkErr == "" {
			errMsg += fmt.Sprintf("domain[%s]: instances, manager and remark are all empty, nothing to update\r\n",
				name)
		}
		params = append(params, domain.SyncDomainParam{DomainName: name, Instances: instances, Manager: manager,
			Remark: d.Remark})
	}
	if errMsg != "" {
		SendResponse(c, errors.New(errMsg), Data{})
		return
	}

	rs, err := domain.DnsDomainMgrResource().SyncDomains(updateParam.App, updateParam.BkCloudId, params,
		opContext(c, updateParam.Operator))
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	_, _ = domain.DnsConfigResource().UpdateLaseUpdateTime()
	SendResponse(c, nil, Data{Detail: rs, RowsNum: syncResultRows(rs)})
}
