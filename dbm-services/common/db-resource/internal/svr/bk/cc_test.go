package bk_test

import (
	"os"
	"testing"

	"dbm-services/common/db-resource/internal/controller/manage"
	"dbm-services/common/go-pubpkg/cc.v3"
)

func TestReserverCC(t *testing.T) {
	client, err := cc.NewClient(os.Getenv("BK_COMPONENT_API_URL"), cc.Secret{
		BKAppCode:   os.Getenv("BK_APP_CODE"),
		BKAppSecret: os.Getenv("BK_APP_SECRET"),
		BKUsername:  os.Getenv("BK_USERNAME"),
	})
	if err != nil {
		t.Fatalf("new client failed %s", err.Error())
		return
	}
	listBizHosts := cc.NewListBizHosts(client)

	resp, _, err := listBizHosts.QueryListBizHosts(&cc.ListBizHostsParam{
		BkBizId: 100443,
		HostPropertyFilter: cc.HostPropertyFilter{
			Condition: "AND",
			Rules: []cc.Rule{{
				Field:    "bk_cloud_id",
				Operator: "equal",
				Value:    0,
			}},
		},
		Fileds: []string{
			"bk_host_id",
			"bk_cloud_id",
			"bk_host_innerip",
			"bk_asset_id",
			"bk_mem",
			"bk_cpu",
			"idc_city_name",
			"idc_city_id",
			"sub_zone",
			"sub_zone_id",
		},
		Page: cc.BKPage{
			Start: 100,
			Limit: 100,
		},
	})
	if err != nil {
		t.Fatalf("query list biz hosts failed %s", err.Error())
	}
	t.Log(resp.Count)
	// t.Logf("all count is %d", resp.Count)
	var hosts []manage.HostBase
	for _, host := range resp.Info {
		t.Log(host.BKHostId, host.InnerIP)
		hosts = append(hosts, manage.HostBase{
			HostId: host.BKHostId,
			Ip:     host.InnerIP,
		})
	}
	param := manage.ImportMachParam{
		ForBizs: []int{1001, 1002},
		BkBizId: 100443,
		RsTypes: []string{"MySQL", "Redis"},
		Hosts:   hosts,
	}
	importResp, err := manage.Doimport(param)
	if err != nil {
		t.Fatal(err)
	}
	t.Log(importResp)
}
