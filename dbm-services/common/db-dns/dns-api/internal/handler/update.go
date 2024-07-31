package handler

import (
	"bk-dnsapi/internal/domain/entity"
	"bk-dnsapi/internal/domain/repo/domain"
	"bk-dnsapi/pkg/tools"
	"fmt"
	"runtime/debug"
	"strings"

	"github.com/pkg/errors"

	"bk-dnsapi/pkg/logger"

	"github.com/gin-gonic/gin"
)

// DnsBasePostReqParam 更新结构体
type DnsBasePostReqParam struct {
	App        string `json:"app,required"`
	BkCloudId  int64  `json:"bk_cloud_id"`
	Instance   string `json:"instance,required"`
	DomainName string `json:"domain_name,required"`
	Set        struct {
		Instance string `json:"instance,required"`
	} `json:"set,required"`
}

// DnsBaseBatchPostReqParam 批量更新参数
type DnsBaseBatchPostReqParam struct {
	App        string `json:"app,required"`
	DomainName string `json:"domain_name,required"`
	BkCloudId  int64  `json:"bk_cloud_id"`
	Sets       []struct {
		OldInstance string `json:"old_instance,required"`
		NewInstance string `json:"new_instance,required"`
	} `json:"sets,required"`
}

// UpdateDns 更新域名
func (h *Handler) UpdateDns(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()

	var updateParam DnsBasePostReqParam
	err := c.BindJSON(&updateParam)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	// TODO check
	// check app exists、 domain_name、 instance format
	var errMsg string
	var ip, newIp string
	var port, newPort int

	if updateParam.DomainName, err = tools.CheckDomain(updateParam.DomainName); err != nil {
		errMsg += err.Error() + "\r\n"
	}
	if ip, port, err = tools.GetIpPortByIns(updateParam.Instance); err != nil {
		errMsg += err.Error() + "\r\n"
	}
	if newIp, newPort, err = tools.GetIpPortByIns(updateParam.Set.Instance); err != nil {
		errMsg += err.Error() + "\r\n"
	}

	// if ip,err = models.CheckIp(ip); err != nil{
	//	errMsg += err.Error() + "\r\n"
	// }
	// if newIp,err = models.CheckIp(newIp); err != nil{
	//	errMsg += err.Error() + "\r\n"
	// }

	if errMsg != "" {
		SendResponse(c, fmt.Errorf(errMsg), Data{})
		return
	}

	var batchDnsBases []domain.UpdateBatchDnsBase
	batchDnsBases = append(batchDnsBases, struct {
		App        string
		DomainName string
		OIp        string
		OPort      int
		NIp        string
		NPort      int
		BkCloudId  int64
	}{App: updateParam.App, DomainName: updateParam.DomainName, OIp: ip,
		OPort: port, NIp: newIp, NPort: newPort, BkCloudId: updateParam.BkCloudId})

	rowsAffected, err := domain.DnsDomainResource().UpdateDomainBatch(batchDnsBases)
	_, _ = domain.DnsConfigResource().UpdateLaseUpdateTime()
	SendResponse(c, err, Data{
		Detail:  nil,
		RowsNum: rowsAffected,
	})
}

// UpdateBatchDns 批量更新
func (h *Handler) UpdateBatchDns(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()

	var updateParam DnsBaseBatchPostReqParam
	err := c.BindJSON(&updateParam)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	// TODO check
	// check app exists、 domain_name、 instance format
	var errMsg string
	var ip, newIp string
	var port, newPort int
	var batchDnsBases []domain.UpdateBatchDnsBase

	if updateParam.DomainName, err = tools.CheckDomain(updateParam.DomainName); err != nil {
		errMsg += err.Error() + "\r\n"
	}
	for _, s := range updateParam.Sets {
		if ip, port, err = tools.GetIpPortByIns(s.OldInstance); err != nil {
			errMsg += err.Error() + "\r\n"
		}
		if newIp, newPort, err = tools.GetIpPortByIns(s.NewInstance); err != nil {
			errMsg += err.Error() + "\r\n"
		}

		batchDnsBases = append(batchDnsBases, struct {
			App        string
			DomainName string
			OIp        string
			OPort      int
			NIp        string
			NPort      int
			BkCloudId  int64
		}{App: updateParam.App, DomainName: updateParam.DomainName, OIp: ip,
			OPort: port, NIp: newIp, NPort: newPort, BkCloudId: updateParam.BkCloudId})
	}
	if errMsg != "" {
		SendResponse(c, fmt.Errorf(errMsg), Data{})
		return
	}

	rowsAffected, err := domain.DnsDomainResource().UpdateDomainBatch(batchDnsBases)
	_, _ = domain.DnsConfigResource().UpdateLaseUpdateTime()

	SendResponse(c, err, Data{
		Detail:  nil,
		RowsNum: rowsAffected,
	})
}

type DnsConfigPostReqParam struct {
	Paraname   string `json:"paraname,required"`
	Paravalue  string `json:"paravalue,required"`
	Pararemark string `json:"pararemark"`
}

// UpdateConfig 更新配置
func (h *Handler) UpdateConfig(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()

	var updateParam DnsConfigPostReqParam
	err := c.BindJSON(&updateParam)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}

	rowsAffected, err := domain.DnsConfigResource().Update(updateParam.Paraname, map[string]interface{}{
		"paravalue":  updateParam.Paravalue,
		"pararemark": updateParam.Pararemark})
	SendResponse(c, err, Data{
		Detail:  nil,
		RowsNum: rowsAffected,
	})
}

type DnsBaseUpdateAppParam struct {
	BkCloudId  int64  `json:"bk_cloud_id"`
	DomainName string `json:"domain_name,required"`
	App        string `json:"app"`
	NewApp     string `json:"new_app"`
}

// UpdateDomainApp 更新域名记录的app
func (h *Handler) UpdateDomainApp(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()

	var updateParam DnsBaseUpdateAppParam
	err := c.BindJSON(&updateParam)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	if !strings.HasSuffix(updateParam.DomainName, ".") {
		updateParam.DomainName += "."
	}

	// 先根据域名、app、bkID查询一遍
	queryParams := map[string]interface{}{
		"domain_name": updateParam.DomainName,
		"app":         updateParam.App,
		"bk_cloud_id": updateParam.BkCloudId,
	}
	logger.Info(fmt.Sprintf("update before query once. params[%+v]", queryParams))
	rs, err := domain.DnsDomainResource().Get(queryParams, new(entity.TbDnsBase).Columns())
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	if len(rs) == 0 {
		SendResponse(c, errors.New("query domain record is 0. please check params"), Data{})
		return
	}

	// 更新
	logger.Info(fmt.Sprintf("update will exec. params[%+v]", updateParam))
	rowsAffected, err := domain.DnsDomainResource().UpdateFieldsByDomain(updateParam.DomainName, updateParam.BkCloudId,
		map[string]interface{}{"app": updateParam.NewApp})
	SendResponse(c, err, Data{
		Detail:  nil,
		RowsNum: rowsAffected,
	})
}
