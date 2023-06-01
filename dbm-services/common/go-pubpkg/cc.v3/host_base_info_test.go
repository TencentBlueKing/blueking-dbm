package cc_test

import (
	"testing"

	"dbm-services/common/go-pubpkg/cc.v3"
)

func TestQueryHostBaseInfo(t *testing.T) {
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
	t.Log("1111")
	// 2000026095
	data, err := cc.NewHostBaseInfo(client).Query(2000026095)
	if err != nil {
		t.Fatal(err)
		return
	}
	for _, v := range data {
		t.Log(v)
	}

}
