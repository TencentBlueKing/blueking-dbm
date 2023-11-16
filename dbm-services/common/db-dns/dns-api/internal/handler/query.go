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

// GetDns 查询dns记录
func (h *Handler) GetDns(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			openlogging.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()

	openlogging.Info("get dns query begin")
	app := tools.TransZeroStrings(c.QueryArray("app"))
	insList := tools.TransZeroStrings(c.QueryArray("ip"))
	domainName := tools.TransZeroStrings(c.QueryArray("domain_name"))
	bkCloudId := tools.TransZeroString(c.Query("bk_cloud_id"))
	columns := tools.TransZeroStrings(c.QueryArray("columns"))

	// 初步检查
	if len(insList) == 0 && len(domainName) == 0 {
		SendResponse(c, fmt.Errorf("param must have one of [domain_name|ip]"), Data{})
		return
	}

	params := make(map[string]interface{})
	for i, d := range domainName {
		if !strings.HasSuffix(d, ".") {
			d += "."
			domainName[i] = d
		}
	}

	var ins []string
	var ip []string
	var errMsg string
	for _, t := range insList {
		// ip#port
		if strings.Contains(t, "#") {
			if tt, err := tools.CheckInstance(t); err != nil {
				errMsg += err.Error() + "\r\n"
				continue
			} else {
				ins = append(ins, strings.TrimSpace(tt))
			}
			//	ip
		} else {
			if tt, err := tools.CheckIp(t); err != nil {
				errMsg += err.Error() + "\r\n"
				continue
			} else {
				ip = append(ip, strings.TrimSpace(tt))
			}
		}
	}
	if errMsg != "" {
		SendResponse(c, fmt.Errorf(errMsg), Data{})
		return
	}

	params["domain_name"] = domainName
	params["app"] = app
	params["bk_cloud_id"] = bkCloudId
	if len(ins) != 0 {
		params["ins"] = ins
	}
	if len(ip) != 0 {
		params["ip"] = ip
	}

	if len(columns) == 0 {
		columns = new(entity.TbDnsBase).Columns()
	}
	openlogging.Info(fmt.Sprintf("query exec. params[%+v], columns[%+v]", params, columns))
	rs, err := domain.DnsDomainResource().Get(params, columns)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}

	SendResponse(c, nil, Data{
		Detail:  rs,
		RowsNum: int64(len(rs)),
	})
	return
}

// GetAllDns 查询所有域名。共reload程序用
func (h *Handler) GetAllDns(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			openlogging.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()

	bkCloudId := tools.TransZeroString(c.Query("bk_cloud_id"))
	columns := []string{"ip", "domain_name"}
	openlogging.Info(fmt.Sprintf("get all dns  query begin. bk_cloud_id is %v", bkCloudId))

	params := make(map[string]interface{})
	params["bk_cloud_id"] = bkCloudId
	rs, err := domain.DnsDomainResource().Get(params, columns)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	SendResponse(c, nil, Data{rs, int64(len(rs))})

	return

}

// GetAllConfig 查询所有config表配置
func (h *Handler) GetAllConfig(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			openlogging.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c,
				fmt.Errorf("panic error:%v", r),
				Data{})
		}
	}()
	params := make(map[string]interface{})
	rs, err := domain.DnsConfigResource().Get(params)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	SendResponse(c, nil, Data{rs, int64(len(rs))})

	return
}
