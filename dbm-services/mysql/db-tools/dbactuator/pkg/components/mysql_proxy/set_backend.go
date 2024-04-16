/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package mysql_proxy 设置proxy后端,建立proxyh和master的关系
package mysql_proxy

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// ProxySetBackendCom  proxy set backend mysql comp
type ProxySetBackendCom struct {
	GeneralParam   *components.GeneralParam
	Params         ProxySetBackendParam
	proxyAdminConn *native.ProxyAdminDbWork `json:"-"`
}

// ProxySetBackendParam  proxy set backend mysql param
type ProxySetBackendParam struct {
	Host        string `json:"host" validate:"required,ip" `      // 当前实例的主机地址
	Port        int    `json:"port" validate:"required,gte=3306"` // 当前实例的端口
	BackendHost string `json:"backend_host" validate:"required,ip"`
	BackendPort int    `json:"backend_port" validate:"required,gte=3306"`
}

// Example  proxy set backend mysql example
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

// Init init proxy set backend mysql
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

// SetBackend set backend
/**
 * @description: refresh backends
 * @return {*}
 */
func (p *ProxySetBackendCom) SetBackend() (err error) {
	return p.proxyAdminConn.RefreshBackends(p.Params.BackendHost, p.Params.BackendPort)
}
