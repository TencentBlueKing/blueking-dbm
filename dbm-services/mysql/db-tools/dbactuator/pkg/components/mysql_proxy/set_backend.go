// Package mysql_proxy TODO
/*
 * @Description:  设置proxy后端,建立proxyh和master的关系
 */
package mysql_proxy

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// ProxySetBackendCom TODO
type ProxySetBackendCom struct {
	GeneralParam   *components.GeneralParam
	Params         ProxySetBackendParam
	proxyAdminConn *native.ProxyAdminDbWork `json:"-"`
}

// ProxySetBackendParam TODO
type ProxySetBackendParam struct {
	Host        string `json:"host" validate:"required,ip" `      // 当前实例的主机地址
	Port        int    `json:"port" validate:"required,gte=3306"` // 当前实例的端口
	BackendHost string `json:"backend_host" validate:"required,ip"`
	BackendPort int    `json:"backend_port" validate:"required,gte=3306"`
}

// Example TODO
func (p *ProxySetBackendCom) Example() interface{} {
	comp := ProxySetBackendCom{
		Params: ProxySetBackendParam{
			Host:        "1.1.1.1",
			Port:        10000,
			BackendHost: "1.2.1.1",
			BackendPort: 20000,
		},
	}
	return comp
}

// Init TODO
/**
 * @description: 建立proxy amdin conn, 并且检查 backends 是否为 1.1.1.1:3306（新上架的proxy backends 一定是1.1.1.1:3306）
 * @return {*}
 */
func (p *ProxySetBackendCom) Init() (err error) {
	p.proxyAdminConn, err = native.InsObject{
		Host: p.Params.Host,
		Port: p.Params.Port,
		User: p.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		Pwd:  p.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	}.ConnProxyAdmin()
	if err != nil {
		logger.Error("connect proxy admin port(ori:%s) failed,%s", p.Params.Port, err.Error())
		return err
	}
	backend, err := p.proxyAdminConn.SelectBackend()
	if err != nil {
		logger.Error("get backends failed %s", err.Error())
		return err
	}
	// 在判断后端指向是否为 "1.1.1.1:3306"
	if strings.TrimSpace(backend.Address) != cst.DefaultBackend {
		return fmt.Errorf("current backends is not empty,%s", backend.Address)
	}
	return
}

// SetBackend TODO
/**
 * @description: refresh backends
 * @return {*}
 */
func (p *ProxySetBackendCom) SetBackend() (err error) {
	return p.proxyAdminConn.RefreshBackends(p.Params.BackendHost, p.Params.BackendPort)
}
