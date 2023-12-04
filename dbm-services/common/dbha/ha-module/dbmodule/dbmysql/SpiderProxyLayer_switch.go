/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
// Package dbmysql
// SpiderProxyLayer file defined spider node's fail-over main logic.

package dbmysql

import (
	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"fmt"
	"strings"
)

// SpiderProxyLayerSwitch spider node switch
type SpiderProxyLayerSwitch struct {
	SpiderCommonSwitch
	//proxy layer instance used(spider, proxy)
	AdminPort int
	//storage layer instance used
	Entry dbutil.BindEntry
	Proxy []dbutil.ProxyInfo
}

// ElectPrimary elect a new primary, only spider-master broken-down may do this
func (ins *SpiderProxyLayerSwitch) ElectPrimary() (TdbctlInfo, error) {
	dbConf := ins.Config.DBConf
	log.Logger.Debugf("route info:%#v", ins.RouteTable)
	for _, node := range ins.RouteTable {
		//only spider-master had tdbctl node, should connect use admin port
		if strings.EqualFold(node.Wrapper, constvar.WrapperTdbctl) {
			//exclude broken-down tdbctl node
			if node.Host == ins.Ip && node.Port == ins.AdminPort {
				continue
			}

			tdbctlIns := MySQLSwitch{
				MySQLCommonSwitch: MySQLCommonSwitch{
					BaseSwitch: dbutil.BaseSwitch{
						Ip:         ins.Ip,
						Port:       ins.AdminPort,
						Config:     ins.Config,
						CmDBClient: client.NewCmDBClient(&dbConf.CMDB, ins.Config.GetCloudId()),
						HaDBClient: client.NewHaDBClient(&dbConf.HADB, ins.Config.GetCloudId()),
						SwitchUid:  ins.GetSwitchUid(),
					},
					StandBySlave: dbutil.SlaveInfo{
						Ip:   node.Host,
						Port: node.Port,
					},
				},
			}
			if err := tdbctlIns.CheckSlaveStatus(); err != nil {
				ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("tdbctl[%s#%d] not satisfied elect:%s,"+
					"try another", node.Host, node.Port, err.Error()))
				continue
			}

			//try to connect a tdbctl node, and get primary tdbctl
			connParam := fmt.Sprintf("%s:%s@(%s:%d)/%s",
				dbConf.MySQL.User, dbConf.MySQL.Pass, node.Host, node.Port, "infodba_schema")
			if tdbctlConn, err := dbutil.ConnMySQL(connParam); err != nil {
				log.Logger.Warnf("connect tdbctl[%s#%d] failed:%s, retry others",
					node.Host, node.Port, err.Error())
				//connect failed, try another
				continue
			} else {
				if _, err = tdbctlConn.Exec(ForcePrimarySQL); err != nil {
					_ = tdbctlConn.Close()
					ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("tdbctl[%s#%d] do "+
						"[%s] failed:%s, try another", node.Host, node.Port, ForcePrimarySQL, err.Error()))
					continue
				}
				_ = tdbctlConn.Close()

				ins.ReportLogs(constvar.InfoResult, "try to reset slave on new primary")
				if binlogFile, binlogPosition, err := tdbctlIns.ResetSlave(); err != nil {
					ins.ReportLogs(constvar.FailResult, fmt.Sprintf("reset slave failed:%s", err.Error()))
				} else {
					ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("reset slave success,"+
						"consistent binlog info:%s,%d", binlogFile, binlogPosition))
				}
				return TdbctlInfo{
					ServerName: node.ServerName,
					Host:       node.Host,
					Port:       node.Port,
				}, nil
			}
		}
	}
	return TdbctlInfo{}, fmt.Errorf("elect new tdbctl primary node failed, no satified node found")
}

// CheckSwitch check whether satisfy switch before do real switch
func (ins *SpiderProxyLayerSwitch) CheckSwitch() (bool, error) {
	return true, nil
}

// DoSwitch do spider(include tdbctl) switch
// 1. release broken-down node's name service if exist
// 2. found primary tdbctl, if primary broken-down, do elect first
// 3. remove broken-down node from primary-tdbctl route table
// 4. primary-tdbctl do flush routing
func (ins *SpiderProxyLayerSwitch) DoSwitch() error {
	//set switch instance's route info(set primary tdbctl also)
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get all route table before switch"))
	if err := ins.SetRoutes(); err != nil {
		return err
	}

	//1. update name service
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to release ip[%s#%d] from all entery",
		ins.Ip, ins.Port))
	if err := ins.DeleteNameService(ins.Entry); err != nil {
		return err
	}

	//2. connect primary tdbctl
	//if primary tdbctl broken-down, elect new reliable primary first
	oldPrimary := ins.PrimaryTdbctl
	if oldPrimary.CurrentServer == 1 {
		ins.ReportLogs(constvar.InfoResult, "primary tdbctl broken-down, try to elect a new one")
		if newPrimary, err := ins.ElectPrimary(); err != nil {
			return err
		} else {
			ins.PrimaryTdbctl = newPrimary
		}
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("elect new primary tdbctl success:%s#%d",
			ins.PrimaryTdbctl.Host, ins.PrimaryTdbctl.Port))

	}

	log.Logger.Debugf("connect to primary tdbctl and update route")
	primaryConn, err := ins.ConnectPrimaryTdbctl()
	if err != nil {
		return err
	}
	defer func() {
		_ = primaryConn.Close()
	}()

	//3. remove broken-down spider node from route table
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("remove spider node[%s#%d] from route table",
		ins.Ip, ins.Port))
	if err := ins.RemoveNodeFromRoute(primaryConn, ins.Ip, ins.Port); err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("remove spider node failed:%s", err.Error()))
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "remove spider node success")

	//4. remove broken-down tdbctl node from route table
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("remove tdbctl node[%s#%d] from route table",
		ins.Ip, ins.AdminPort))
	if err := ins.RemoveNodeFromRoute(primaryConn, ins.Ip, ins.AdminPort); err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("remove tdbctl node[%s#%d] from route-table failed:%s",
			ins.Ip, ins.AdminPort, err.Error()))
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "remove tdbctl node success")

	//5. flush routing
	ins.ReportLogs(constvar.InfoResult, "flush route table")
	if _, err = primaryConn.Exec(FlushRouteSQL); err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("flush route failed:%s", err.Error()))
		return fmt.Errorf("execute[%s] failed:%s", FlushRouteSQL, err.Error())
	}
	ins.ReportLogs(constvar.SuccessResult, "flush ok, switch success")

	return nil
}

// RollBack proxy do rollback
func (ins *SpiderProxyLayerSwitch) RollBack() error {
	return nil
}

// ShowSwitchInstanceInfo show db-mysql instance's switch info
func (ins *SpiderProxyLayerSwitch) ShowSwitchInstanceInfo() string {
	return fmt.Sprintf("<%s#%d IDC:%d Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IdcID, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)
}
