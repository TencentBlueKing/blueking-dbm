package test

import (
	"testing"

	"dbm-services/common/dbha/ha-module/util"
)

func TestMonIp(t *testing.T) {
	for i := 0; i < 100000; i++ {
		ip, err := util.GetMonIp()
		if err != nil {
			t.Errorf("get mon ip failed.err:%s", err.Error())
			return
		}
		if ip != "127.0.0.1" {
			t.Errorf("get mon ip error.ip:%s", ip)
			return
		}
	}
}
