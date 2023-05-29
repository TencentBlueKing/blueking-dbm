package native_test

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"testing"
)

func TestConnProxyAdminPort(t *testing.T) {
	t.Log("start conn proxy")
	pc, err := native.NewDbWorkerNoPing("{IP}:11000", "proxy", "xx")
	if err != nil {
		t.Fatalf("conn proxy failed %s", err.Error())
		return
	}
	ver, err := pc.SelectVersion()
	if err != nil {
		t.Fatalf("get version failed %s", err.Error())
		return
	}
	t.Logf("current version is %s", ver)
}

func TestConnProxyAdminAddUser(t *testing.T) {
	t.Log("start conn proxy")
	pc, err := native.NewDbWorkerNoPing("{IP}:11000", "proxy", "xx")
	if err != nil {
		t.Fatalf("conn proxy failed %s", err.Error())
		return
	}
	af, err := pc.Exec("refresh_users('user@%','+') ")
	if err != nil {
		t.Fatalf("refresh_users %s", err.Error())
		return
	}
	t.Logf("current refresh_users is %d", af)
}

func TestGetProxyBackends(t *testing.T) {
	t.Log("start conn proxy")
	b := native.InsObject{
		Host: "",
		Port: 10000,
		User: "",
		Pwd:  "",
	}
	pc, err := b.ConnProxyAdmin()
	if err != nil {
		t.Fatalf("conn proxy failed %s", err.Error())
		return
	}
	backends, err := pc.SelectBackend()
	if err != nil {
		t.Fatalf("SelectBackends %s", err.Error())
		return
	}
	t.Logf("current SelectBackends is %v", backends)
}
