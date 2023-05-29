// Package proxytest proxy test
package proxytest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomproxy"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"time"
	// "dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomproxy"
	// "dbm-services/redis/db-tools/dbactuator/pkg/consts"
	// "dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// TwemproxyBackendsMd5Test TODO
// RedisBackupTest 场景需求测试
type TwemproxyBackendsMd5Test struct {
	proxies atomproxy.ProxyCheckParam
	// proxies   []atomproxy.ProxyInstances
	Err error `json:"-"`
}

// SetProxiesList TODO
// SetInatanceList 可配置，干掉老链接、检查同步状态 场景
func (test *TwemproxyBackendsMd5Test) SetProxiesList(ips []string, port int) {
	if test.Err != nil {
		return
	}

	for _, ip := range ips {
		test.proxies.Instances = append(test.proxies.Instances, atomproxy.ProxyInstances{IP: ip, Port: port})
	}
}

// RunCheckProxyBackends 检查proxy backends 是否一致
func (test *TwemproxyBackendsMd5Test) RunCheckProxyBackends() error {
	msg := fmt.Sprintf("=========CheckProxyBackendsTest start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========CheckProxyBackendsTest fail============")
		} else {
			msg = fmt.Sprintf("=========CheckProxyBackendsTest success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test.proxies)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomproxy.NewTwemproxySceneCheckBackends().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	return test.Err
}
