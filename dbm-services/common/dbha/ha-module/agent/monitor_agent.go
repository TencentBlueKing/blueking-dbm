package agent

import (
	"dbm-services/common/dbha/hadb-api/model"
	"fmt"
	"net"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbmodule"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/monitor"
	"dbm-services/common/dbha/ha-module/util"
)

// MonitorAgent agent work struct
type MonitorAgent struct {
	CityID int
	Campus string
	//detect dbType
	DetectType string
	// agent ip
	MonIp            string
	LastFetchInsTime time.Time
	LastFetchGMTime  time.Time
	DBInstance       map[string]dbutil.DataBaseDetect
	GMInstance       map[string]*GMConnection
	// config file
	Conf *config.Config
	// API client to access cmdb metadata
	CmDBClient *client.CmDBClient
	// API client to access hadb
	HaDBClient *client.HaDBClient
	heartbeat  time.Time
}

// NewMonitorAgent new a new agent do detect
func NewMonitorAgent(conf *config.Config, detectType string) (*MonitorAgent, error) {
	var err error
	agent := &MonitorAgent{
		CityID:           conf.AgentConf.CityID,
		Campus:           conf.AgentConf.Campus,
		DetectType:       detectType,
		LastFetchInsTime: time.Now(),
		LastFetchGMTime:  time.Now(),
		GMInstance:       map[string]*GMConnection{},
		heartbeat:        time.Now(),
		Conf:             conf,
		CmDBClient:       client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId()),
		HaDBClient:       client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId()),
		MonIp:            conf.AgentConf.LocalIP,
	}

	// register agent into
	err = agent.registerAgentInfoToHaDB()
	if err != nil {
		return nil, err
	}

	// fetch alive GMConf instance
	err = agent.FetchGMInstance()
	if err != nil {
		return nil, err
	}

	err = agent.FetchDBInstance()
	if err != nil {
		return nil, err
	}

	return agent, nil
}

// Process parallel detect all instances periodic. Every round completed,
// report agent's heartbeat info.
func (a *MonitorAgent) Process(instances map[string]dbutil.DataBaseDetect) {
	var wg sync.WaitGroup
	log.Logger.Debugf("need to detect instances number:%d", len(a.DBInstance))
	for _, ins := range instances {
		wg.Add(1)
		go func(ins dbutil.DataBaseDetect) {
			defer wg.Done()
			a.DoDetectSingle(ins)
		}(ins)
	}
	wg.Wait()
	a.DetectPostProcess()
	time.Sleep(time.Second)
}

// Run agent main entry
func (a *MonitorAgent) Run() error {
	for {
		a.RefreshInstanceCache()
		a.RefreshGMCache()
		a.Process(a.DBInstance)
	}
}

// RefreshInstanceCache check whether needed to re-fetch instance, gm
func (a *MonitorAgent) RefreshInstanceCache() {
	if a.NeedRefreshInsCache() {
		err := a.FetchDBInstance()
		if err != nil {
			log.Logger.Errorf("fetch %s instance failed. err:%s",
				a.DetectType, err.Error())
		}
		a.flushInsFetchTime()
	}
}

// DoDetectSingle do single instance detect
func (a *MonitorAgent) DoDetectSingle(ins dbutil.DataBaseDetect) {
	ip, port := ins.GetAddress()
	log.Logger.Debugf("begin to detect instance:%s#%d", ip, port)
	err := ins.Detection()
	if err != nil {
		log.Logger.Warnf("Detect db instance failed. ins:[%s:%d],dbType:%s status:%s,DeteckErr=%s",
			ip, port, ins.GetType(), ins.GetStatus(), err.Error())
	}

	a.reportMonitor(ins, err)
	if ins.NeedReporter() {
		// reporter detect result to hadb
		err = a.HaDBClient.ReportDBStatus(ins.GetApp(), a.MonIp, ip, port,
			string(ins.GetType()), string(ins.GetStatus()))
		if err != nil {
			log.Logger.Errorf(
				"reporter hadb instance status failed. err:%s, ip:%s, port:%d, db_type:%s, status:%s",
				err.Error(), ip, port, ins.GetType(), ins.GetStatus())
		}
		err = a.ReporterGM(ins)
		if err != nil {
			log.Logger.Errorf("reporter gm failed. err:%s", err.Error())
		}
		ins.UpdateReporterTime()
	}
}

// DetectPostProcess post agent heartbeat
func (a *MonitorAgent) DetectPostProcess() {
	err := a.reporterHeartbeat()
	if err != nil {
		log.Logger.Errorf("reporter heartbeat failed. err:%s", err.Error())
	}
	log.Logger.Infof("report agent heartbeat success.")
}

// RefreshGMCache refresh gm cache, delete expire gm
func (a *MonitorAgent) RefreshGMCache() {
	if a.NeedRefreshGMCache() {
		if err := a.FetchGMInstance(); err != nil {
			log.Logger.Errorf("fetch gm failed. err:%s", err.Error())
		}
		a.flushGmFetchTime()
	}

	for ip, ins := range a.GMInstance {
		ins.Mutex.Lock()
		anHour := time.Now().Add(-60 * time.Minute)
		// connect leak?
		if ins.LastFetchTime.Before(anHour) {
			ins.IsClose = true
			log.Logger.Infof("gm:%s de-cached", ip)
			delete(a.GMInstance, ip)
		}
		ins.Mutex.Unlock()
	}

	// we not return error here, next refresh, new added gm maybe available.
	if len(a.GMInstance) == 0 {
		log.Logger.Errorf("after refresh, no gm available")
	}
}

// FetchDBInstance fetch instance list by city info
func (a *MonitorAgent) FetchDBInstance() error {
	rawInfo, err := a.CmDBClient.GetDBInstanceInfoByCity(a.CityID)

	if err != nil {
		log.Logger.Errorf("get instance info from cmdb failed. err:%s", err.Error())
		return err
	}

	log.Logger.Debugf("get db instance number:%d", len(rawInfo))
	// get callback function by db type
	cb, ok := dbmodule.DBCallbackMap[a.DetectType]
	if !ok {
		err = fmt.Errorf("can't find fetch %s instance callback", a.DetectType)
		log.Logger.Error(err.Error())
		return err
	}
	// unmarshal instance from cmdb struct(api response) to detect struct
	AllDbInstance, err := cb.FetchDBCallback(rawInfo, a.Conf)
	if err != nil {
		log.Logger.Errorf("fetch db instance failed. err:%s", err.Error())
		return err
	}
	log.Logger.Debugf("get type[%s] instance info number:%d", a.DetectType, len(AllDbInstance))

	a.DBInstance, err = a.moduloHashSharding(AllDbInstance)
	if err != nil {
		log.Logger.Errorf("fetch module hash sharding failed. err:%s", err.Error())
		return err
	}
	log.Logger.Debugf("current agent need to detect type[%s] number:%d", a.DetectType, len(a.DBInstance))
	return nil
}

// FetchGMInstance fetch appropriate gm for current agent(different city)
func (a *MonitorAgent) FetchGMInstance() error {
	gmInfo, err := a.HaDBClient.GetAliveHAComponent(constvar.GM, a.Conf.AgentConf.FetchInterval)
	if err != nil {
		log.Logger.Errorf("get gm info failed. err:%s", err.Error())
		return err
	}

	for _, info := range gmInfo {
		if info.CityID == a.CityID || info.CloudID != a.Conf.AgentConf.CloudID {
			continue
		}
		// needn't lock
		_, ok := a.GMInstance[info.Ip]
		if ok {
			a.GMInstance[info.Ip].LastFetchTime = time.Now()
		} else {
			a.GMInstance[info.Ip] = &GMConnection{
				Ip:            info.Ip,
				Port:          info.Port,
				LastFetchTime: time.Now(),
				IsClose:       false,
			}
			err = a.GMInstance[info.Ip].Init()
			if err != nil {
				log.Logger.Errorf("init gm failed. gm_ip:%s, gm_port:%d, err:%s",
					info.Ip, info.Port, err.Error())
				return err
			}
		}
	}

	log.Logger.Infof("agent get alive gm info :%d, GmInstance:%d",
		len(gmInfo), len(a.GMInstance))
	return nil
}

// ReporterGM report detect info to gm
func (a *MonitorAgent) ReporterGM(reporterInstance dbutil.DataBaseDetect) error {
	if reporterInstance.GetStatus() == constvar.DBCheckSuccess ||
		reporterInstance.GetStatus() == constvar.SSHCheckSuccess {
		// if db is normal, needn't reporter gm
		return nil
	}
	var err error
	isReporter := false
	ip, port := reporterInstance.GetAddress()

	for _, gmIns := range a.GMInstance {
		gmIns.Mutex.Lock()
		if !gmIns.IsConnection {
			gmIns.Mutex.Unlock()
			continue
		}
		jsonInfo, err := reporterInstance.Serialization()
		if err != nil {
			gmIns.Mutex.Unlock()
			log.Logger.Errorf("instance Serialization failed. err:%s", err.Error())
			return err
		}
		err = gmIns.ReportInstance(reporterInstance.GetDetectType(), jsonInfo)
		if err != nil {
			log.Logger.Warnf("reporter gm failed. gm_ip:%s, gm_port:%d, err:%s", ip, port, err.Error())
			gmIns.IsConnection = false
			err = a.RepairGM(gmIns)
			if err != nil {
				log.Logger.Errorf("Repair gm failed:%s", err.Error())
				return err
			}
		} else {
			log.Logger.Debugf("reporter gm success. gm info:%s#%d", ip, port)
			if err = a.reporterBindGM(fmt.Sprintf("%s#%d", gmIns.Ip, gmIns.Port)); err != nil {
				log.Logger.Warnf("update agent's bind gm info failed:%s", err.Error())
			}
			isReporter = true
			gmIns.Mutex.Unlock()
			break
		}
		gmIns.Mutex.Unlock()
	}

	if !isReporter {
		err = fmt.Errorf("all gm disconnect")
		log.Logger.Error(err.Error())
		return err
	}
	return nil
}

// NeedRefreshInsCache whether needed to refresh instance's cache
func (a *MonitorAgent) NeedRefreshInsCache() bool {
	return time.Now().After(a.LastFetchInsTime.Add(time.Second * time.Duration(a.Conf.AgentConf.FetchInterval)))
}

// NeedRefreshGMCache whether needed to refresh gm's cache
func (a *MonitorAgent) NeedRefreshGMCache() bool {
	return time.Now().After(a.LastFetchGMTime.Add(time.Second * time.Duration(a.Conf.AgentConf.FetchInterval)))
}

// flushInsFetchTime flush the instance time
func (a *MonitorAgent) flushInsFetchTime() {
	a.LastFetchInsTime = time.Now()
}

// flushGmFetchTime flush the gm time
func (a *MonitorAgent) flushGmFetchTime() {
	a.LastFetchGMTime = time.Now()
}

// RepairGM if conn break, do reconnect
func (a *MonitorAgent) RepairGM(gmIns *GMConnection) error {
	go func(gmIns *GMConnection) {
		for {
			gmIns.Mutex.Lock()
			if gmIns.IsClose {
				gmIns.Mutex.Unlock()
				return
			}
			address := gmIns.Ip + ":" + strconv.Itoa(gmIns.Port)
			conn, err := net.Dial("tcp", address)
			if err != nil {
				log.Logger.Warn(
					"RepairGM: ip:", gmIns.Ip, " port:", gmIns.Port, " connect failed, err:", err.Error())
			} else {
				gmIns.NetConnection = conn
				gmIns.IsConnection = true
				log.Logger.Info("RepairGM: ip:", gmIns.Ip, " port:", gmIns.Port, " connect success.")
				gmIns.Mutex.Unlock()
				return
			}
			gmIns.Mutex.Unlock()
			time.Sleep(10 * time.Second)
		}
	}(gmIns)
	return nil
}

// registerAgentInfoToHaDB register current agent info
func (a *MonitorAgent) registerAgentInfoToHaDB() error {
	err := a.HaDBClient.RegisterDBHAInfo(
		a.MonIp,
		0,
		constvar.Agent,
		a.CityID,
		a.Campus,
		a.DetectType)
	if err != nil {
		return err
	}
	return nil
}

// moduloHashSharding rehash all instance into detect map, each ip
// only detect the minimum port instance, other instances ignore.
func (a *MonitorAgent) moduloHashSharding(allDbInstance []dbutil.DataBaseDetect) (map[string]dbutil.DataBaseDetect,
	error) {
	mod, modValue, err := a.HaDBClient.AgentGetHashValue(a.MonIp, a.CityID, a.DetectType, a.Conf.AgentConf.FetchInterval)
	if err != nil {
		log.Logger.Errorf("get Modulo failed and wait next refresh time. err:%s", err.Error())
		return nil, err
	}
	log.Logger.Debugf("current agent detect dbType[%s], mod[%d], modValue[%d]",
		a.DetectType, mod, modValue)
	shieldConfig, err := a.HaDBClient.GetShieldConfig(&model.HAShield{
		ShieldType: string(model.ShieldSwitch),
	})
	if err != nil {
		log.Logger.Errorf("get shield config failed:%s", err.Error())
		return nil, err
	}

	result := make(map[string]dbutil.DataBaseDetect)
	for _, rawIns := range allDbInstance {
		rawIp, rawPort := rawIns.GetAddress()
		if _, ok := shieldConfig[rawIp]; ok {
			log.Logger.Debugf("shield config exist this ip, skip detect :%s", rawIp)
			continue
		}
		if ins, ok := result[rawIp]; !ok {
			if util.CRC32(rawIp)%mod == modValue {
				result[rawIp] = rawIns
			}
		} else {
			_, port := ins.GetAddress()
			if rawPort < port {
				result[rawIp] = ins
			}
		}
	}
	return result, nil
}

// reporterHeartbeat send agent heartbeat to HA-DB
func (a *MonitorAgent) reporterHeartbeat() error {
	interval := time.Now().Sub(a.heartbeat).Seconds()
	err := a.HaDBClient.ReporterAgentHeartbeat(a.MonIp, a.DetectType, int(interval), "N/A")
	a.heartbeat = time.Now()
	return err
}

// reporterBindGM send bind gm info to hadb
// only agent trigger double check(report GM) should call this
func (a *MonitorAgent) reporterBindGM(gmInfo string) error {
	interval := time.Now().Sub(a.heartbeat).Seconds()
	err := a.HaDBClient.ReporterAgentHeartbeat(a.MonIp, a.DetectType, int(interval), gmInfo)
	a.heartbeat = time.Now()
	return err
}

// reportMonitor report monitor
func (a *MonitorAgent) reportMonitor(ins dbutil.DataBaseDetect, err error) {
	var errInfo string
	if err != nil {
		errInfo = err.Error()
	} else {
		errInfo = "no err information"
	}

	switch ins.GetStatus() {
	case constvar.SSHCheckFailed:
		content := "agent detect failed by ssh check, err:" + errInfo
		monitor.MonitorSendDetect(ins, constvar.DBHAEventDetectSSH, content)
	case constvar.AUTHCheckFailed:
		// only send monitor when the instance is redis
		if !a.SkipMonitor(ins) {
			content := "agent detect failed by auth check, err:" + errInfo
			monitor.MonitorSendDetect(ins, constvar.DBHAEventDetectAuth, content)
		}
	case constvar.DBCheckFailed:
		content := "agent detect failed by db check, err" + errInfo
		monitor.MonitorSendDetect(ins, constvar.DBHAEventDetectDB, content)
	default:
		break
	}
}

// SkipMonitor check skip send monitor or not
func (a *MonitorAgent) SkipMonitor(ins dbutil.DataBaseDetect) bool {
	clusterType := ins.GetCluster()
	if clusterType == constvar.DetectTenDBHA ||
		clusterType == constvar.DetectTenDBCluster {
		return true
	} else {
		return false
	}
}
