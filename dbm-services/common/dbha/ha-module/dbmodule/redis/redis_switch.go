package redis

import (
	"bufio"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

// RedisSwitch redis switch instance
type RedisSwitch struct {
	RedisSwitchInfo
	Config       *config.Config
	FLock        *util.FileLock
	IsSkipSwitch bool
}

const (
	MaxLastIOSecondsAgo = 600
)

// CheckSwitch check redis status before switch
func (ins *RedisSwitch) CheckSwitch() (bool, error) {
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("redis switch precheck: handle instance[%s:%d]", ins.Ip, ins.Port))

	// if instance is slave, set NoNeed flag
	if ins.IsSkipSwitch = ins.IsSlave(); ins.IsSkipSwitch {
		ins.ReportLogs(constvar.InfoResult,
			fmt.Sprintf("redis switch precheck: ins is slave[%s:%d], skip with success.", ins.Ip, ins.Port))
		return true, nil
	}

	// check the number of slave
	if len(ins.Slave) < 1 {
		redisErr := fmt.Errorf("redis switch precheck: have invald slave[%d]", len(ins.Slave))
		ins.ReportLogs(constvar.FailResult, redisErr.Error())
		return false, redisErr
	}
	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("redis switch precheck: choice slave[%s:%d] for switch ;slave list:%+v",
			ins.Slave[0].Ip, ins.Slave[0].Port, ins.Slave))

	ins.SetInfo(constvar.SlaveIpKey, ins.Slave[0].Ip)
	ins.SetInfo(constvar.SlavePortKey, ins.Slave[0].Port)
	if err := ins.DoLockByFile(); err != nil {
		redisErrLog := fmt.Sprintf("redis switch precheck: lockfile failed,err:%s", err.Error())
		ins.ReportLogs(constvar.FailResult, redisErrLog)
		return false, err
	}

	if ins.ClusterType != constvar.RedisInstance {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("redis switch precheck: twemproxy infos:%v", ins.Proxy))
		if _, err := ins.CheckTwemproxyPing(); err != nil {
			ins.DoUnLockByFile()
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("redis switch precheck: twemproxy failed,err:%s", err.Error()))
			return false, err
		}
	}

	// here , do slave sync check.
	if err := ins.CheckSlaveSyncStatus(ins.Ip, ins.Port, ins.Slave[0].Ip, ins.Slave[0].Port); err != nil {
		ins.DoUnLockByFile()
		ins.ReportLogs(constvar.FailResult,
			fmt.Sprintf("redis switch precheck: slave sync check failed,err:%s", err.Error()))
		return false, err
	}

	ins.ReportLogs(constvar.InfoResult,
		"redis switch precheck: lock file and check twemproxy and sync status ok; next ^_^")
	return true, nil
}

// DoSwitch do switch action
func (ins *RedisSwitch) DoSwitch() error {
	log.Logger.Infof("redis switch: redis do switch.info:{%s}", ins.ShowSwitchInstanceInfo())
	if ins.IsSkipSwitch {
		ins.ReportLogs(constvar.InfoResult,
			fmt.Sprintf("redis switch: ins is slave[%s:%d], skip with success.", ins.Ip, ins.Port))
		return nil
	}

	r := &client.RedisClient{}
	defer r.Close()

	slave := ins.Slave[0]
	addr := fmt.Sprintf("%s:%d", slave.Ip, slave.Port)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), ins.GetMetaType())
	}
	r.Init(addr, ins.Pass, ins.Timeout, 0)

	ret, err := r.SlaveOf("No", "One")
	if err != nil {
		ins.DoUnLockByFile()
		redisErrLog := fmt.Sprintf("redis switch: Slave[%s] exec slaveOf no one failed,%s", addr, err.Error())
		ins.ReportLogs(constvar.FailResult, redisErrLog)
		return err
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("redis switch: [%s] exec slaveof no one, return:%s", addr, ret))

	if !strings.Contains(ret, "OK") {
		ins.DoUnLockByFile()
		redisErr := fmt.Errorf("redis switch: redis do slaveof failed, [%s:%d],rsp:%s", slave.Ip, slave.Port, ret)
		log.Logger.Errorf("redis switch: %s info:%s", redisErr.Error(), ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(constvar.FailResult, redisErr.Error())
		return redisErr
	}

	if ins.ClusterType != constvar.RedisInstance {
		if err := ins.TwemproxySwitchM2S(ins.Ip, ins.Port, slave.Ip, slave.Port); err != nil {
			ins.DoUnLockByFile()
			return err
		}
	}
	return nil
}

// ShowSwitchInstanceInfo show switch instance information
func (ins *RedisSwitch) ShowSwitchInstanceInfo() string {
	format := `<%s#%d IDC:%d Status:%s App:%s ClusterType:%s MachineType:%s Cluster:%s>`
	str := fmt.Sprintf(
		format, ins.Ip, ins.Port, ins.IdcID, ins.Status, ins.App,
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

// UpdateMetaInfo swap redis role information from cmdb
func (ins *RedisSwitch) UpdateMetaInfo() error {
	if ins.IsSkipSwitch {
		ins.ReportLogs(constvar.InfoResult,
			fmt.Sprintf("meta update: no need update meta!, status updated yet. [%s:%d]", ins.Ip, ins.Port))
		return nil
	}

	defer ins.DoUnLockByFile()
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("meta update: handle swap_role for cmdb [%s:%d]", ins.Ip, ins.Port))
	if len(ins.Slave) != 1 {
		redisErr := fmt.Errorf("meta update: redis have invald slave[%d]", len(ins.Slave))
		ins.ReportLogs(constvar.FailResult, redisErr.Error())
		return redisErr
	}

	err := ins.CmDBClient.SwapRedisRole(ins.Cluster, ins.Ip, ins.Port,
		ins.Slave[0].Ip, ins.Slave[0].Port)
	if err != nil {
		redisErrLog := fmt.Sprintf("meta update: swap redis role failed. err:%s", err.Error())
		ins.ReportLogs(constvar.FailResult, redisErrLog)
		return err
	}
	swapOk := fmt.Sprintf("meta update: cluster[%s] swap_role slave[%s#%d] master[%s#%d] ok",
		ins.Cluster, ins.Ip, ins.Port, ins.Slave[0].Ip, ins.Slave[0].Port)
	ins.ReportLogs(constvar.InfoResult, swapOk)
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
		ins.ReportLogs(constvar.FailResult, lockErrLog)
		return err
	} else {
		log.Logger.Infof("RedisSwitch lockfile ok,path:%s,info:%s",
			path, ins.ShowSwitchInstanceInfo())
		ins.FLock = fl
		ins.ReportLogs(
			constvar.InfoResult, fmt.Sprintf("instance lock file %s ok", path),
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
		ins.ReportLogs(constvar.FailResult, lockErrLog)
		return
	} else {
		log.Logger.Infof("RedisSwitch unlock ok,path:%s,info:%s",
			ins.FLock.Path, ins.ShowSwitchInstanceInfo())
		ins.ReportLogs(
			constvar.InfoResult, fmt.Sprintf("instance unlock file %s ok", ins.FLock.Path),
		)
		return
	}
}

// CheckTwemproxyPing 检查proxy 后端一致性，只统计状态是 RUNNING 的 proxy
func (ins *RedisSwitch) CheckTwemproxyPing() ([]dbutil.ProxyInfo, error) {
	var wg sync.WaitGroup
	var proxyLock sync.Mutex
	kickProxys, proxyServers, proxyMd5s, running :=
		make([]dbutil.ProxyInfo, 0), map[string]map[string]string{}, map[string][]string{}, 0
	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("twemproxy ping: start get nosqlproxy servers , with [%d] twemproxy",
			len(ins.Proxy)),
	)

	for _, proxy := range ins.Proxy {
		wg.Add(1)
		if ins.ProxyStatusIsRunning(proxy) {
			running++
		}
		go func(proxyInfo dbutil.ProxyInfo) {
			defer wg.Done()
			proxyAddr := fmt.Sprintf("%s:%d", proxyInfo.Ip, proxyInfo.Port)
			log.Logger.Infof("twemproxy ping: start check proxy [%s] backends servers .", proxyAddr)

			segs, pmd5, err := ins.GetTwemProxyBackendsMD5(proxyInfo.Ip, proxyInfo.AdminPort)
			if err != nil { // proxy 探测失败
				if ins.ProxyStatusIsRunning(proxyInfo) {
					proxyLock.Lock()
					kickProxys = append(kickProxys, proxyInfo)
					proxyLock.Unlock()
					log.Logger.Errorf("twemproxy ping: [%s:%s] get nosqlproxy servers failed:{%+v}, info:%s",
						proxyAddr, proxyInfo.Status, err, ins.ShowSwitchInstanceInfo())
				} else {
					log.Logger.Warnf("twemproxy ping: [%s:%s] get nosqlproxy servers failed:{%+v}, info:%s",
						proxyAddr, proxyInfo.Status, err, ins.ShowSwitchInstanceInfo())
				}
			} else { // proxy 可以链接上
				if ins.ProxyStatusIsRunning(proxyInfo) { // 只统计状态是 RUNNING 的 proxy
					proxyLock.Lock()
					proxyServers[proxyAddr] = segs

					if _, ok := proxyMd5s[pmd5]; !ok {
						proxyMd5s[pmd5] = []string{}
					}
					proxyMd5s[pmd5] = append(proxyMd5s[pmd5], proxyAddr)
					proxyLock.Unlock()
				} else { // 忽略不是Running状态的
					log.Logger.Warnf("twemproxy ping: [%s:%s] static md5 ignore[md5sum:%s]. :{%+v}, info:%s",
						proxyAddr, proxyInfo.Status, pmd5, err, ins.ShowSwitchInstanceInfo())
				}
			}
		}(proxy)
	}
	wg.Wait()

	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("twemproxy ping: summary [total:%d, running:%d] checked, with [%d] ok, [%d] will be kickoff",
			len(ins.Proxy), running, len(proxyServers)-len(kickProxys), len(kickProxys)))
	ins.KickOffTwemproxy(kickProxys)

	x, _ := json.Marshal(proxyMd5s)
	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("twemproxy ping: round by [%s:%d] backends servers md5 summary static: %s", ins.Ip, ins.Port, x))
	if len(proxyMd5s) != 1 {
		for oneMd5 := range proxyMd5s {
			md5Servers := proxyMd5s[oneMd5]
			if len(md5Servers) > 0 {
				ins.ReportLogs(constvar.FailResult,
					fmt.Sprintf("twemproxy ping: check with md5 : %s(serverCount:%d) ,servers:%+v",
						oneMd5, len(md5Servers), proxyServers[md5Servers[0]]))
			}
		}

		checkErrLog := fmt.Sprintf("twemproxy ping: got mutil status==running proxy backends md5 [%+v]", proxyMd5s)
		ins.ReportLogs(constvar.FailResult, checkErrLog)
		return nil, fmt.Errorf(checkErrLog)
	}

	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("twemproxy ping: round by [%s:%d] done with result all twemproxy nosqlproxy servers equal",
			ins.Ip, ins.Port))
	return kickProxys, nil
}

// KickOffTwemproxy kick twemproxy from gateway
func (ins *RedisSwitch) KickOffTwemproxy(kickProxys []dbutil.ProxyInfo) {
	if len(kickProxys) == 0 {
		ins.ReportLogs(constvar.InfoResult,
			"all twemproxy sames to be ok,ignore kickOff...")
		return
	}

	kickLog := fmt.Sprintf("kickoff twemproxy: need to kickoff twemproxy [%d]", len(kickProxys))
	ins.ReportLogs(constvar.InfoResult, kickLog)
	for _, proxy := range kickProxys {
		ins.ReportLogs(constvar.InfoResult,
			fmt.Sprintf("kickoff twemproxy: do kickoff bad ping twemproxys,twemproxy:%+v", proxy))
		ins.DoKickTwemproxy(proxy)
	}
	ins.ReportLogs(constvar.InfoResult, "kickoff twemproxy: kickoff bad ping twemproxy done")
}

// ProxyStatusIsRunning check status of proxy is running or not
func (ins *RedisSwitch) ProxyStatusIsRunning(proxy dbutil.ProxyInfo) bool {
	return proxy.Status == constvar.RUNNING
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

// DoKickTwemproxy kick bad case of twemproxy from twemproxy
func (ins *RedisSwitch) DoKickTwemproxy(proxy dbutil.ProxyInfo) error {
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("kickoff twemproxy: start kickoff by [%s:%d]", proxy.Ip, proxy.Port))
	infos, err := ins.CmDBClient.GetDBInstanceInfoByIp(proxy.Ip)
	if err != nil {
		redisErr := fmt.Errorf("kickoff twemproxy: get twemproxy[%s:%d:%d] from cmdb failed",
			proxy.Ip, proxy.Port, proxy.AdminPort)
		ins.ReportLogs(constvar.FailResult, redisErr.Error())
		return redisErr
	}

	if len(infos) == 0 {
		redisErr := fmt.Errorf("kickoff twemproxy: the number of proxy[%d] is invalid geted by cmdb", len(infos))
		ins.ReportLogs(constvar.FailResult, redisErr.Error())
		return redisErr
	}

	for _, info := range infos {
		proxyIns, err := CreateRedisProxySwitchInfo(info, ins.Config)
		if err != nil {
			log.Logger.Errorf(err.Error())
			continue
		}

		if proxyIns.Ip != proxy.Ip || proxyIns.Port != proxy.Port ||
			proxyIns.MetaType != constvar.TwemproxyMetaType {
			log.Logger.Warnf("kickoff twemproxy: RedisSwitch skip kick[%s:%d-%s],proxy[%s:%d-%s]",
				proxy.Ip, proxy.Port, constvar.TwemproxyMetaType,
				proxyIns.Ip, proxyIns.Port, proxyIns.MetaType,
			)
			continue
		}

		if proxyIns.Status != constvar.RUNNING &&
			proxyIns.Status != constvar.AVAILABLE {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("kickoff twemproxy: skip kickoff status is [%s],twemproxy[%s:%d]",
				proxyIns.Status, proxyIns.Ip, proxyIns.Port))
			continue
		}

		err = proxyIns.KickOffDns()
		if err != nil {
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("kickoff twemproxy:  failed by dns,proxy=%s,err=%s",
				proxyIns.ShowSwitchInstanceInfo(), err.Error()))
			return err
		}
		err = proxyIns.KickOffPolaris()
		if err != nil {
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("kickoff twemproxy:  failed by polaris,proxy=%s,err=%s",
				proxyIns.ShowSwitchInstanceInfo(), err.Error()))
			return err
		}
		err = proxyIns.KickOffClb()
		if err != nil {
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("kickoff twemproxy:  failed by clb,proxy=%s,err=%s",
				proxyIns.ShowSwitchInstanceInfo(), err.Error()))
			return err
		}
	}

	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("kickoff twemproxy: done kickoff by [%s:%d]", proxy.Ip, proxy.Port))
	return nil
}

// TwemproxySwitchM2S twemproxy switch master and slave role
func (ins *RedisSwitch) TwemproxySwitchM2S(masterIp string, masterPort int, slaveIp string, slavePort int) error {
	var successSwitchNum int64 = 0
	var wg sync.WaitGroup
	masterAddr, slaveAddr := fmt.Sprintf("%s:%d", masterIp, masterPort), fmt.Sprintf("%s:%d", slaveIp, slavePort)
	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("twemproxy switch: from master[%s] -> slave[%s] begin, proxies{%d}.",
			masterAddr, slaveAddr, len(ins.Proxy)))
	notRunningCnt := 0
	for _, proxy := range ins.Proxy {
		if proxy.Status != "running" {
			notRunningCnt++
		}
		wg.Add(1)
		go func(proxyInfo dbutil.ProxyInfo) {
			defer wg.Done()
			log.Logger.Infof("twemproxy switch: [%s:%d:%d] switch, from master[%s] -> slave[%s] begin .",
				proxyInfo.Ip, proxyInfo.Port, proxyInfo.AdminPort, masterAddr, slaveAddr)

			var rsp string
			var err error
			for i := 0; i < 10; i++ { // read: connection reset by peer
				if rsp, err = ins.DoSwitchTwemproxyBackends(proxyInfo.Ip, proxyInfo.AdminPort, masterAddr, slaveAddr); err != nil {
					ins.ReportLogs(constvar.WarnResult,
						fmt.Sprintf("twemproxy switch: [%s:%d] switch from %s to %s failed, retry:%d, err:%s",
							proxyInfo.Ip, proxyInfo.Port, masterAddr, slaveAddr, i+1, err.Error()))
					time.Sleep(time.Second)
				} else {
					break
				}
			}

			if err != nil {
				redisErr := fmt.Errorf("twemproxy switch: [%s:%d] switch from %s to %s failed, err:%s",
					proxyInfo.Ip, proxyInfo.Port, masterAddr, slaveAddr, err.Error())
				ins.ReportLogs(constvar.FailResult, redisErr.Error())
				return
			}

			if !strings.Contains(rsp, "success") {
				redisErr := fmt.Errorf("twemproxy switch: [%s:%d] switch from  %s to %s failed:%s",
					proxyInfo.Ip, proxyInfo.Port, masterAddr, slaveAddr, rsp)
				ins.ReportLogs(constvar.FailResult, redisErr.Error())
				return
			}

			log.Logger.Infof("twemproxy switch: [%s:%d:%d] switch, from master[%s] -> slave[%s] %s .",
				proxyInfo.Ip, proxyInfo.Port, proxyInfo.AdminPort, masterAddr, slaveAddr, rsp)
			atomic.AddInt64(&successSwitchNum, 1)
		}(proxy)
	}
	wg.Wait()

	if int(successSwitchNum) == len(ins.Proxy) {
		ins.ReportLogs(constvar.InfoResult,
			fmt.Sprintf("twemproxy switch: from master[%s] -> slave[%s] switched successfuly {total:%d==succ:%d}",
				masterAddr, slaveAddr, len(ins.Proxy), successSwitchNum))
		return nil
	}
	//	ignore status !=running
	if int(successSwitchNum)+notRunningCnt >= len(ins.Proxy) {
		ins.ReportLogs(constvar.FailResult,
			fmt.Sprintf("twemproxy switch: partly proxy switched [tota:%d, succ:%d , norunning:%d]",
				len(ins.Proxy), successSwitchNum, notRunningCnt))
		return nil
	}

	ins.ReportLogs(constvar.FailResult,
		fmt.Sprintf("twemproxy switch: partly proxy switched [tota:%d != succ:%d]", len(ins.Proxy), successSwitchNum))
	return fmt.Errorf("partly proxy switched [tota:%d != succ:%d]", len(ins.Proxy), successSwitchNum)
}

// DoSwitchTwemproxyBackends "change nosqlproxy $mt:$mp $st:$sp"
func (ins *RedisSwitch) DoSwitchTwemproxyBackends(ip string, port int, from, to string) (rst string, err error) {
	nc, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", ip, port), time.Second)
	if err != nil {
		return "nil", err
	}
	defer nc.Close()
	_, err = nc.Write([]byte(fmt.Sprintf("change nosqlproxy %s %s", from, to)))
	if err != nil {
		return "nil", err
	}
	return bufio.NewReader(nc).ReadString('\n')
}

// GetTwemProxyBackendsMD5 获取MD5 sum
func (ins *RedisSwitch) GetTwemProxyBackendsMD5(ip string, adminPort int) (map[string]string, string, error) {
	segsMap, err := ins.GetTwemproxyBackends(ip, adminPort)
	if err != nil {
		return nil, "errFailed", err
	}
	segList := []string{}
	for addr, seg := range segsMap {
		segList = append(segList, fmt.Sprintf("%s|%s", addr, seg))
	}
	sort.Slice(segList, func(i, j int) bool {
		return segList[i] > segList[j]
	})

	x, _ := json.Marshal(segList)
	return segsMap, fmt.Sprintf("%x", md5.Sum(x)), nil
}

// GetTwemproxyBackends get nosqlproxy servers
func (ins *RedisSwitch) GetTwemproxyBackends(ip string, adminPort int) (segs map[string]string, err error) {
	addr := fmt.Sprintf("%s:%d", ip, adminPort)
	nc, err := net.DialTimeout("tcp", addr, time.Second)
	if err != nil {
		return nil, err
	}
	defer nc.Close()
	if _, err = nc.Write([]byte("get nosqlproxy servers")); err != nil {
		return nil, err
	}
	reader := bufio.NewReader(nc)
	segs = make(map[string]string)
	for {
		line, _, err := reader.ReadLine()
		if err != nil {
			if err == io.EOF {
				break
			}
			return nil, err
		}
		//1.a.b.c:30111 app 388500-391999 1
		strws := strings.Split(string(line), " ")
		if len(strws) == 4 {
			segs[strws[2]] = strws[0]
		}
	}
	return segs, nil
}

// CheckSlaveSyncStatus 	// 5. 检查同步状态
func (ins *RedisSwitch) CheckSlaveSyncStatus(masterIp string, masterPort int, slaveIp string, slavePort int) error {
	slaveAddr, slaveConn := fmt.Sprintf("%s:%d", slaveIp, slavePort), &client.RedisClient{}
	masterAddr := fmt.Sprintf("%s:%d", masterIp, masterPort)
	if ins.Pass == "" {
		ins.Pass = GetPassByClusterID(ins.GetClusterId(), ins.GetMetaType())
	}
	slaveConn.Init(slaveAddr, ins.Pass, ins.Timeout, 1)
	defer slaveConn.Close()

	replic, err := slaveConn.InfoV2("replication")
	if err != nil {
		return fmt.Errorf("[%s] new master node, exec info failed, err:%+v", slaveAddr, err)
	}
	ins.ReportLogs(constvar.InfoResult,
		fmt.Sprintf("redis switch precheck: slave replication info %s:%+v", slaveAddr, replic))

	if replic["role"] != "slave" {
		err := fmt.Errorf("unexpected status role:%s != SLAVE", replic["role"])
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("redis switch precheck: (%s) : %s", slaveAddr, err.Error()))
		return err
	}

	realMasterIP, realMasterPort := replic["master_host"], replic["master_port"]
	if masterIp != realMasterIP || strconv.Itoa(masterPort) != realMasterPort {
		err := fmt.Errorf("unexpected status: confied:%s:%d, but running:%s:%s",
			masterIp, masterPort, realMasterIP, realMasterPort)
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("redis switch precheck: (%s) : %s", slaveAddr, err.Error()))
		return err
	}

	// master_last_io_seconds_ago:-1 master_link_status:down master_link_down_since_seconds:160  master_port:30001
	// master_last_io_seconds_ago:114 master_link_status:up master_port:30000 master_repl_offset:2113331 master |
	if err := ins.checkReplicationSync(slaveConn, masterAddr, slaveAddr); err != nil {
		err := fmt.Errorf("unexpected status master_sync_status:%s", err)
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("redis switch precheck: (%s) : %s", slaveAddr, err.Error()))
		return err
	}

	lastIOseconds, _ := strconv.Atoi(replic["master_last_io_seconds_ago"])
	if lastIOseconds > MaxLastIOSecondsAgo {
		err := fmt.Errorf("unexpected status master_last_io_seconds_ago:%d(%d)", lastIOseconds, MaxLastIOSecondsAgo)
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("redis switch precheck: (%s) :  %s", slaveAddr, err.Error()))
		return err
	}

	return nil
}

// checkReplicationSync # here we just check the master heartbeat:
func (ins *RedisSwitch) checkReplicationSync(newMasterConn *client.RedisClient,
	masterAddr, slaveAddr string) (err error) {
	var masterTime, slaveTime int64

	rst, err := newMasterConn.Get(fmt.Sprintf("%s:time", masterAddr))
	if err != nil {
		return fmt.Errorf("[%s]new master node, exec cmd err:%+v", masterAddr, err)
	}
	if masterTime, err = strconv.ParseInt(rst, 10, 64); err != nil {
		return fmt.Errorf("[%s]new master node, time2Int64 err:%+v", masterAddr, err)
	}

	slaveTime = time.Now().Unix() // here gcs.perl use redis-cli time

	slaveMasterDiffTime := math.Abs(float64(slaveTime) - float64(masterTime))
	if slaveMasterDiffTime > MaxLastIOSecondsAgo {
		return fmt.Errorf("err master slave sync too long %s => %s diff: %.0f(%d)",
			masterAddr, slaveAddr, slaveMasterDiffTime, MaxLastIOSecondsAgo)
	}

	log.Logger.Infof("[%s]new master node, master on slave time:%d, diff:%.0f slave time:%d",
		slaveAddr, masterTime, slaveMasterDiffTime, slaveTime)
	return nil
}

// IsSlave check instance is slave or not
func (ins *RedisSwitch) IsSlave() bool {
	return strings.Contains(ins.Role, "slave")
}

// GetRole get the role of instance
func (ins *RedisSwitch) GetRole() string {
	return ins.Role
}
