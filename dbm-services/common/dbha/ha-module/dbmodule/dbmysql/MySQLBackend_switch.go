package dbmysql

import (
	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"fmt"
)

// MySQLSwitch defined mysql switch struct
type MySQLSwitch struct {
	MySQLCommonSwitch
	//proxy layer instance used(spider, proxy)
	AdminPort int
	//storage layer instance used
	Proxy  []dbutil.ProxyInfo
	Dumper []dbutil.DumperInfo
}

// ShowSwitchInstanceInfo show mysql instance's switch info
func (ins *MySQLSwitch) ShowSwitchInstanceInfo() string {
	str := fmt.Sprintf("<%s#%d IDC:%d Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IdcID, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)
	//TODO right way to check empty?
	if ins.StandBySlave != (dbutil.SlaveInfo{}) {
		str = fmt.Sprintf("%s Switch from MASTER:<%s#%d> to SLAVE:<%s#%d>",
			str, ins.Ip, ins.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port)
	}
	return str
}

// CheckSwitch check slave before switch
func (ins *MySQLSwitch) CheckSwitch() (bool, error) {
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
		err = ins.CheckSlaveStatus()
		if err != nil {
			ins.ReportLogs(constvar.FailResult, err.Error())
			return false, err
		}

		log.Logger.Infof("start to switch. info{%s}", ins.ShowSwitchInstanceInfo())

		if len(ins.Proxy) == 0 {
			// available instance usual without proxy
			log.Logger.Infof("without proxy! info:{%s}", ins.ShowSwitchInstanceInfo())
			ins.ReportLogs(constvar.InfoResult, "without proxy!")
			return false, nil
		}
	} else {
		err = fmt.Errorf("info:{%s} unknown role", ins.ShowSwitchInstanceInfo())
		log.Logger.Error(err)
		ins.ReportLogs(constvar.FailResult, "instance unknown role")
		return false, err
	}

	ins.ReportLogs(constvar.InfoResult, "db-mysql check switch ok")
	return true, nil
}

// DoSwitch do switch from master to slave
//  1. refresh all proxy's backend to 1.1.1.1
//  2. reset slave
//  3. get slave's consistent binlog pos
//  4. refresh backend to alive(slave) mysql
func (ins *MySQLSwitch) DoSwitch() error {
	successFlag := true
	proxyUser := ins.Config.DBConf.MySQL.ProxyUser
	proxyPass := ins.Config.DBConf.MySQL.ProxyPass
	ins.ReportLogs(constvar.InfoResult, "one phase:update all proxy's backend to 1.1.1.1 first")
	for _, proxyIns := range ins.Proxy {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to flush proxy:[%s:%d]'s backends to 1.1.1.1",
			proxyIns.Ip, proxyIns.Port))
		err := SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, proxyUser,
			proxyPass, "1.1.1.1", 3306)
		if err != nil {
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("flush proxy's backend failed: %s", err.Error()))
			return fmt.Errorf("flush proxy's backend to 1.1.1.1 failed")
		}
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("flush proxy:[%s:%d]'s backends to 1.1.1.1 success",
			proxyIns.Ip, proxyIns.Port))
	}
	ins.ReportLogs(constvar.InfoResult, "all proxy flush backends to 1.1.1.1 success")

	ins.ReportLogs(constvar.InfoResult, "try to reset slave")
	binlogFile, binlogPosition, err := ins.ResetSlave()
	if err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("reset slave failed:%s", err.Error()))
		return fmt.Errorf("reset slave failed")
	}
	ins.StandBySlave.BinlogFile = binlogFile
	ins.StandBySlave.BinlogPosition = binlogPosition
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("reset slave success, consistent binlog info:%s,%s",
		ins.StandBySlave.BinlogFile, ins.StandBySlave.BinlogPosition))

	ins.ReportLogs(constvar.InfoResult, "two phase: update all proxy's backend to new master")
	for _, proxyIns := range ins.Proxy {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to flush proxy[%s:%d]'s backend to [%s:%d]",
			proxyIns.Ip, proxyIns.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port))
		err = SwitchProxyBackendAddress(proxyIns.Ip, proxyIns.AdminPort, proxyUser,
			proxyPass, ins.StandBySlave.Ip, ins.StandBySlave.Port)
		if err != nil {
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("flush proxy[%s:%d]'s backend to new master failed:%s",
				proxyIns.Ip, proxyIns.Port, err.Error()))
			successFlag = false
		}
		ins.ReportLogs(constvar.InfoResult, "flush proxy's backend to new master success")
	}

	if !successFlag {
		return fmt.Errorf("not all proxy's backend switch to new master")
	}

	ins.ReportLogs(constvar.InfoResult, "all proxy flush backends to new master success")
	return nil
}

// RollBack do switch rollback
func (ins *MySQLSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo swap master, slave 's meta info in cmdb
func (ins *MySQLSwitch) UpdateMetaInfo() error {
	cmdbClient := client.NewCmDBClient(&ins.Config.DBConf.CMDB, ins.Config.GetCloudId())
	if err := cmdbClient.SwapMySQLRole(ins.Ip, ins.Port,
		ins.StandBySlave.Ip, ins.StandBySlave.Port); err != nil {
		updateErrLog := fmt.Sprintf("swap db-mysql role failed. err:%s", err.Error())
		ins.ReportLogs(constvar.FailResult, updateErrLog)
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "mysql switch update meta info success")
	return nil
}

// DoFinal after switch done, check whether to do dumper switch
func (ins *MySQLSwitch) DoFinal() error {
	ins.ReportLogs(constvar.InfoResult, "mysql switch do final")
	log.Logger.Debugf("final switch detail info:%#v", ins)
	if ins.Role == constvar.TenDBStorageMaster && len(ins.Dumper) > 0 {
		//all dumper under this master need to do switch with same position
		ins.ReportLogs(constvar.InfoResult, "begin to switch tbinlogdumper")
		dumperSwitchInfo := []client.SlaveInfo{}
		for _, dumper := range ins.Dumper {
			dumperSwitchInfo = append(dumperSwitchInfo, client.SlaveInfo{
				Ip:             dumper.Ip,
				Port:           dumper.Port,
				BinlogFile:     ins.StandBySlave.BinlogFile,
				BinlogPosition: ins.StandBySlave.BinlogPosition,
			})
		}

		switchInfos := []client.DumperSwitchInfo{
			{
				ClusterDomain:   ins.Cluster,
				SwitchInstances: dumperSwitchInfo,
			},
		}
		cmdbClient := client.NewCmDBClient(&ins.Config.DBConf.CMDB, ins.Config.GetCloudId())
		if err := cmdbClient.DoDumperSwitch(ins.App, switchInfos); err != nil {

		}
		ins.ReportLogs(constvar.InfoResult, "call api do dumper migrate success")
	}

	return nil
}
