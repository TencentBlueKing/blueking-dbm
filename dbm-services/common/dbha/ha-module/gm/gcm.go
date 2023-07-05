package gm

import (
	"fmt"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/monitor"
)

// GCM gcm work struct
type GCM struct {
	GQAChan                  chan dbutil.DataBaseSwitch
	CmDBClient               *client.CmDBClient
	HaDBClient               *client.HaDBClient
	Conf                     *config.Config
	AllowedChecksumMaxOffset int
	AllowedSlaveDelayMax     int
	AllowedTimeDelayMax      int
	ExecSlowKBytes           int
	reporter                 *HAReporter
}

// NewGCM init new gcm
func NewGCM(conf *config.Config, ch chan dbutil.DataBaseSwitch, reporter *HAReporter) (*GCM, error) {
	var err error
	gcm := &GCM{
		GQAChan:                  ch,
		Conf:                     conf,
		AllowedChecksumMaxOffset: conf.GMConf.GCM.AllowedChecksumMaxOffset,
		AllowedTimeDelayMax:      conf.GMConf.GCM.AllowedTimeDelayMax,
		AllowedSlaveDelayMax:     conf.GMConf.GCM.AllowedSlaveDelayMax,
		ExecSlowKBytes:           conf.GMConf.GCM.ExecSlowKBytes,
		reporter:                 reporter,
	}
	gcm.CmDBClient, err = client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
	if err != nil {
		return nil, err
	}
	gcm.HaDBClient, err = client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())
	if err != nil {
		return nil, err
	}
	return gcm, nil
}

// Run gcm run main entry
func (gcm *GCM) Run() {
	for {
		select {
		case ins := <-gcm.GQAChan:
			gcm.Process(ins)
		case <-time.After(time.Duration(gcm.Conf.GMConf.ReportInterval) * time.Second):
		}
		gcm.reporter.DoReport(ModuleReportInfo{
			Module: constvar.GCM,
		})
	}
}

// PopInstance pop instance from GQA chan
func (gcm *GCM) PopInstance() dbutil.DataBaseSwitch {
	switchInstance := <-gcm.GQAChan
	return switchInstance
}

// Process gcm process instance switch
func (gcm *GCM) Process(switchInstance dbutil.DataBaseSwitch) {
	go func(switchInstance dbutil.DataBaseSwitch) {
		gcm.DoSwitchSingle(switchInstance)
	}(switchInstance)
}

// DoSwitchSingle gcm do instance switch
func (gcm *GCM) DoSwitchSingle(switchInstance dbutil.DataBaseSwitch) {
	var err error

	// 这里先将实例获取锁设为unavailable，再插入switch_queue。原因是如果先插switch_queue，如果其他gm同时更新，则会有多条
	// switch_queue记录，则更新switch_queue会同时更新多条记录，因为我们没有无法区分哪条记录是哪个gm插入的
	log.Logger.Infof("get instance lock and set unavailable")
	err = gcm.SetUnavailableAndLockInstance(switchInstance)
	if err != nil {
		switchFail := "set instance to unavailable failed:" + err.Error()
		switchInstance.ReportLogs(constvar.SwitchFail, switchFail)
		monitor.MonitorSendSwitch(switchInstance, switchFail, false)
		return
	}

	log.Logger.Infof("insert tb_mon_switch_queue. info:{%s}", switchInstance.ShowSwitchInstanceInfo())
	err = gcm.InsertSwitchQueue(switchInstance)
	if err != nil {
		log.Logger.Errorf("insert switch queue failed. err:%s, info{%s}", err.Error(),
			switchInstance.ShowSwitchInstanceInfo())
		switchFail := "insert switch queue failed. err:" + err.Error()
		monitor.MonitorSendSwitch(switchInstance, switchFail, false)
		return
	}
	switchInstance.ReportLogs(constvar.CheckSwitchInfo, "set instance unavailable success")

	for i := 0; i < 1; i++ {
		switchInstance.ReportLogs(constvar.CheckSwitchInfo, "start check switch")

		var needContinue bool
		needContinue, err = switchInstance.CheckSwitch()

		if err != nil {
			log.Logger.Errorf("check switch failed. err:%s, info{%s}", err.Error(),
				switchInstance.ShowSwitchInstanceInfo())
			err = fmt.Errorf("check switch failed:%s", err.Error())
			break
		}

		if !needContinue {
			break
		}

		switchInstance.ReportLogs(constvar.SwitchInfo, "start do switch")
		err = switchInstance.DoSwitch()
		if err != nil {
			log.Logger.Errorf("do switch failed. err:%s, info{%s}", err.Error(),
				switchInstance.ShowSwitchInstanceInfo())
			err = fmt.Errorf("do switch failed:%s", err.Error())
			break
		}
		switchInstance.ReportLogs(constvar.SwitchInfo, "do switch success. try to update meta info")

		log.Logger.Infof("do update meta info. info{%s}", switchInstance.ShowSwitchInstanceInfo())
		err = switchInstance.UpdateMetaInfo()
		if err != nil {
			log.Logger.Errorf("do update meta info failed. err:%s, info{%s}", err.Error(),
				switchInstance.ShowSwitchInstanceInfo())
			err = fmt.Errorf("do update meta info failed:%s", err.Error())
			break
		}
		switchInstance.ReportLogs(constvar.SwitchInfo, "update meta info success")
	}
	if err != nil {
		monitor.MonitorSendSwitch(switchInstance, err.Error(), false)
		log.Logger.Errorf("switch instance failed. info:{%s}", switchInstance.ShowSwitchInstanceInfo())

		updateErr := gcm.UpdateSwitchQueue(switchInstance, err.Error(), constvar.SwitchFail)
		if updateErr != nil {
			log.Logger.Errorf("update switch queue failed. err:%s, info{%s}", updateErr.Error(),
				switchInstance.ShowSwitchInstanceInfo())
		}
		gcm.InsertSwitchLogs(switchInstance, false, err.Error())

		rollbackErr := switchInstance.RollBack()
		if rollbackErr != nil {
			log.Logger.Errorf("instance rollback failed. err:%s, info{%s}", rollbackErr.Error(),
				switchInstance.ShowSwitchInstanceInfo())
		}
	} else {
		log.Logger.Infof("switch instance success. info:{%s}", switchInstance.ShowSwitchInstanceInfo())
		switchOk := "switch success"
		monitor.MonitorSendSwitch(switchInstance, switchOk, true)
		gcm.InsertSwitchLogs(switchInstance, true, switchOk)

		updateErr := gcm.UpdateSwitchQueue(switchInstance, "switch_done", constvar.SwitchSucc)
		if updateErr != nil {
			log.Logger.Errorf("update Switch queue failed. err:%s", updateErr.Error())
			return
		}
	}
}

// InsertSwitchQueue insert switch info to tb_mon_switch_queue
func (gcm *GCM) InsertSwitchQueue(instance dbutil.DataBaseSwitch) error {
	ip, port := instance.GetAddress()
	uid, err := gcm.HaDBClient.InsertSwitchQueue(
		ip, port, instance.GetIDC(), time.Now(), instance.GetApp(),
		instance.GetClusterType(), instance.GetCluster(),
	)
	if err != nil {
		log.Logger.Errorf("insert switch queue failed. err:%s", err.Error())
		return err
	}
	instance.SetSwitchUid(uid)
	return nil
}

// InsertSwitchLogs insert switch logs to switchLogs table
func (gcm *GCM) InsertSwitchLogs(instance dbutil.DataBaseSwitch, result bool, resultInfo string) {
	var resultDetail string
	var comment string
	curr := time.Now()
	info := instance.ShowSwitchInstanceInfo()
	if result {
		resultDetail = constvar.SwitchSucc
		comment = fmt.Sprintf("%s %s success", curr.Format("2006-01-02 15:04:05"), info)
	} else {
		resultDetail = constvar.SwitchFail
		comment = fmt.Sprintf(
			"%s %s failed,err:%s", curr.Format("2006-01-02 15:04:05"), info, resultInfo,
		)
	}

	ip, port := instance.GetAddress()
	err := gcm.HaDBClient.InsertSwitchLog(
		instance.GetSwitchUid(), ip, port, resultDetail, comment, time.Now(),
	)
	if err != nil {
		log.Logger.Errorf("insert switch logs failed. err:%s", err.Error())
	}
}

// SetUnavailableAndLockInstance update instance status to unavailable
func (gcm *GCM) SetUnavailableAndLockInstance(instance dbutil.DataBaseSwitch) error {
	// no lock
	ip, port := instance.GetAddress()
	err := gcm.CmDBClient.UpdateDBStatus(ip, port, constvar.UNAVAILABLE)
	if err != nil {
		log.Logger.Errorf("set instance unavailable failed. err:%s", err.Error())
		return err
	}
	return nil
}

// UpdateSwitchQueue update switch result
func (gcm *GCM) UpdateSwitchQueue(instance dbutil.DataBaseSwitch, confirmResult string, switchResult string) error {
	var (
		confirmStr string
		slaveIp    string
		slavePort  int
	)
	if ok, dcInfo := instance.GetInfo(constvar.SwitchInfoDoubleCheck); ok {
		confirmStr = dcInfo.(string)
	} else {
		confirmStr = confirmResult
	}

	if ok, slaveIpInfo := instance.GetInfo(constvar.SwitchInfoSlaveIp); ok {
		slaveIp = slaveIpInfo.(string)
	} else {
		slaveIp = "N/A"
	}

	if ok, slavePortInfo := instance.GetInfo(constvar.SwitchInfoSlavePort); ok {
		slavePort = slavePortInfo.(int)
	} else {
		slavePort = 0
	}

	ip, port := instance.GetAddress()
	if err := gcm.HaDBClient.UpdateSwitchQueue(
		instance.GetSwitchUid(), ip, port,
		constvar.UNAVAILABLE,
		slaveIp,
		slavePort,
		confirmStr,
		switchResult,
		instance.GetRole(),
	); err != nil {
		log.Logger.Errorf("update switch queue failed. err:%s", err.Error())
		return err
	}
	return nil
}
