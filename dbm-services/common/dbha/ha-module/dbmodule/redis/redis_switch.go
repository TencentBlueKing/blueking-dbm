package redis

import (
	"fmt"
	"strings"
	"sync"
	"sync/atomic"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// RedisSwitch TODO
type RedisSwitch struct {
	RedisSwitchInfo
	Config *config.Config
	FLock  *util.FileLock
}

// CheckSwitch TODO
func (ins *RedisSwitch) CheckSwitch() (bool, error) {
	ins.ReportLogs(
		constvar.CheckSwitchInfo, fmt.Sprintf("handle instance[%s:%d]", ins.Ip, ins.Port),
	)
	if len(ins.Slave) != 1 {
		redisErr := fmt.Errorf("redis have invald slave[%d]", len(ins.Slave))
		log.Logger.Errorf("%s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, redisErr.Error())
		return false, redisErr
	}

	ins.SetInfo(constvar.SwitchInfoSlaveIp, ins.Slave[0].Ip)
	ins.SetInfo(constvar.SwitchInfoSlavePort, ins.Slave[0].Port)
	err := ins.DoLockByFile()
	if err != nil {
		redisErrLog := fmt.Sprintf("RedisSwitch lockfile failed,err:%s", err.Error())
		log.Logger.Errorf("%s info:%s", redisErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, redisErrLog)
		return false, err
	}

	ins.ReportLogs(constvar.CheckSwitchInfo, fmt.Sprintf("twemproxy infos:%v", ins.Proxy))
	_, err = ins.CheckTwemproxyPing()
	if err != nil {
		ins.DoUnLockByFile()
		redisErrLog := fmt.Sprintf("RedisSwitch check twemproxy failed,err:%s", err.Error())
		log.Logger.Errorf("%s info:%s", redisErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, redisErrLog)
		return false, err
	}

	ins.ReportLogs(
		constvar.CheckSwitchInfo, "RedisSwitch lock file and check twemproxy ok",
	)
	return true, nil
}

// DoSwitch TODO
func (ins *RedisSwitch) DoSwitch() error {
	log.Logger.Infof("redis do switch.info:{%s}", ins.ShowSwitchInstanceInfo())
	r := &client.RedisClient{}
	defer r.Close()

	slave := ins.Slave[0]
	addr := fmt.Sprintf("%s:%d", slave.Ip, slave.Port)
	r.Init(addr, ins.Pass, ins.Timeout, 0)

	rsp, err := r.SlaveOf("no", "one")
	if err != nil {
		ins.DoUnLockByFile()
		redisErrLog := fmt.Sprintf("Slave[%s] exec slaveOf no one failed,%s", addr, err.Error())
		log.Logger.Errorf("%s info:%s", redisErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, redisErrLog)
		return err
	}

	rspInfo, ok := rsp.(string)
	if !ok {
		ins.DoUnLockByFile()
		redisErr := fmt.Errorf("redis info response type is not string")
		log.Logger.Errorf("%s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, redisErr.Error())
		return redisErr
	}

	log.Logger.Infof("redis switch slaveof addr:%s,rsp:%s", addr, rspInfo)
	if !strings.Contains(rspInfo, "OK") {
		ins.DoUnLockByFile()
		redisErr := fmt.Errorf("redis do slaveof failed,slave:%d,rsp:%s",
			len(ins.Slave), rspInfo)
		log.Logger.Errorf("%s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, redisErr.Error())
		return redisErr
	}

	slaveOfOk := fmt.Sprintf("do slaveof no one ok,mark slave[%s] as master", addr)
	log.Logger.Infof("RedisSwitch  %s info:%s", slaveOfOk, ins.ShowSwitchInstanceInfo())
	ins.ReportLogs(constvar.SwitchInfo, slaveOfOk)

	ok, switchNum := ins.TwemproxySwitchM2S(ins.Ip, ins.Port, slave.Ip, slave.Port)
	if !ok {
		switchPart := fmt.Sprintf("redis switch proxy part success,succ:{%d},fail[%d],total:{%d}",
			switchNum, len(ins.Proxy)-switchNum, len(ins.Proxy))
		log.Logger.Infof("%s info:%s", switchPart, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, switchPart)
		return nil
	}

	switchAllOk := fmt.Sprintf("redis switch twemproxy ok,succ[%d],fail[%d],total[%d]",
		switchNum, len(ins.Proxy)-switchNum, len(ins.Proxy))
	log.Logger.Infof("%s info:%s", switchAllOk, ins.ShowSwitchInstanceInfo())
	ins.ReportLogs(constvar.SwitchInfo, switchAllOk)
	return nil
}

// ShowSwitchInstanceInfo TODO
func (ins *RedisSwitch) ShowSwitchInstanceInfo() string {
	format := `<%s#%d IDC:%s Status:%s App:%s ClusterType:%s MachineType:%s Cluster:%s>`
	str := fmt.Sprintf(
		format, ins.Ip, ins.Port, ins.IDC, ins.Status, ins.App,
		ins.ClusterType, ins.MetaType, ins.Cluster,
	)
	if len(ins.Slave) > 0 {
		str = fmt.Sprintf("%s Switch from MASTER:<%s#%d> to SLAVE:<%s#%d>",
			str, ins.Ip, ins.Port, ins.Slave[0].Ip, ins.Slave[0].Port)
	}
	return str
}

// RollBack TODO
func (ins *RedisSwitch) RollBack() error {
	return nil
}

// UpdateMetaInfo TODO
func (ins *RedisSwitch) UpdateMetaInfo() error {
	defer ins.DoUnLockByFile()
	ins.ReportLogs(constvar.UpdateMetaInfo, "handle swap_role for cmdb")
	if len(ins.Slave) != 1 {
		redisErr := fmt.Errorf("redis have invald slave[%d]", len(ins.Slave))
		log.Logger.Errorf("%s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.UpdateMetaFail, redisErr.Error())
		return redisErr
	}

	err := ins.CmDBClient.SwapRedisRole(ins.Cluster, ins.Ip, ins.Port,
		ins.Slave[0].Ip, ins.Slave[0].Port)
	if err != nil {
		redisErrLog := fmt.Sprintf("swap redis role failed. err:%s", err.Error())
		log.Logger.Errorf("%s info:%s", redisErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.UpdateMetaFail, redisErrLog)
		return err
	}
	swapOk := fmt.Sprintf("cluster[%s] swap_role slave[%s#%d] master[%s#%d] ok",
		ins.Cluster, ins.Ip, ins.Port, ins.Slave[0].Ip, ins.Slave[0].Port)
	ins.ReportLogs(constvar.UpdateMetaInfo, swapOk)
	return nil
}

// DoLockByFile do file lock by cluster and ip
func (ins *RedisSwitch) DoLockByFile() error {
	format := "/tmp/tendis-cluster-switch-%s.%s.lock"
	path := fmt.Sprintf(format, ins.Cluster, ins.Ip)
	fl := util.NewFileLock(path)

	err := fl.Lock()
	if err != nil {
		lockErrLog := fmt.Sprintf("lockfile failed,path:%s,err:%s", path, err.Error())
		log.Logger.Errorf("%s info:%s", lockErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, lockErrLog)
		return err
	} else {
		log.Logger.Infof("RedisSwitch lockfile ok,path:%s,info:%s",
			path, ins.ShowSwitchInstanceInfo())
		ins.FLock = fl
		ins.ReportLogs(
			constvar.CheckSwitchInfo, fmt.Sprintf("instance lock file %s ok", path),
		)
		return nil
	}
}

// DoUnLockByFile un-lock file lock
func (ins *RedisSwitch) DoUnLockByFile() {
	if nil == ins.FLock {
		log.Logger.Errorf("RedisSwitch filelock uninit and nil,info:%s",
			ins.ShowSwitchInstanceInfo())
		return
	}

	err := ins.FLock.UnLock()
	if err != nil {
		lockErrLog := fmt.Sprintf("RedisSwitch unlock failed,path:%s,err:%s",
			ins.FLock.Path, err.Error())
		log.Logger.Errorf("%s info:%s", lockErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, lockErrLog)
		return
	} else {
		log.Logger.Infof("RedisSwitch unlock ok,path:%s,info:%s",
			ins.FLock.Path, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(
			constvar.CheckSwitchInfo, fmt.Sprintf("instance unlock file %s ok", ins.FLock.Path),
		)
		return
	}
}

// CheckTwemproxyPing TODO
func (ins *RedisSwitch) CheckTwemproxyPing() ([]dbutil.ProxyInfo, error) {
	ins.ReportLogs(constvar.CheckSwitchInfo,
		fmt.Sprintf("twemproxy ping:start check_ping, with [%d] twemproxy",
			len(ins.Proxy)),
	)
	var wg sync.WaitGroup
	var proxyLock sync.Mutex
	kickProxys := make([]dbutil.ProxyInfo, 0)
	proxyServers := make([]map[string]string, 0)
	for _, proxy := range ins.Proxy {
		wg.Add(1)
		go func(proxyInfo dbutil.ProxyInfo) {
			defer wg.Done()
			psvrs, err := ins.DoTwemproxyPing(proxyInfo)
			if err != nil {
				if psvrs != nil && ins.ProxyStatusIsRunning(proxy) {
					proxyLock.Lock()
					kickProxys = append(kickProxys, proxyInfo)
					proxyServers = append(proxyServers, psvrs)
					proxyLock.Unlock()
				}
			} else {
				if psvrs != nil && ins.ProxyStatusIsRunning(proxy) {
					proxyLock.Lock()
					proxyServers = append(proxyServers, psvrs)
					proxyLock.Unlock()
				}
			}
		}(proxy)
	}

	wg.Wait()
	ins.ReportLogs(constvar.CheckSwitchInfo,
		fmt.Sprintf("twemproxy ping:[%d] check ping,with [%d] ok,[%d] kickoff",
			len(ins.Proxy), len(proxyServers)-len(kickProxys), len(kickProxys)))
	ins.KickOffTwemproxy(kickProxys)

	err := CheckInstancesEqual(proxyServers)
	if err != nil {
		redisErrLog := fmt.Sprintf("twemproxy conf not equal,err:%s, info:%s",
			err.Error(), ins.ShowSwitchInstanceInfo())
		log.Logger.Errorf(redisErrLog)
		ins.ReportLogs(constvar.CheckSwitchFail, redisErrLog)
		return nil, err
	}

	ins.ReportLogs(constvar.CheckSwitchInfo,
		"all twemproxy nosqlproxy servers is equal")
	return kickProxys, nil
}

// KickOffTwemproxy TODO
func (ins *RedisSwitch) KickOffTwemproxy(kickProxys []dbutil.ProxyInfo) {
	if len(kickProxys) == 0 {
		ins.ReportLogs(constvar.CheckSwitchInfo,
			"all twemproxy sames to be ok,ignore kickOff...")
		return
	}

	kickLog := fmt.Sprintf("need to kickoff twemproxy [%d]", len(kickProxys))
	ins.ReportLogs(constvar.CheckSwitchInfo, kickLog)
	log.Logger.Infof("RedisSwitch %s", kickLog)
	for _, proxy := range kickProxys {
		ins.ReportLogs(constvar.CheckSwitchInfo,
			fmt.Sprintf("do kickoff bad ping twemproxys,twemproxy:%v", proxy))
		ins.DoKickTwemproxy(proxy)
	}
	ins.ReportLogs(constvar.CheckSwitchInfo, "kickoff bad ping twemproxy done")
	return
}

// ProxyStatusIsRunning check status of proxy is running or not
func (ins *RedisSwitch) ProxyStatusIsRunning(proxy dbutil.ProxyInfo) bool {
	if len(proxy.Status) == 0 {
		log.Logger.Infof("RedisSwitch proxy has no status and skip")
		return true
	}

	if proxy.Status != constvar.RUNNING {
		log.Logger.Infof("RedisSwitch proxy status[%s] is not RUNNING", proxy.Status)
		return false
	} else {
		log.Logger.Infof("RedisSwitch proxy status[%s] is RUNNING", proxy.Status)
		return true
	}
}

// ParseTwemproxyResponse parse the reponse of twemproxy
func ParseTwemproxyResponse(rsp string) (map[string]string, error) {
	proxyIns := make(map[string]string)
	lines := strings.Split(rsp, "\n")
	if len(lines) == 0 {
		redisErr := fmt.Errorf("twemproxy nosqlproxy servers return none")
		return proxyIns, redisErr
	}

	for _, line := range lines {
		eles := strings.Split(line, " ")
		if len(eles) < 3 {
			continue
		}

		proxyIns[eles[0]] = eles[2]
	}
	return proxyIns, nil
}

// CheckInstancesEqual check if the redis instances of twemproxy is equivalent
func CheckInstancesEqual(proxysSvrs []map[string]string) error {
	if len(proxysSvrs) <= 1 {
		return nil
	}

	filterProxys := make([]map[string]string, 0)
	for _, p := range proxysSvrs {
		if len(p) > 0 {
			filterProxys = append(filterProxys, p)
		}
	}

	log.Logger.Debugf("RedisSwitch compare proxys, proxySvrs:%d filterProxySvrs:%d",
		len(proxysSvrs), len(filterProxys))
	if len(filterProxys) <= 1 {
		return nil
	}

	first := filterProxys[0]
	for i := 1; i < len(filterProxys); i++ {
		cmpOne := filterProxys[i]
		for k, v := range first {
			val, ok := cmpOne[k]
			if !ok {
				err := fmt.Errorf("compare twemproxy server failed,%s-%s not find, twemproxyConf:%v",
					k, v, filterProxys)
				log.Logger.Errorf(err.Error())
				return err
			}

			if val != v {
				err := fmt.Errorf("compare twemproxy server failed,[%s-%s] vs [%s-%s], twemproxyConf:%v",
					k, v, k, val, filterProxys)
				log.Logger.Errorf(err.Error())
				return err
			}
		}
	}
	return nil
}

// DoTwemproxyPing get redis instance infomation from twemproxy by netcat
func (ins *RedisSwitch) DoTwemproxyPing(proxy dbutil.ProxyInfo) (map[string]string, error) {
	rsp, err := ins.CommunicateTwemproxy(proxy.Ip, proxy.AdminPort,
		"get nosqlproxy servers")
	if err != nil {
		checkErrLog := fmt.Sprintf("twemproxy ping: communicate failed,proxy[%s:%d],err=%s",
			proxy.Ip, proxy.Port, err.Error())
		log.Logger.Errorf("RedisSwitch %s info:%s", checkErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, checkErrLog)
		return nil, nil
	}

	proxyIns, err := ParseTwemproxyResponse(rsp)
	if err != nil {
		checkErrLog := fmt.Sprintf("twemproxy ping: parse rsp[%s] failed,proxy[%s:%d]",
			rsp, proxy.Ip, proxy.Port)
		log.Logger.Errorf("RedisSwitch %s info:%s", checkErrLog, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, checkErrLog)
		return nil, nil
	}

	masterInfo := fmt.Sprintf("%s:%d", ins.Ip, ins.Port)
	if _, ok := proxyIns[masterInfo]; !ok {
		format := "twemproxy[%s:%d:%d] not have %s and need to kick,addr[%s:%d],twemproxyConf:%s"
		redisErr := fmt.Errorf(format, proxy.Ip, proxy.Port,
			proxy.AdminPort, masterInfo, proxy.Ip, proxy.Port, rsp)
		log.Logger.Errorf("RedisSwitch %s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, redisErr.Error())
		return proxyIns, redisErr
	}
	log.Logger.Debugf("RedisSwitch do ping twemproxy proxy[%s:%d] ok, twemproxyConf:%v",
		proxy.Ip, proxy.Port, rsp)
	return proxyIns, nil
}

// DoKickTwemproxy kick bad case of twemproxy from twemproxy
func (ins *RedisSwitch) DoKickTwemproxy(proxy dbutil.ProxyInfo) error {
	log.Logger.Infof("RedisSwitch kick twemproxy[%s:%d-%d]",
		proxy.Ip, proxy.Port, proxy.AdminPort)
	infos, err := ins.CmDBClient.GetDBInstanceInfoByIp(proxy.Ip)
	if err != nil {
		redisErr := fmt.Errorf("get twemproxy[%s:%d:%d] from cmdb failed",
			proxy.Ip, proxy.Port, proxy.AdminPort)
		log.Logger.Errorf("%s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, redisErr.Error())
		return redisErr
	}

	if len(infos) == 0 {
		redisErr := fmt.Errorf("the number of proxy[%d] is invalid", len(infos))
		log.Logger.Errorf("%s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.CheckSwitchFail, redisErr.Error())
		return redisErr
	}

	log.Logger.Infof("RedisSwitch kick debug 2,infoLen=%d", len(infos))
	for _, info := range infos {
		proxyIns, err := CreateRedisProxySwitchInfo(info, ins.Config)
		if err != nil {
			log.Logger.Errorf(err.Error())
			continue
		}

		if proxyIns.Ip != proxy.Ip || proxyIns.Port != proxy.Port ||
			proxyIns.MetaType != constvar.TwemproxyMetaType {
			log.Logger.Infof("RedisSwitch skip kick[%s:%d-%s],proxy[%s:%d-%s]",
				proxy.Ip, proxy.Port, constvar.TwemproxyMetaType,
				proxyIns.Ip, proxyIns.Port, proxyIns.MetaType,
			)
			continue
		}

		if proxyIns.Status != constvar.RUNNING &&
			proxyIns.Status != constvar.AVAILABLE {
			kickSkipLog := fmt.Sprintf("skip while status is [%s],twemproxy[%s:%d]",
				proxyIns.Status, proxyIns.Ip, proxyIns.Port)
			log.Logger.Infof("RedisSwitch %s", kickSkipLog)
			ins.ReportLogs(constvar.CheckSwitchInfo, kickSkipLog)
			continue
		}

		if proxyIns.CheckFetchEntryDetail() {
			edErr := proxyIns.GetEntryDetailInfo()
			if edErr != nil {
				kickErrLog := fmt.Sprintf("GetEntryDetail failed while Kick Twemproxy:%s,err:%s",
					proxyIns.ShowSwitchInstanceInfo(), edErr.Error())
				log.Logger.Errorf("RedisSwitch %s", kickErrLog)
				return edErr
			}
		}

		err = proxyIns.KickOffDns()
		if err != nil {
			kickErrLog := fmt.Sprintf("kick twemproxy failed by dns,proxy=%s,err=%s",
				proxyIns.ShowSwitchInstanceInfo(), err.Error())
			log.Logger.Errorf("RedisSwitch %s", kickErrLog)
			ins.ReportLogs(constvar.CheckSwitchFail, kickErrLog)
			return err
		}
		err = proxyIns.KickOffPolaris()
		if err != nil {
			kickErrLog := fmt.Sprintf("kick twemproxy failed by polaris,proxy=%s,err=%s",
				proxyIns.ShowSwitchInstanceInfo(), err.Error())
			log.Logger.Errorf("RedisSwitch %s", kickErrLog)
			ins.ReportLogs(constvar.CheckSwitchFail, kickErrLog)
			return err
		}
		err = proxyIns.KickOffClb()
		if err != nil {
			kickErrLog := fmt.Sprintf("kick twemproxy failed by clb,proxy=%s,err=%s",
				proxyIns.ShowSwitchInstanceInfo(), err.Error())
			log.Logger.Errorf("RedisSwitch %s", kickErrLog)
			ins.ReportLogs(constvar.CheckSwitchFail, kickErrLog)
			return err
		}
	}

	kickOkLog := fmt.Sprintf(" kick twemproxy[%s:%d-%d] ok",
		proxy.Ip, proxy.Port, proxy.AdminPort)
	log.Logger.Infof("RedisSwitch %s", kickOkLog)
	ins.ReportLogs(constvar.CheckSwitchInfo, kickOkLog)
	return nil
}

// TwemproxySwitchM2S TODO
func (ins *RedisSwitch) TwemproxySwitchM2S(masterIp string, masterPort int,
	slaveIp string, slavePort int) (bool, int) {
	var successSwitchNum int64 = 0
	var wg sync.WaitGroup
	for _, proxy := range ins.Proxy {
		wg.Add(1)
		go func(proxyInfo dbutil.ProxyInfo) {
			defer wg.Done()
			log.Logger.Infof("RedisCache twemproxy[%s:%d:%d] switch,master[%s:%d]->slave[%s:%d]",
				proxyInfo.Ip, proxyInfo.Port, proxyInfo.AdminPort,
				masterIp, masterPort, slaveIp, slavePort)
			pok, err := ins.TwemproxySwitchSingle(
				proxyInfo, masterIp, masterPort, slaveIp, slavePort,
			)
			if err != nil {
				log.Logger.Infof("redisCache twemproxy switch failed,err:%s,info:%s",
					err.Error(), ins.ShowSwitchInstanceInfo())
				return
			}

			if !pok {
				log.Logger.Infof("redisCache twemproxy switch failed,info:%s",
					ins.ShowSwitchInstanceInfo())
			} else {
				log.Logger.Infof("RedisCache twemproxy switch M2S ok,proxy[%s:%d-%d],info:%s",
					proxyInfo.Ip, proxyInfo.Port, proxyInfo.AdminPort, ins.ShowSwitchInstanceInfo())
				atomic.AddInt64(&successSwitchNum, 1)
			}
		}(proxy)
	}

	wg.Wait()
	switchSucc := int(successSwitchNum)
	if switchSucc == len(ins.Proxy) {
		log.Logger.Infof("RedisCache twemproxy switch M2S,all succ[%d]", len(ins.Proxy))
		return true, switchSucc
	} else {
		log.Logger.Infof("RedisCache twemproxy switch M2S,part succ[%d],all[%d]",
			switchSucc, len(ins.Proxy))
		return false, switchSucc
	}
}

// TwemproxySwitchSingle change the redis information of twemproxy by master and slave
func (ins *RedisSwitch) TwemproxySwitchSingle(proxy dbutil.ProxyInfo,
	masterIp string, masterPort int,
	slaveIp string, slavePort int) (bool, error) {
	format := "change nosqlproxy %s %s"
	masterAddr := fmt.Sprintf("%s:%d", masterIp, masterPort)
	slaveAddr := fmt.Sprintf("%s:%d", slaveIp, slavePort)
	cmdInfo := fmt.Sprintf(format, masterAddr, slaveAddr)

	rsp, err := ins.CommunicateTwemproxy(proxy.Ip, proxy.AdminPort, cmdInfo)
	if err != nil {
		redisErr := fmt.Errorf("twemproxy[%s:%d:%d] switch %s to %s failed,cmd:%s,err:%s",
			proxy.Ip, proxy.Port, proxy.AdminPort, masterAddr, slaveAddr, cmdInfo, err.Error())
		log.Logger.Errorf("RedisSwitch %s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, redisErr.Error())
		return false, redisErr
	}

	if strings.Contains(rsp, "success") {
		return true, nil
	} else {
		redisErr := fmt.Errorf("switch twemproxy[%s:%d:%d] from %s to %s failed",
			proxy.Ip, proxy.Port, proxy.AdminPort, masterAddr, slaveAddr)
		log.Logger.Errorf("RedisSwitch %s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.SwitchFail, redisErr.Error())
		return false, redisErr
	}
}

// CommunicateTwemproxy connect to twemproxy and send command by tcp
func (ins *RedisSwitch) CommunicateTwemproxy(
	ip string, port int, text string,
) (string, error) {
	nc := &client.NcClient{}
	addr := fmt.Sprintf("%s:%d", ip, port)
	defer nc.Close()

	err := nc.DoConn(addr, ins.Timeout)
	if err != nil {
		log.Logger.Errorf("RedisSwitch nc conn failed,addr:%s,timeout:%d,err:%s",
			addr, ins.Timeout, err.Error())
		return "", err
	}

	err = nc.WriteText(text)
	if err != nil {
		log.Logger.Errorf("RedisSwitch nc write failed,addr:%s,timeout:%d,err:%s",
			addr, ins.Timeout, err.Error())
		return "", err
	}

	rsp := make([]byte, 1024*10)
	n, err := nc.Read(rsp)
	if err != nil {
		log.Logger.Errorf("RedisSwitch nc read failed,addr:%s,timeout:%d,err:%s",
			addr, ins.Timeout, err.Error())
		return "", err
	}
	return string(rsp[:n]), nil
}
