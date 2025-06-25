package gm

import (
	"dbm-services/common/dbha/ha-module/util"
	"dbm-services/common/dbha/hadb-api/model"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbmodule"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/monitor"
)

// GQA work struct
type GQA struct {
	GMMChan              chan DoubleCheckInstanceInfo
	GCMChan              chan dbutil.DataBaseSwitch
	CmDBClient           *client.CmDBClient
	HaDBClient           *client.HaDBClient
	gdm                  *GDM
	Conf                 *config.Config
	IDCCache             map[int]time.Time
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
	gcmCh chan dbutil.DataBaseSwitch, reporter *HAReporter) *GQA {
	return &GQA{
		GMMChan:              gmmCh,
		GCMChan:              gcmCh,
		gdm:                  gdm,
		Conf:                 conf,
		IDCCache:             map[int]time.Time{},
		IDCCacheExpire:       conf.GMConf.GQA.IDCCacheExpire,
		SingleSwitchInterval: conf.GMConf.GQA.SingleSwitchInterval,
		SingleSwitchLimit:    conf.GMConf.GQA.SingleSwitchLimit,
		AllSwitchInterval:    conf.GMConf.GQA.AllSwitchInterval,
		AllSwitchLimit:       conf.GMConf.GQA.AllHostSwitchLimit,
		SingleSwitchIDCLimit: conf.GMConf.GQA.SingleSwitchIDC,
		reporter:             reporter,
		CmDBClient:           client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId()),
		HaDBClient:           client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId()),
	}
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

// PreProcess fetch instance detail info for process
func (gqa *GQA) PreProcess(instance DoubleCheckInstanceInfo) []dbutil.DataBaseSwitch {
	ip, port := instance.db.GetAddress()
	log.Logger.Infof("gqa get instance. ip:%s, port:%d", ip, port)

	cmdbInfos, err := gqa.getAllInstanceFromCMDB(&instance)
	if err != nil {
		errInfo := fmt.Sprintf("get idc failed. err:%s", err.Error())
		log.Logger.Errorf(errInfo)
		gqa.HaDBClient.ReportHaLogRough(gqa.Conf.GMConf.LocalIP, instance.db.GetApp(), ip, port, "gqa", errInfo)
		return nil
	}
	if len(cmdbInfos) == 0 {
		log.Logger.Debugf("gqa get instance nil")
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
	if len(cmdbInfos) == 0 {
		log.Logger.Debugf("no instance needed to process, skip")
		return
	}

	var (
		masterCheckFailed atomic.Bool
		checkResults      sync.Map
		masterWg          sync.WaitGroup
	)

	log.Logger.Debugf("gqa process instance")
	for _, instance := range cmdbInfos {
		log.Logger.Infof("insert ha_switch_queue. info:{%s}", instance.ShowSwitchInstanceInfo())
		err := gqa.InsertSwitchQueue(instance)
		if err != nil {
			switchFail := "insert switch queue failed. err:" + err.Error()
			log.Logger.Errorf("%s, info{%s}", err.Error(), instance.ShowSwitchInstanceInfo())
			monitor.MonitorSendSwitch(instance, switchFail, false)
			return
		}

		if instance.GetRole() == constvar.TenDBClusterStorageMaster {
			masterWg.Add(1)
			go func(ins dbutil.DataBaseSwitch) {
				defer masterWg.Done()
				ip, port := ins.GetAddress()
				log.Logger.Infof("gqa check tendbcluster storage. ip:%s, port:%d", ip, port)
				ok, err := ins.CheckSwitch()
				if !ok {
					checkResults.Store(ins, err)
					gqa.HaDBClient.ReportHaLogRough(gqa.Conf.GMConf.LocalIP, instance.GetApp(), ip, port,
						"gqa", err.Error())
					masterCheckFailed.Store(true)
				}
			}(instance)
		}
	}
	masterWg.Wait()

	failed := masterCheckFailed.Load()
	if failed {
		log.Logger.Errorf("not all instances pre-check ok")
	}

	for _, instance := range cmdbInfos {
		ip, port := instance.GetAddress()
		if instance.GetRole() == constvar.TenDBClusterStorageMaster {
			if err, ok := checkResults.Load(instance); ok && err != nil {
				instance.SetInfo(constvar.GQACheckKey, err)
			} else if failed {
				instance.SetInfo(constvar.GQACheckKey,
					fmt.Errorf("other instances under this ip not satisfy switch"))
			}
		}

		log.Logger.Infof("gqa handle instance. ip:%s, port:%d", ip, port)
		log.Logger.Infof("start switch. ip:%s, port:%d, cluster_Type:%s, app:%s",
			ip, port, instance.GetClusterType(), instance.GetApp())
		gqa.PushInstance2Next(instance)
	}
}

func (gqa *GQA) getAllInstanceFromCMDB(
	instance *DoubleCheckInstanceInfo) ([]dbutil.DataBaseSwitch, error) {
	ip, _ := instance.db.GetAddress()
	instances, err := gqa.CmDBClient.GetDBInstanceInfoByIp(ip)
	if err != nil {
		minInfo := monitor.GetApiAlertInfo(constvar.CmDBInstanceUrl, err.Error())
		if e := monitor.MonitorSend("get instances failed", minInfo); e != nil {
			log.Logger.Warnf(e.Error())
		}
		log.Logger.Errorf("get mysql instance failed. err:%s", err.Error())
		return nil, err
	}

	if nil == instances {
		log.Logger.Errorf("gqa get mysql instances nil")
	} else {
		log.Logger.Infof("gqa get mysql instance number:%d", len(instances))
	}

	cb, ok := dbmodule.DBCallbackMap[instance.db.GetDetectType()]
	if !ok {
		err = fmt.Errorf("can't find %s instance callback", instance.db.GetDetectType())
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
		log.Logger.Infof("gqa get switch instance num:%d", len(ret))
	}
	log.Logger.Errorf("need process instances detail:%#v", ret)

	for _, sins := range ret {
		sins.SetDoubleCheckId(instance.CheckID)
		sins.SetInfo(constvar.DoubleCheckInfoKey, instance.ResultInfo)
		sins.SetInfo(constvar.DoubleCheckTimeKey, instance.ConfirmTime)
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

// InsertSwitchQueue insert switch info to ha_switch_queue
func (gqa *GQA) InsertSwitchQueue(instance dbutil.DataBaseSwitch) error {
	log.Logger.Debugf("switch instance info:%#v", instance)
	ip, port := instance.GetAddress()
	confirmTime := time.Now()
	if ok, value := instance.GetInfo(constvar.DoubleCheckTimeKey); ok {
		if t, ok := value.(time.Time); ok {
			confirmTime = t
		}
	}
	doubleCheckInfo := "unknown"
	if ok, value := instance.GetInfo(constvar.DoubleCheckInfoKey); ok {
		doubleCheckInfo = value.(string)
	}

	currentTime := time.Now()
	req := &client.SwitchQueueRequest{
		DBCloudToken: gqa.Conf.DBConf.HADB.BKConf.BkToken,
		BKCloudID:    gqa.Conf.GetCloudId(),
		Name:         constvar.InsertSwitchQueue,
		SetArgs: &model.HASwitchQueue{
			CheckID:          instance.GetDoubleCheckId(),
			IP:               ip,
			Port:             port,
			IdcID:            instance.GetIdcID(),
			App:              instance.GetApp(),
			ConfirmCheckTime: &confirmTime,
			DbType:           instance.GetMetaType(),
			CloudID:          gqa.Conf.GetCloudId(),
			Cluster:          instance.GetCluster(),
			Status:           constvar.SwitchStart,
			SwitchStartTime:  &currentTime,
			DbRole:           instance.GetRole(),
			ConfirmResult:    doubleCheckInfo,
			SwitchHashID: util.GenerateHash(fmt.Sprintf("%#%d", ip, port),
				int64(max(300, gqa.Conf.GMConf.ReportInterval))),
		},
	}

	uid, err := gqa.HaDBClient.InsertSwitchQueue(req)
	if err != nil {
		log.Logger.Errorf("insert switch queue failed. err:%s", err.Error())
		return err
	}
	instance.SetSwitchUid(uid)
	return nil
}
