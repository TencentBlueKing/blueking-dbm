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
	// blackWhiteListCache 缓存黑白名单，key为cluster_name，进入GQA时一次性加载
	blackWhiteListCache map[string]bool
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
			// 每次处理实例前刷新黑白名单缓存
			gqa.refreshBlackWhiteListCache()
			instances := gqa.PreProcess(ins)
			gqa.Process(instances)
		case <-time.After(time.Duration(gqa.Conf.GMConf.ReportInterval) * time.Second):
		}

		gqa.reporter.DoReport(ModuleReportInfo{
			Module: constvar.GQA,
		})
	}
}

// refreshBlackWhiteListCache 刷新黑白名单缓存，一次性加载所有记录
func (gqa *GQA) refreshBlackWhiteListCache() {
	log.Logger.Infof("[BlackWhiteList] start refreshing black white list cache for cloud %d", gqa.Conf.GetCloudId())
	blackList, err := gqa.HaDBClient.GetAllBlackWhiteList()
	if err != nil {
		log.Logger.Warnf("[BlackWhiteList] refresh black white list cache failed: %s, will use previous cache (size=%d)",
			err.Error(), len(gqa.blackWhiteListCache))
		// 查询失败时保留上一次的缓存，如果没有缓存则初始化为空map
		if gqa.blackWhiteListCache == nil {
			gqa.blackWhiteListCache = make(map[string]bool)
		}
		return
	}
	prevSize := len(gqa.blackWhiteListCache)
	gqa.blackWhiteListCache = blackList
	log.Logger.Infof("[BlackWhiteList] refreshed cache successfully, previous=%d entries, current=%d entries",
		prevSize, len(blackList))
	// 打印缓存中的集群列表，方便排查
	if len(blackList) > 0 {
		clusters := make([]string, 0, len(blackList))
		for cluster := range blackList {
			clusters = append(clusters, cluster)
		}
		log.Logger.Infof("[BlackWhiteList] cached clusters: %v", clusters)
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

	// 检查黑白名单：如果集群在v2白名单中（switch_version=v2且status=enabled），
	// 则v1跳过切换，由v2负责处理。通过GQACheckKey标记不允许切换的实例。
	gqa.CheckBlackWhiteList(cmdbInfos)

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
			//master all standby slave satisfy switch
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

// CheckBlackWhiteList 检查黑白名单，判断同一IP下所有实例的黑白名单一致性
// 使用预加载的缓存进行判断，避免逐个集群发起网络请求
//
// 整机一致性要求：
// 1. 都在黑名单 —— 所有实例标记GQACheckKey，跳过切换（由dbha-v2负责）
// 2. 都不在黑名单 —— 正常切换，不做任何标记
// 3. 部分在部分不在 —— 配置异常，所有实例标记GQACheckKey，报错跳过切换
func (gqa *GQA) CheckBlackWhiteList(instances []dbutil.DataBaseSwitch) {
	if len(instances) == 0 {
		return
	}

	// 取第一个实例的IP用于日志
	ip, _ := instances[0].GetAddress()
	log.Logger.Infof("[BlackWhiteList] start checking %d instances on ip[%s], cache size=%d",
		len(instances), ip, len(gqa.blackWhiteListCache))

	// 统计在黑名单中和不在黑名单中的实例
	var inBlackList []dbutil.DataBaseSwitch
	var notInBlackList []dbutil.DataBaseSwitch

	for _, instance := range instances {
		clusterName := instance.GetCluster()
		_, port := instance.GetAddress()
		if gqa.blackWhiteListCache[clusterName] {
			log.Logger.Infof("[BlackWhiteList] instance ip[%s] port[%d] cluster[%s] MATCHED in black white list",
				ip, port, clusterName)
			inBlackList = append(inBlackList, instance)
		} else {
			log.Logger.Infof("[BlackWhiteList] instance ip[%s] port[%d] cluster[%s] NOT in black white list",
				ip, port, clusterName)
			notInBlackList = append(notInBlackList, instance)
		}
	}

	log.Logger.Infof("[BlackWhiteList] check result on ip[%s]: inBlackList=%d, notInBlackList=%d",
		ip, len(inBlackList), len(notInBlackList))

	// 全部不在黑名单中，正常切换，不做任何标记
	if len(inBlackList) == 0 {
		log.Logger.Infof("[BlackWhiteList] all instances on ip[%s] not in black list, proceed with normal switch", ip)
		return
	}

	// 全部在黑名单中，标记所有实例跳过切换
	if len(notInBlackList) == 0 {
		log.Logger.Infof("[BlackWhiteList] skip all instances on ip[%s]: all %d clusters managed by dbha-v2",
			ip, len(inBlackList))
		for _, instance := range inBlackList {
			instIp, instPort := instance.GetAddress()
			log.Logger.Infof("[BlackWhiteList] marking instance ip[%s] port[%d] cluster[%s] to skip switch (managed by dbha-v2)",
				instIp, instPort, instance.GetCluster())
			gqa.HaDBClient.ReportHaLogRough(gqa.Conf.GMConf.LocalIP, instance.GetApp(), instIp, instPort,
				"gqa", fmt.Sprintf("[BlackWhiteList] cluster[%s] is in v2 white list, managed by dbha-v2, skip v1 switch",
					instance.GetCluster()))
			instance.SetInfo(constvar.GQACheckKey,
				fmt.Errorf("cluster[%s] is in v2 white list, managed by dbha-v2, skip switch",
					instance.GetCluster()))
		}
		return
	}

	// 部分在黑名单、部分不在，配置不一致，标记所有实例报错跳过切换
	inconsistentMsg := fmt.Sprintf("[BlackWhiteList] config inconsistent on ip[%s]: "+
		"%d instances in black list, %d instances not in black list, skip whole host switch",
		ip, len(inBlackList), len(notInBlackList))
	log.Logger.Errorf(inconsistentMsg)

	for _, instance := range inBlackList {
		instIp, instPort := instance.GetAddress()
		log.Logger.Errorf("[BlackWhiteList] inconsistent - instance ip[%s] port[%d] cluster[%s] IN black list",
			instIp, instPort, instance.GetCluster())
		gqa.HaDBClient.ReportHaLogRough(gqa.Conf.GMConf.LocalIP, instance.GetApp(), instIp, instPort,
			"gqa", fmt.Sprintf("[BlackWhiteList] cluster[%s] in v2 white list, but other clusters on same ip[%s] NOT in list, "+
				"config inconsistent, skip whole host switch", instance.GetCluster(), ip))
		instance.SetInfo(constvar.GQACheckKey,
			fmt.Errorf("cluster[%s] in v2 white list, but other clusters on same ip[%s] NOT in list, "+
				"config inconsistent, skip whole host switch", instance.GetCluster(), ip))
	}
	for _, instance := range notInBlackList {
		instIp, instPort := instance.GetAddress()
		log.Logger.Errorf("[BlackWhiteList] inconsistent - instance ip[%s] port[%d] cluster[%s] NOT IN black list",
			instIp, instPort, instance.GetCluster())
		gqa.HaDBClient.ReportHaLogRough(gqa.Conf.GMConf.LocalIP, instance.GetApp(), instIp, instPort,
			"gqa", fmt.Sprintf("[BlackWhiteList] cluster[%s] NOT in v2 white list, but other clusters on same ip[%s] ARE in list, "+
				"config inconsistent, skip whole host switch", instance.GetCluster(), ip))
		instance.SetInfo(constvar.GQACheckKey,
			fmt.Errorf("cluster[%s] NOT in v2 white list, but other clusters on same ip[%s] ARE in list, "+
				"config inconsistent, skip whole host switch", instance.GetCluster(), ip))
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
