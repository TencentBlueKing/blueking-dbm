package handler

import (
	"bk-dnsapi/internal/domain/repo/domain"
	"bk-dnsapi/pkg/tools"
	"fmt"
	"runtime/debug"

	"github.com/gin-gonic/gin"
	"github.com/go-mesh/openlogging"
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
			openlogging.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
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
			openlogging.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
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
			openlogging.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
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
