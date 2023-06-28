package bk

import (
	"net/url"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// EsbClient TODO
var EsbClient *cc.Client

// GseClient TODO
var GseClient *cc.Client

// CCModuleFields TODO
var CCModuleFields []string

// init TODO
func init() {
	var err error
	EsbClient, err = NewClient()
	if err != nil {
		logger.Fatal("init cmdb client failed %s", err.Error())
		return
	}
	GseClient, err = NewGseClient()
	if err != nil {
		logger.Fatal("init gse client failed %s", err.Error())
		return
	}
	CCModuleFields = []string{
		"bk_host_id",
		"bk_cloud_id",
		"bk_host_innerip",
		"bk_asset_id",
		"svr_device_class",
		"bk_mem",
		"bk_cpu",
		"bk_disk",
		"idc_city_id",
		"idc_city_name",
		"sub_zone",
		"sub_zone_id",
		"rack_id",
		"svr_type_name",
		"net_device_id",
	}
}

// NewGseClient TODO
func NewGseClient() (*cc.Client, error) {
	var apiserver string
	var err error
	apiserver = config.AppConfig.BkSecretConfig.GseBaseUrl
	if cmutil.IsEmpty(apiserver) {
		apiserver, err = url.JoinPath(config.AppConfig.BkSecretConfig.BkBaseUrl, "/api/bk-gse/prod")
		if err != nil {
			return nil, err
		}
	}
	return cc.NewClient(apiserver, cc.Secret{
		BKAppCode:   config.AppConfig.BkSecretConfig.BkAppCode,
		BKAppSecret: config.AppConfig.BkSecretConfig.BKAppSecret,
		BKUsername:  config.AppConfig.BkSecretConfig.BkUserName,
	})
}

// NewClient TODO
func NewClient() (*cc.Client, error) {
	return cc.NewClient(config.AppConfig.BkSecretConfig.BkBaseUrl, cc.Secret{
		BKAppCode:   config.AppConfig.BkSecretConfig.BkAppCode,
		BKAppSecret: config.AppConfig.BkSecretConfig.BKAppSecret,
		BKUsername:  config.AppConfig.BkSecretConfig.BkUserName,
	})
}

// BatchQueryHostsInfo TODO
func BatchQueryHostsInfo(bizId int, allhosts []string) (ccHosts []*cc.Host, nofoundHosts []string, err error) {
	for _, hosts := range cmutil.SplitGroup(allhosts, int64(200)) {
		err = cmutil.Retry(cmutil.RetryConfig{Times: 3, DelayTime: 1 * time.Second}, func() error {
			data, resp, err := cc.NewListBizHosts(EsbClient).QueryListBizHosts(&cc.ListBizHostsParam{
				BkBizId: bizId,
				Fileds:  CCModuleFields,
				Page: cc.BKPage{
					Start: 0,
					Limit: len(hosts),
				},
				HostPropertyFilter: cc.HostPropertyFilter{
					Condition: "AND",
					Rules: []cc.Rule{
						{
							Field:    "bk_host_innerip",
							Operator: "in",
							Value:    hosts,
						},
					},
				},
			})
			if resp != nil {
				logger.Info("respone request id is %s,message:%s,code:%d", resp.RequestId, resp.Message, resp.Code)
			}
			if err != nil {
				logger.Error("QueryListBizHosts failed %s", err.Error())
				return err
			}
			ccHosts = append(ccHosts, data.Info...)
			return nil
		})
	}
	searchMap := make(map[string]struct{})
	for _, host := range allhosts {
		searchMap[host] = struct{}{}
	}
	for _, hf := range ccHosts {
		delete(searchMap, hf.InnerIP)
		logger.Info("cc info %v", hf)
	}
	for host := range searchMap {
		nofoundHosts = append(nofoundHosts, host)
	}
	return ccHosts, nofoundHosts, err
}
