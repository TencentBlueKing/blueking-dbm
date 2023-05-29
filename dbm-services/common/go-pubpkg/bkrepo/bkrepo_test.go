package bkrepo_test

import (
	"net/http"
	"testing"

	"dbm-services/common/go-pubpkg/bkrepo"
)

func TestDownload(t *testing.T) {
	t.Log("start ...")
	b := &bkrepo.BkRepoClient{
		Client: &http.Client{
			Transport: &http.Transport{},
		},
		BkRepoProject:   "",
		BkRepoPubBucket: "",
		BkRepoUser:      "",
		BkRepoPwd:       "",
		BkRepoEndpoint:  "",
	}
	err := b.Download("/dbbackup/latest", "dbbackup_2.2.48.tar.gz", "/data/")
	if err != nil {
		t.Fatalf(err.Error())
	}
	t.Log("ending ...")
}

func TestQueryMeta(t *testing.T) {
	t.Log("start ...")
	b := &bkrepo.BkRepoClient{
		Client: &http.Client{
			Transport: &http.Transport{},
		},
		BkRepoProject:   "",
		BkRepoPubBucket: "",
		BkRepoUser:      "",
		BkRepoPwd:       "",
		BkRepoEndpoint:  "",
	}
	d, err := b.QueryFileNodeInfo("/dbbackup/latest", "dbbackup_2.2.48.tar.gz")
	if err != nil {
		t.Fatalf(err.Error())
	}
	t.Log("ending ...", d)
}
