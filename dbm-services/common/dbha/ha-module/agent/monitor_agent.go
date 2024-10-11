package agent

import (
	"dbm-services/common/dbha/hadb-api/model"
	"fmt"
	"net"
	"sort"
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
	// mod for current agent
	HashMod int
	// mod value for current agent
	HashValue  int
	DBInstance map[string]dbutil.DataBaseDetect
	GMInstance map[string]*GMConnection
	// config file
	Conf *config.Config
	// API client to access cmdb metadata
	CmDBClient *client.CmDBClient
	// API client to access hadb
	HaDBClient     *client.HaDBClient
	heartbeat      time.Time
	MaxConcurrency int // Add this field to store the max concurrency value
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
		MaxConcurrency:   conf.AgentConf.MaxConcurrency,
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
	sem := make(chan struct{}, a.MaxConcurrency) // 创建一个有缓冲的通道，容量为 maxConcurrency
	log.Logger.Debugf("[%s] need to detect instances number:%d", a.DetectType, len(a.DBInstance))
	for _, ins := range instances {
		wg.Add(1)
		sem <- struct{}{} // 向通道发送信号，表明一个新的 goroutine 启动
		go func(ins dbutil.DataBaseDetect) {
			defer wg.Done()
			defer func() { <-sem }() // goroutine 完成后，从通道接收信号，释放一个槽位
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
			//if fetch failed, not flush fetch time
			return
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
			ip, port, ins.GetDBType(), ins.GetStatus(), err.Error())
	}

	a.reportMonitor(ins, err)
	if ins.NeedReporter() {
		// reporter detect result to hadb
		if err = a.ReporterDetectInfo(ins); err != nil {
			log.Logger.Errorf(
				"reporter hadb instance status failed. err:%s, ip:%s, port:%d, db_type:%s, status:%s",
				err.Error(), ip, port, ins.GetDBType(), ins.GetStatus())
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
	log.Logger.Infof("[%s] report agent heartbeat success.", a.DetectType)
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
	mod, modValue, err := a.HaDBClient.AgentGetHashValue(a.MonIp, a.CityID, a.DetectType, a.Conf.AgentConf.FetchInterval)
	if err != nil {
		log.Logger.Errorf("get hash module info failed and wait next refresh time. err:%s", err.Error())
		return err
	}
	//set current agent's hash mod, hash value, and report to DB later
	log.Logger.Debugf("hash mod:%d, hash value:%d, dbType:%s", mod, modValue, a.DetectType)
	a.HashMod = mod
	a.HashValue = modValue

	req := client.DBInstanceInfoRequest{
		LogicalCityIDs: []int{a.CityID},
		HashCnt:        mod,
		HashValue:      modValue,
		ClusterTypes:   []string{a.DetectType},
	}

	rawInfo, err := a.CmDBClient.GetDBInstanceInfoByClusterType(req)
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

	shieldConfig, err := a.HaDBClient.GetShieldConfig(&model.HAShield{
		ShieldType: string(model.ShieldSwitch),
	})
	if err != nil {
		log.Logger.Errorf("get shield config failed:%s", err.Error())
		return err
	}

	//should clean cache always
	a.DBInstance = make(map[string]dbutil.DataBaseDetect)
	for _, rawIns := range AllDbInstance {
		rawIp, rawPort := rawIns.GetAddress()
		if _, ok := shieldConfig[rawIp]; ok {
			log.Logger.Debugf("shield config exist this ip, skip detect :%s", rawIp)
			continue
		}
		if ins, ok := a.DBInstance[rawIp]; !ok {
			a.DBInstance[rawIp] = rawIns
		} else {
			_, port := ins.GetAddress()
			if rawPort < port {
				a.DBInstance[rawIp] = ins
			}
		}
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

// ReporterDetectInfo report detect info to gm
func (a *MonitorAgent) ReporterDetectInfo(reporterInstance dbutil.DataBaseDetect) error {
	var err error
	isReporter := false
	ip, port := reporterInstance.GetAddress()
	if reporterInstance.GetStatus() == constvar.DBCheckSuccess ||
		reporterInstance.GetStatus() == constvar.SSHCheckSuccess {
		if err = a.HaDBClient.ReportDBStatus(reporterInstance.GetApp(), a.MonIp, ip, port,
			string(reporterInstance.GetDBType()), string(reporterInstance.GetStatus()), "N/A"); err != nil {
			log.Logger.Errorf(
				"reporter hadb instance status failed. err:%s, ip:%s, port:%d, db_type:%s, status:%s",
				err.Error(), ip, port, reporterInstance.GetDBType(), reporterInstance.GetStatus())
		}
		return nil
	}

	// 提取 GMInstance 的 IP 列表
	var gmIPs []string
	for gmIP := range a.GMInstance {
		gmIPs = append(gmIPs, gmIP)
	}

	// 按照 IP 字典顺序排序
	sort.Strings(gmIPs)

	for _, sortedIp := range gmIPs {
		gmIns := a.GMInstance[sortedIp]
		gmIns.Mutex.Lock()
		if !gmIns.IsConnection {
			gmIns.Mutex.Unlock()
			continue
		}
		gmInfo := fmt.Sprintf("%s#%d", gmIns.Ip, gmIns.Port)
		jsonInfo, err := reporterInstance.Serialization()
		if err != nil {
			gmIns.Mutex.Unlock()
			log.Logger.Errorf("instance Serialization failed. err:%s", err.Error())
			return err
		}
		log.Logger.Infof("ins:[%s#%d] try to report detect info to gm:[%s]", ip, port, gmInfo)
		err = gmIns.ReportInstance(reporterInstance.GetDetectType(), jsonInfo)
		if err != nil {
			log.Logger.Warnf("reporter gm failed. gm_ip:%s, gm_port:%d, err:%s", gmIns.Ip, gmIns.Port, err.Error())
			gmIns.IsConnection = false
			err = a.RepairGM(gmIns)
			if err != nil {
				log.Logger.Errorf("Repair gm failed:%s", err.Error())
				return err
			}
		} else {
			if err = a.HaDBClient.ReportDBStatus(reporterInstance.GetApp(), a.MonIp, ip, port,
				string(reporterInstance.GetDBType()), string(reporterInstance.GetStatus()), gmInfo); err != nil {
				log.Logger.Errorf(
					"reporter hadb instance status failed. err:%s, ip:%s, port:%d, db_type:%s, status:%s",
					err.Error(), ip, port, reporterInstance.GetDBType(), reporterInstance.GetStatus())
			}
			isReporter = true
			gmIns.Mutex.Unlock()
			break
		}
		gmIns.Mutex.Unlock()
	}

	if !isReporter {
		err = fmt.Errorf("get report GM failed: all gm disconnect")
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

// reporterHeartbeat send agent heartbeat to HA-DB
func (a *MonitorAgent) reporterHeartbeat() error {
	interval := time.Now().Sub(a.heartbeat).Seconds()
	err := a.HaDBClient.ReporterAgentHeartbeat(a.MonIp, a.DetectType, int(interval), a.HashMod, a.HashValue)
	a.heartbeat = time.Now()
	return err
}

// reportMonitor report onitor
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
	case constvar.SSHAuthFailed:
		content := "agent detect failed by ssh auth, err:" + errInfo
		monitor.MonitorSendDetect(ins, constvar.DBHAEventDetectSSHAuth, content)
	case constvar.RedisAuthFailed:
		content := "agent detect failed by redis auth, err:" + errInfo
		monitor.MonitorSendDetect(ins, constvar.DBHAEventDetectRedisAuth, content)
	case constvar.DBCheckFailed:
		content := "agent detect failed by db check, err" + errInfo
		monitor.MonitorSendDetect(ins, constvar.DBHAEventDetectDB, content)
	default:
		break
	}
}
