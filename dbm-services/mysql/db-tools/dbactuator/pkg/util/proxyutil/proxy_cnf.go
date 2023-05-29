package proxyutil

import (
	"fmt"
	"reflect"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// PROXY_SEC_NAME TODO
const PROXY_SEC_NAME = "mysql-proxy"

// ProxyCnfObject TODO
type ProxyCnfObject struct {
	MysqlProxy map[string]string `json:"mysql-proxy" sectag:"mysql-proxy"`
}

// ReplaceProxyConfigs TODO
type ReplaceProxyConfigs struct {
	AdminAddress        string `keytag:"admin-address"`
	AdminUserName       string `keytag:"admin-username"`
	AdminPassWord       string `keytag:"admin-password"`
	AdminLuaScript      string `keytag:"admin-lua-script"`
	AdminUsersFile      string `keytag:"admin-users-file"` // 配置文件
	ProxyAddress        string `keytag:"proxy-address"`
	ProxyBackendAddress string `keytag:"proxy-backend-addresses"`
	BaseDir             string `keytag:"basedir"`
	LogFile             string `keytag:"log-file"`
}

// NewProxyCnfObject TODO
func (c ProxyCnfObject) NewProxyCnfObject(proxycnffile string) (pf *util.CnfFile, err error) {
	pf = util.NewEmptyCnfObj(proxycnffile)
	for key, v := range c.MysqlProxy {
		pf.RenderSection(PROXY_SEC_NAME, key, v, true)
	}
	return
}

// ReplaceProxyConfigsObjects TODO
func ReplaceProxyConfigsObjects(f *util.CnfFile, c ReplaceProxyConfigs) error {
	t := reflect.TypeOf(c)
	v := reflect.ValueOf(c)
	if t.Kind() != reflect.Struct {
		return fmt.Errorf("proxycnf object reflect is not struct")
	}
	for i := 0; i < t.NumField(); i++ {
		keyName := t.Field(i).Tag.Get(util.KeyTag)
		val := v.Field(i).String()
		f.ReplaceValue(PROXY_SEC_NAME, string(keyName), false, val)
	}
	return nil
}
