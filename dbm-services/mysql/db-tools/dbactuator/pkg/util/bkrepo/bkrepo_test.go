package bkrepo_test

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/bkrepo"
	"net/url"
	"path"
	"testing"
)

func TestUploadFile(t *testing.T) {
	t.Log("start...")
	r, err := url.Parse(path.Join("/generic", "/"))
	t.Log(r.String())
	resp, err := bkrepo.UploadFile("/tmp/1.sql", "", "", "", 0, "")
	if err != nil {
		t.Log(err.Error())
		return
	}
	t.Log(resp)
}
