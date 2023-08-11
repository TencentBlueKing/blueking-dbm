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
// SpiderStorageLayer_switch defined remote node's fail-over main logic.

package dbmysql

import (
	"fmt"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

const (
//sql format to alter node
)

// SpiderStorageSwitch spider remote node switch
type SpiderStorageSwitch struct {
	SpiderCommonSwitch
	//proxy layer instance used(spider, proxy)
	Proxy []dbutil.ProxyInfo
}

// CheckSwitch check slave before switch
func (ins *SpiderStorageSwitch) CheckSwitch() (bool, error) {
	var err error
	if ins.Role == constvar.TenDBClusterStorageSlave {
		ins.ReportLogs(constvar.InfoResult, "instance is slave, skip switch check")
		return false, nil
	} else if ins.Role == constvar.TenDBClusterStorageMaster {
		log.Logger.Infof("info:{%s} is master", ins.ShowSwitchInstanceInfo())

		log.Logger.Infof("check slave status. info{%s}", ins.ShowSwitchInstanceInfo())
		if ins.StandBySlave == (MySQLSlaveInfo{}) {
			ins.ReportLogs(constvar.FailResult, "no slave info found")
			return false, err
		}
		if ins.StandBySlave.Status == constvar.UNAVAILABLE {
			ins.ReportLogs(constvar.FailResult, "standby slave's status is unavailable")
			return false, err
		}
		ins.SetInfo(constvar.SlaveIpKey, ins.StandBySlave.Ip)
		ins.SetInfo(constvar.SlavePortKey, ins.StandBySlave.Port)
		err = ins.CheckSlaveStatus()
		if err != nil {
			ins.ReportLogs(constvar.FailResult, err.Error())
			return false, err
		}

		log.Logger.Infof("start to switch. info{%s}", ins.ShowSwitchInstanceInfo())

		if len(ins.Proxy) == 0 {
			// available instance usual without proxy
			log.Logger.Infof("without spider! info:{%s}", ins.ShowSwitchInstanceInfo())
			ins.ReportLogs(constvar.InfoResult, "without proxy!")
			return false, nil
		}

	} else {
		return false, fmt.Errorf("unknown instance role:%s", ins.Role)
	}

	ins.ReportLogs(constvar.InfoResult, "remote node check slave info finished.")
	return true, nil
}

// DoSwitch do remote switch
// 1. connect primary tdbctl and update route
// 2. flush routing
func (ins *SpiderStorageSwitch) DoSwitch() error {
	//set primary, set all route info 
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get all route table before switch"))
	if err := ins.SetRoutes(); err != nil {
		return err
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("old master[%s#%d], old slave[%s#%d]",
		ins.Ip, ins.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port))
	oldMaster := ins.GetRouteInfo(ins.Ip, ins.Port)
	newMaster := ins.GetRouteInfo(ins.StandBySlave.Ip, ins.StandBySlave.Port)
	if oldMaster == nil || newMaster == nil {
		ins.ReportLogs(constvar.FailResult, "get master/slave's route failed")
		return fmt.Errorf("no master/slave's record found in route table")
	}

	//connect to primary tdbctl
	log.Logger.Debugf("connect to primary tdbctl")
	primaryConn, err := ins.ConnectPrimaryTdbctl()
	if err != nil {
		return fmt.Errorf("connect to primary tdbctl[%s#%d] failed:%s",
			ins.PrimaryTdbctl.Host, ins.PrimaryTdbctl.Port, err.Error())
	}
	defer func() {
		_ = primaryConn.Close()
	}()

	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to update route from old master to new master"))
	alterSQL := fmt.Sprintf(AlterNodeFormat, oldMaster.ServerName, newMaster.Host,
		newMaster.UserName, newMaster.Password, newMaster.Port)
	if result, err := primaryConn.Exec(alterSQL); err != nil {
		return fmt.Errorf("execute TDBCTL ALTER NODE failed:%s", err.Error())
	} else {
		if rowCnt, _ := result.RowsAffected(); rowCnt == 0 {
			//TODO: current tdbctl server's rowsAffected incorrect. Next version, should return error instead
			log.Logger.Warnf("execute TDBCTL ALTER NODE failed, rowsAffected 0")
		}
	}
	ins.ReportLogs(constvar.InfoResult, "update route info success, do flush next")

	if _, err = primaryConn.Exec(FlushRouteSQL); err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("flush route failed:%s", err.Error()))
		return fmt.Errorf("execute[%s] failed:%s", FlushRouteSQL, err.Error())
	}
	ins.ReportLogs(constvar.InfoResult, "flush route ok, switch success")

	return nil
}

// ShowSwitchInstanceInfo show db-mysql instance's switch info
func (ins *SpiderStorageSwitch) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("<%s#%d IDC:%s Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IDC, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)
	//TODO right way to check empty?
	if ins.StandBySlave != (MySQLSlaveInfo{}) {
		str = fmt.Sprintf("%s Switch from MASTER:<%s#%d> to SLAVE:<%s#%d>",
			str, ins.Ip, ins.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port)
	}
	return str
}

// RollBack proxy do rollback
func (ins *SpiderStorageSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo swap master, slave 's meta info in cmdb
func (ins *SpiderStorageSwitch) UpdateMetaInfo() error {
	cmdbClient := client.NewCmDBClient(&ins.Config.DBConf.CMDB, ins.Config.GetCloudId())
	if err := cmdbClient.SwapMySQLRole(ins.Ip, ins.Port,
		ins.StandBySlave.Ip, ins.StandBySlave.Port); err != nil {
		updateErrLog := fmt.Sprintf("swap db-mysql role failed. err:%s", err.Error())
		ins.ReportLogs(constvar.FailResult, updateErrLog)
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "update meta info success")
	return nil
}
