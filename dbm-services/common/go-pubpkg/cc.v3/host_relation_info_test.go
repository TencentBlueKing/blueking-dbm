package cc_test

import (
	"testing"

	"dbm-services/common/go-pubpkg/cc.v3"
)

func TestQueryHostRelationList(t *testing.T) {
	t.Log("start testing...")
	client, err := cc.NewClient("", cc.Secret{
		BKAppCode:   "",
		BKAppSecret: "",
		BKUsername:  "",
	})
	if err != nil {
		t.Fatal(err)
		return
	}
	cc.NewListBizHosts(client).QueryListBizHosts(&cc.ListBizHostsParam{})
	data, err := cc.NewHostRelationList(client).Query(&cc.HostMetaData{InnerIPs: []string{"127.0.0.1"}}, cc.BKPage{Start: 0, Limit: 100})
	if err != nil {
		t.Fatal(err)
		return
	}
	t.Log(data)
}
