/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"fmt"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/go-pubpkg/logger"
)

// SqlserverSwitch defined sqlserver-related switch struct
type SqlserverSwitch struct {
	dbutil.BaseSwitch
	//instance role type
	Role string
	//standby slave which master switch to
	StandBySlave dbutil.SlaveInfo
	Entry        dbutil.BindEntry
}

func (ins *SqlserverSwitch) SetStandbySlave(slaves []dbutil.SlaveInfo) {
	if len(slaves) > 0 {
		//try to found standby slave
		ins.StandBySlave = slaves[0]
		for _, slave := range slaves {
			if slave.IsStandBy {
				ins.StandBySlave = slave
				break
			}
		}
		log.Logger.Debugf("set standy slave success:%#v", ins.StandBySlave)
	} else {
		ins.StandBySlave = dbutil.SlaveInfo{}
	}
}

// ShowSwitchInstanceInfo todo
func (ins *SqlserverSwitch) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("<%s#%d IDC:%d Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IdcID, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)

	if ins.StandBySlave != (dbutil.SlaveInfo{}) {
		str = fmt.Sprintf("%s Switch from MASTER:<%s#%d> to SLAVE:<%s#%d>",
			str, ins.Ip, ins.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port)
	}
	return str
}

// CheckSwitch check slave before switch
func (ins *SqlserverSwitch) CheckSwitch() (bool, error) {
	var err error
	if ins.Role == constvar.TenDBStorageSlave {
		ins.ReportLogs(constvar.InfoResult, "instance is slave, needn't check")
		return false, nil
	} else if ins.Role == constvar.TenDBStorageRepeater {
		ins.ReportLogs(constvar.FailResult, "instance is repeater, dbha not support")
		return false, err
	} else if ins.Role == constvar.TenDBStorageMaster {
		log.Logger.Infof("info:{%s} is master", ins.ShowSwitchInstanceInfo())

		log.Logger.Infof("check slave status. info{%s}", ins.ShowSwitchInstanceInfo())
		if ins.StandBySlave == (dbutil.SlaveInfo{}) {
			ins.ReportLogs(constvar.FailResult, "no standby slave info found")
			return false, err
		}
		if ins.StandBySlave.Status == constvar.UNAVAILABLE {
			ins.ReportLogs(constvar.FailResult, "standby slave's status is unavailable")
			return false, err
		}

		ins.SetInfo(constvar.SlaveIpKey, ins.StandBySlave.Ip)
		ins.SetInfo(constvar.SlavePortKey, ins.StandBySlave.Port)

		log.Logger.Infof("start to switch. info{%s}", ins.ShowSwitchInstanceInfo())

	} else {
		err = fmt.Errorf("info:{%s} unknown role", ins.ShowSwitchInstanceInfo())
		log.Logger.Error(err)
		ins.ReportLogs(constvar.FailResult, "instance unknown role")
		return false, err
	}

	ins.ReportLogs(constvar.InfoResult, "db-mssql check switch ok")
	return true, nil
}

// DoSwitch todo
func (ins *SqlserverSwitch) DoSwitch() error {
	var err error
	switchUser := ins.Config.DBConf.Sqlserver.User
	switchPass := ins.Config.DBConf.Sqlserver.Pass
	execTimeout := ins.Config.DBConf.Sqlserver.Timeout
	newMasterDB, err := NewDbWorker(switchUser, switchPass, ins.StandBySlave.Ip, ins.StandBySlave.Port, execTimeout)
	if err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("connect new master db failed:%s", err.Error()))
	}
	// loss_over sql
	if err = ExecSwitchSP(newMasterDB, "Sys_AutoSwitch_LossOver", ""); err != nil {
		logger.Error(
			"exec Sys_AutoSwitch_LossOver in instance [%s:%d] failed: %s",
			ins.StandBySlave.Ip,
			ins.StandBySlave.Port,
			err.Error(),
		)
		return err
	}

	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("exec Sys_AutoSwitch_LossOver instance [%s:%d] successfully",
			ins.StandBySlave.Ip,
			ins.StandBySlave.Port,
		),
	)
	// delete dns for old_master
	if err := ins.DeleteNameService(ins.Entry); err != nil {
		return err
	}

	// create dns in new master
	conf := ins.Config
	ins.ReportLogs(
		constvar.InfoResult,
		fmt.Sprintf("try to create dns entry [%s:%d]", ins.StandBySlave.Ip, ins.StandBySlave.Port),
	)
	dnsClient := client.NewNameServiceClient(&conf.NameServices.DnsConf, conf.GetCloudId())
	for _, dns := range ins.Entry.Dns {
		isExist := false
		var details []client.DomainInfo
		if details, err = dnsClient.GetDomainInfoByDomain(dns.DomainName); err != nil {
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("check domain[%s] in dns_service failed:%s",
				dns.DomainName, err.Error()))
			return err
		}

		for _, info := range details {
			log.Logger.Debug(info)
			if info.Ip == ins.StandBySlave.Ip {
				// exist in dns
				ins.ReportLogs(
					constvar.FailResult, fmt.Sprintf(" ip[%s] to domain[%s] exist", info.Ip, dns.DomainName),
				)
				isExist = true
				break
			}
		}
		if !isExist {
			// create dns-new_master_ip
			if err := dnsClient.CreateDomain(
				dns.DomainName, ins.GetApp(), ins.StandBySlave.Ip, ins.StandBySlave.Port,
			); err != nil {

				ins.ReportLogs(constvar.FailResult, fmt.Sprintf("create ip[%s] to domain[%s] failed:%s",
					ins.StandBySlave.Ip, dns.DomainName, err.Error()))
				return err

			}
		}

	}
	return nil
}

// RollBack todo
func (ins *SqlserverSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo todo
func (ins *SqlserverSwitch) UpdateMetaInfo() error {
	cmdbClient := client.NewCmDBClient(&ins.Config.DBConf.CMDB, ins.Config.GetCloudId())
	if err := cmdbClient.SwapSqlserverRole(ins.Ip, ins.Port,
		ins.StandBySlave.Ip, ins.StandBySlave.Port); err != nil {
		updateErrLog := fmt.Sprintf("swap db-sqlserver role failed. err:%s", err.Error())
		ins.ReportLogs(constvar.FailResult, updateErrLog)
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "sqlserver switch update meta info success")
	return nil
}
