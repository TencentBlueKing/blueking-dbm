/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctl

import (
	"errors"
	"fmt"
	"sync"

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// CheckTdbctlWithSpideRouterComp 检查spider和中控路由是否一致
type CheckTdbctlWithSpideRouterComp struct {
	GeneralParam *components.GeneralParam        `json:"general"`
	Params       CheckTdbctlWithSpideRouterParam `json:"extend"`
}

// CheckTdbctlWithSpideRouterParam 检查参数
type CheckTdbctlWithSpideRouterParam struct {
	Host string `json:"host"  validate:"required,ip"`                // 当前实例的主机地址
	Port int    `json:"port"  validate:"required,lt=65536,gte=3306"` // 当前实例的端口
}

// Example subcommand example input
func (c CheckTdbctlWithSpideRouterComp) Example() interface{} {
	return CheckTdbctlWithSpideRouterComp{
		Params: CheckTdbctlWithSpideRouterParam{
			Host: "127.0.0.1",
			Port: 26000,
		},
	}
}

// Run Run
func (c *CheckTdbctlWithSpideRouterComp) Run() (err error) {
	user := c.GeneralParam.RuntimeAccountParam.MonitorUser
	pwd := c.GeneralParam.RuntimeAccountParam.MonitorPwd
	conn, err := native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: user,
		Pwd:  pwd,
	}.Conn()
	if err != nil {
		logger.Error("connect to tdbctl failed, err: %s", err.Error())
		return err
	}
	defer conn.Close()
	tdbCtlConn := &native.TdbctlDbWork{DbWorker: *conn}
	logger.Info("开始检查SpiderMaster路由关系 ...")
	mspNodes, err := tdbCtlConn.GetMasterSpiderNodes()
	if err != nil {
		logger.Error("查询SpiderMaster节点信息失败: %s", err.Error())
		return err
	}
	masterSptRouters, err := tdbCtlConn.GetMasterSptRouters()
	if err != nil {
		logger.Error("查询主分片节点信息失败: %s", err.Error())
		return err
	}
	tdbCtlmasterSptRouters := lo.SliceToMap(masterSptRouters, func(item native.Server) (string, native.Server) {
		return item.ServerName, item
	})
	err = checkRouter(mspNodes, tdbCtlmasterSptRouters)
	if err != nil {
		return err
	}
	sspNodes, err := tdbCtlConn.GetSlaveSpiderNodes()
	if err != nil {
		logger.Error("查询SpiderSlave节点信息失败: %s", err.Error())
		return err
	}
	if len(sspNodes) == 0 {
		return err
	}
	slaveSptRouters, err := tdbCtlConn.GetSlaveSptRouters()
	if err != nil {
		logger.Error("查询Slave分片节点信息失败: %s", err.Error())
		return err
	}
	tdbCtlslaveSptRouters := lo.SliceToMap(slaveSptRouters, func(item native.Server) (string, native.Server) {
		return item.ServerName, item
	})
	logger.Info("检查从分片路由关系")
	err = checkRouter(sspNodes, tdbCtlslaveSptRouters)
	return err
}

func checkRouter(nodes []native.Server, tdbctlRouters map[string]native.Server) (err error) {
	var errs []error
	wg := sync.WaitGroup{}
	errChan := make(chan error)
	cChan := make(chan struct{}, 5)
	for _, node := range nodes {
		wg.Add(1)
		cChan <- struct{}{}
		go func(spiderNode native.Server) {
			logger.Info("开始检查 %s-%s的路由", spiderNode.ServerName, spiderNode.GetEndPoint())
			defer func() { wg.Done(); <-cChan }()
			sconn, errx := spiderNode.GetConn()
			if errx != nil {
				logger.Error("connect to spider %s failed, err: %s", spiderNode.GetEndPoint(), err.Error())
				errChan <- errx
				return
			}
			defer sconn.Close()
			var spiderSptRouters []native.Server
			if native.SvrNameIsSlaveSpiderShard(spiderNode.ServerName) {
				spiderSptRouters, errx = sconn.GetSlaveSptRouters()
			} else {
				spiderSptRouters, errx = sconn.GetMasterSptRouters()
			}
			if errx != nil {
				logger.Error("query mysql.servers failed, err: %s", err.Error())
				errChan <- errx
				return
			}
			errx = compareRouter(tdbctlRouters, spiderSptRouters)
			if errx != nil {
				errChan <- fmt.Errorf("[%s-%s]:%w", spiderNode.ServerName, spiderNode.GetEndPoint(), errx)
			}

		}(node)
	}
	go func() {
		wg.Wait()
		close(errChan)
	}()
	for err = range errChan {
		errs = append(errs, err)
	}
	return errors.Join(errs...)
}

func compareRouter(tdbctlRouters map[string]native.Server, spiderrRouters []native.Server) (err error) {
	spiderrRoutersMap := lo.SliceToMap(spiderrRouters, func(item native.Server) (string, native.Server) {
		return item.ServerName, item
	})
	for svrName, rt := range tdbctlRouters {
		spiderrRouter, ok := spiderrRoutersMap[svrName]
		if !ok {
			logger.Error("spider router not found router: %s", svrName)
			return err
		}
		if rt.Host != spiderrRouter.Host || rt.Port != spiderrRouter.Port {
			errMsg := "spider router not match  tdbctl router:"
			errMsg += fmt.Sprintf("tdbctl router:%s %s %d\n", rt.ServerName, rt.Host, rt.Port)
			errMsg += fmt.Sprintf("spider router:%s %s %d\n", spiderrRouter.ServerName, spiderrRouter.Host, spiderrRouter.Port)
			return fmt.Errorf("%s", errMsg)
		}
	}
	return
}
