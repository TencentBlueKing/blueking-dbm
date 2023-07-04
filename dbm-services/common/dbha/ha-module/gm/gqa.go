package gm

import (
	"fmt"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbmodule"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// GQA work struct
type GQA struct {
	GMMChan              chan DoubleCheckInstanceInfo
	GCMChan              chan dbutil.DataBaseSwitch
	CmDBClient           *client.CmDBClient
	HaDBClient           *client.HaDBClient
	gdm                  *GDM
	Conf                 *config.Config
	IDCCache             map[string]time.Time
	IDCCacheExpire       int
	SingleSwitchInterval int
	SingleSwitchLimit    int
	AllSwitchInterval    int
	AllSwitchLimit       int
	SingleSwitchIDCLimit int
	reporter             *HAReporter
}

// NewGQA init GQA object
func NewGQA(gdm *GDM, conf *config.Config,
	gmmCh chan DoubleCheckInstanceInfo,
	gcmCh chan dbutil.DataBaseSwitch, reporter *HAReporter) (*GQA, error) {
	var err error
	gqa := &GQA{
		GMMChan:              gmmCh,
		GCMChan:              gcmCh,
		gdm:                  gdm,
		Conf:                 conf,
		IDCCache:             map[string]time.Time{},
		IDCCacheExpire:       conf.GMConf.GQA.IDCCacheExpire,
		SingleSwitchInterval: conf.GMConf.GQA.SingleSwitchInterval,
		SingleSwitchLimit:    conf.GMConf.GQA.SingleSwitchLimit,
		AllSwitchInterval:    conf.GMConf.GQA.AllSwitchInterval,
		AllSwitchLimit:       conf.GMConf.GQA.AllHostSwitchLimit,
		SingleSwitchIDCLimit: conf.GMConf.GQA.SingleSwitchIDC,
		reporter:             reporter,
	}
	gqa.CmDBClient, err = client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId())
	if err != nil {
		return nil, err
	}
	gqa.HaDBClient, err = client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId())
	if err != nil {
		return nil, err
	}
	return gqa, nil
}

// Run GQA main entry
func (gqa *GQA) Run() {
	for {
		select {
		case ins := <-gqa.GMMChan:
			instances := gqa.PreProcess(ins)
			gqa.Process(instances)
		case <-time.After(time.Duration(gqa.Conf.GMConf.ReportInterval) * time.Second):
		}

		gqa.reporter.DoReport(ModuleReportInfo{
			Module: constvar.GQA,
		})
	}
}

// PopInstance pop instance from gmm
func (gqa *GQA) PopInstance() []dbutil.DataBaseSwitch {
	instance := <-gqa.GMMChan
	return gqa.PreProcess(instance)
}

// PreProcess fetch instance detail info for process
func (gqa *GQA) PreProcess(instance DoubleCheckInstanceInfo) []dbutil.DataBaseSwitch {
	ip, port := instance.db.GetAddress()
	log.Logger.Infof("gqa get instance. ip:%s, port:%d", ip, port)

	cmdbInfos, err := gqa.getAllInstanceFromCMDB(&instance)
	if err != nil {
		errInfo := fmt.Sprintf("get idc failed. err:%s", err.Error())
		log.Logger.Errorf(errInfo)
		gqa.HaDBClient.ReportHaLog(ip, port, "gqa", errInfo)
		return nil
	}
	return cmdbInfos
}

// PushInstance2Next push instance to gcm chan
func (gqa *GQA) PushInstance2Next(ins dbutil.DataBaseSwitch) {
	gqa.GCMChan <- ins
	return
}

// Process decide whether instance allow next switch
func (gqa *GQA) Process(cmdbInfos []dbutil.DataBaseSwitch) {
	if nil == cmdbInfos {
		return
	}

	for _, instanceInfo := range cmdbInfos {
		ip, port := instanceInfo.GetAddress()
		log.Logger.Infof("gqa handle instance. ip:%s, port:%d", ip, port)

		// check single IDC
		lastCacheTime, ok := gqa.IDCCache[instanceInfo.GetIDC()]
		if ok {
			if time.Now().After(lastCacheTime.Add(time.Duration(gqa.IDCCacheExpire) * time.Second)) {
				delete(gqa.IDCCache, instanceInfo.GetIDC())
			} else {
				err := gqa.delaySwitch(instanceInfo)
				if err != nil {
					errInfo := fmt.Sprintf("delay switch failed. err:%s", err.Error())
					log.Logger.Errorf(errInfo)
					gqa.HaDBClient.ReportHaLog(ip, port, "gqa", errInfo)
				} else {
					gqa.HaDBClient.ReportHaLog(ip, port, "gqa",
						"single IDC switch too much, delay switch")
				}
				continue
			}
		}

		// check status
		if instanceInfo.GetStatus() != constvar.RUNNING && instanceInfo.GetStatus() != constvar.AVAILABLE {
			gqa.HaDBClient.ReportHaLog(ip, port, "gqa",
				fmt.Sprintf("status:%s not equal RUNNING or AVAILABLE", instanceInfo.GetStatus()))
			continue
		}

		// query single instance total
		singleTotal, err := gqa.HaDBClient.QuerySingleTotal(ip, port, gqa.SingleSwitchInterval)
		if err != nil {
			errInfo := fmt.Sprintf("query single total failed. err:%s", err.Error())
			log.Logger.Errorf(errInfo)
			gqa.HaDBClient.ReportHaLog(ip, port, "gqa", errInfo)
			continue
		}
		if singleTotal >= gqa.SingleSwitchLimit {
			gqa.HaDBClient.ReportHaLog(ip, port, "gqa", "reached single total.")
			continue
		}

		// query all machines max total
		intervalTotal, err := gqa.HaDBClient.QueryIntervalTotal(gqa.AllSwitchInterval)
		if err != nil {
			errInfo := fmt.Sprintf("query interval total failed. err:%s", err.Error())
			log.Logger.Errorf(errInfo)
			gqa.HaDBClient.ReportHaLog(ip, port, "gqa", errInfo)
			continue
		}
		if intervalTotal >= gqa.AllSwitchLimit {
			err = gqa.delaySwitch(instanceInfo)
			if err != nil {
				errInfo := fmt.Sprintf("delay switch failed. err:%s", err.Error())
				log.Logger.Errorf(errInfo)
				gqa.HaDBClient.ReportHaLog(ip, port, "gqa", errInfo)
			} else {
				gqa.HaDBClient.ReportHaLog(ip, port, "gqa",
					"dbha switch too much, delay switch")
			}
			continue
		}

		// query job doing(machine)

		// query single idc(machine) in 1 minute
		idcTotal, err := gqa.HaDBClient.QuerySingleIDC(ip, instanceInfo.GetIDC())
		if err != nil {
			errInfo := fmt.Sprintf("query single idc failed. err:%s", err.Error())
			log.Logger.Errorf(errInfo)
			gqa.HaDBClient.ReportHaLog(ip, port, "gqa", errInfo)
			continue
		}
		if idcTotal >= gqa.SingleSwitchIDCLimit {
			_, ok = gqa.IDCCache[instanceInfo.GetIDC()]
			if !ok {
				gqa.IDCCache[instanceInfo.GetIDC()] = time.Now()
			}
			err = gqa.delaySwitch(instanceInfo)
			if err != nil {
				errInfo := fmt.Sprintf("delay switch failed. err:%s", err.Error())
				log.Logger.Errorf(errInfo)
				gqa.HaDBClient.ReportHaLog(ip, port, "gqa", errInfo)
			} else {
				gqa.HaDBClient.ReportHaLog(ip, port, "gqa",
					"single IDC switch too much, delay switch")
			}
			continue
		}

		// query instance and proxy info

		log.Logger.Infof("start switch. ip:%s, port:%d, cluster_Type:%s, app:%s",
			ip, port, instanceInfo.GetClusterType(), instanceInfo.GetApp())
		gqa.PushInstance2Next(instanceInfo)
	}
}

func (gqa *GQA) getAllInstanceFromCMDB(
	instance *DoubleCheckInstanceInfo) ([]dbutil.DataBaseSwitch, error) {
	ip, _ := instance.db.GetAddress()
	instances, err := gqa.CmDBClient.GetDBInstanceInfoByIp(ip)
	if err != nil {
		log.Logger.Errorf("get mysql instance failed. err:%s", err.Error())
		return nil, err
	}

	if nil == instances {
		log.Logger.Errorf("gqa get mysql instances nil")
	} else {
		log.Logger.Infof("gqa get mysql instance number:%d", len(instances))
	}

	cb, ok := dbmodule.DBCallbackMap[instance.db.GetType()]
	if !ok {
		err = fmt.Errorf("can't find %s instance callback", instance.db.GetType())
		log.Logger.Errorf(err.Error())
		return nil, err
	}
	ret, err := cb.GetSwitchInstanceInformation(instances, gqa.Conf)
	if err != nil {
		log.Logger.Errorf("get switch instance info failed. err:%s", err.Error())
		return nil, err
	}

	if ret == nil {
		log.Logger.Errorf("gqa get switch instance is nil")
	} else {
		log.Logger.Errorf("gqa get switch instance num:%d", len(ret))
	}

	for _, sins := range ret {
		sins.SetInfo(constvar.SwitchInfoDoubleCheck, instance.ResultInfo)
	}
	return ret, nil
}

func (gqa *GQA) delaySwitch(instance dbutil.DataBaseSwitch) error {
	ip, port := instance.GetAddress()
	log.Logger.Infof("start delay switch. ip:%s, port:%d, app:%s",
		ip, port, instance.GetApp())
	// err := gqa.HaDBClient.UpdateTimeDelay(instance.Ip, instance.Port, instance.App)
	// if err != nil {
	// 	log.Logger.Errorf("update timedelay failed. err:%s", err.Error())
	// 	return err
	// }
	gqa.gdm.InstanceSwitchDone(ip, port, instance.GetClusterType())
	return nil
}
