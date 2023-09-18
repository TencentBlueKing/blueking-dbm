package test

import (
	"fmt"
	"net/http"
	"testing"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbmodule"
)

func TestNewClientByAddrs(t *testing.T) {
	addr := "http://127.0.0.1:8080"
	c, _ := client.NewClientByAddrs([]string{addr}, constvar.CmDBName)
	param := c.ConvertParamForGetRequest(map[string]string{
		"apps": "test1",
	})
	result, err := c.DoNew(http.MethodGet, "/cmdb/cluster/query?"+param, nil, nil)
	if err != nil {
		fmt.Printf("requst failed:%s", err.Error())
	}
	fmt.Printf("%s", string(result.Data))
}

func TestGetInstanceByCity(t *testing.T) {
	GlobalConfig, err := config.ParseConfigureFile("../monitor_agent.yaml")
	if err != nil {
		fmt.Printf("get config failed. err:%s", err.Error())
		t.FailNow()
	}
	addr := "http://127.0.0.1:8080"
	c, _ := client.NewClientByAddrs([]string{addr}, constvar.CmDBName)
	cmdbC := client.CmDBClient{
		Client: *c,
	}
	rawList, err := cmdbC.GetDBInstanceInfoByCity("2")
	if err != nil {
		fmt.Printf("get instance failed. err:%s", err.Error())
		t.FailNow()
	}
	dbs, err := dbmodule.DBCallbackMap["tendbha"].FetchDBCallback(rawList, GlobalConfig)
	for _, info := range dbs {
		ip, port := info.GetAddress()
		fmt.Printf("%s, %d, %s, %s, %s\n", ip, port, info.GetType(), info.GetStatus(), info.GetApp())
	}
}

func TestGetInstanceByIp(t *testing.T) {
	addr := "http://127.0.0.1:8080"
	c, _ := client.NewClientByAddrs([]string{addr}, constvar.CmDBName)
	cmdbC := client.CmDBClient{
		Client: *c,
	}
	inf, err := cmdbC.GetDBInstanceInfoByIp("6.6.6.6")
	if err != nil {
		fmt.Printf("get instance failed. err:%s", err.Error())
		t.FailNow()
	}
	list, err := dbmodule.DBCallbackMap["tendbha"].GetSwitchInstanceInformation(inf, nil)
	if err != nil {
		fmt.Printf("get switch instance failed. err:%s", err.Error())
		t.FailNow()
	}
	for _, info := range list {
		fmt.Printf("%v\n", info)
	}
}

func TestHaDBAgentGetGMInfo(t *testing.T) {
	addr := "http://127.0.0.1:8080"
	c, _ := client.NewClientByAddrs([]string{addr}, constvar.HaDBName)
	hadb := client.HaDBClient{
		Client: *c,
	}
	gmInfo, err := hadb.AgentGetGMInfo()
	if err != nil {
		fmt.Printf("get gm failed. err:%s", err.Error())
		t.FailNow()
	}
	for _, info := range gmInfo {
		fmt.Printf("%v\n", info)
	}
}
