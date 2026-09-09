/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package redisswitch

import (
	"context"
	"fmt"
	"math"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"dbm-services/common/dbha-v2/pkg/storage/haredis"
)

const (
	maxLastIOSecondsAgo      = 600
	twemproxySwitchMaxRetry  = 10
	twemproxySwitchRetryWait = 500 * time.Millisecond
)

var (
	_ switchcore.SwitchableInstance        = (*RedisStorageSwitchInstance)(nil)
	_ switchcore.InstanceNewMasterProvider = (*RedisStorageSwitchInstance)(nil)
)

// RedisStorageSwitchInstance handles tendiscache/tendisssd/tendisplus master-slave switch.
type RedisStorageSwitchInstance struct {
	RedisBaseSwitchInstance

	ProxyList    []dbm.DbmMetadataProxyInstance
	SlaveList    []dbm.DbmMetadataSlaveInfo
	StandBySlave *dbm.DbmMetadataSlaveInfo
}

// NewRedisStorageSwitchInstance creates a redis storage switch instance from metadata.
func NewRedisStorageSwitchInstance(metadata *dbm.DbInstMetadata) (*RedisStorageSwitchInstance, error) {
	if metadata == nil {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "nil metadata for redis storage switch instance")
	}

	ins := &RedisStorageSwitchInstance{
		ProxyList: metadata.ProxyInstanceSet,
		SlaveList: metadata.Receiver,
	}
	ins.initBaseInfoFromMetadata(metadata)
	return ins, nil
}

// errorToString returns the error message as string.
func errorToString(err error) string {
	if err == nil {
		return "nil"
	}
	return err.Error()
}

// ProxyStatusIsRunning checks whether the proxy status is running.
func (ins *RedisStorageSwitchInstance) ProxyStatusIsRunning(proxy dbm.DbmMetadataProxyInstance) bool {
	return proxy.Status == dbm.Running
}

// GetTwemProxyBackends returns the backend map of the twemproxy.
func (ins *RedisStorageSwitchInstance) GetTwemProxyBackends(
	ip string, adminPort int,
) (haredis.TwemproxyServerMap, error) {
	cli, err := haredis.NewTwemproxyAdminClient(
		haredis.OptionIP(ip),
		haredis.OptionPort(adminPort),
	)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to create twemproxy admin client, ip:%s, adminPort:%d, err:%s", ip, adminPort, err.Error())
	}
	return cli.GetServerMap()
}

// unbindFailedTwemproxyFromNameService re-queries metadata and unbinds one failed twemproxy.
func (ins *RedisStorageSwitchInstance) unbindFailedTwemproxyFromNameService(
	bkCloudID int, proxy dbm.DbmMetadataProxyInstance,
) error {
	ins.ReportLogf(switchlogger.SwitchInfo,
		"try to unbind failure twemproxy from name service, ip:%s, port:%d, adminPort:%d, status:%s",
		proxy.Ip, proxy.Port, proxy.AdminPort, proxy.Status)

	// step 1: query metadata of failure twemproxy
	timeout := config.Cfg.Workflow.DbmApiMetadata.Timeout
	if timeout <= 0 {
		timeout = defaultRedisSwitchTimeout
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	_, infos, err := ins.DbmClient.QueryMetadataFromDbm(ctx, bkCloudID, []string{proxy.Ip})
	if err != nil {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to query metadata of failure twemproxy, ip:%s, port:%d, adminPort:%d, err:%s",
			proxy.Ip, proxy.Port, proxy.AdminPort, err.Error())
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	var meta *dbm.DbInstMetadata
	for _, info := range infos {
		if info == nil {
			continue
		}
		if info.IP == proxy.Ip && info.Port == proxy.Port &&
			info.MachineType == haprobe.DbmMetadataMachineTypeTwemProxy {
			meta = info
			break
		}
	}
	if meta == nil {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to find twemproxy metadata from query metadata, ip:%s, port:%d, adminPort:%d",
			proxy.Ip, proxy.Port, proxy.AdminPort)
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	// step 2: create twemproxy switch instance
	proxyIns, err := NewTwemproxySwitchInstance(meta)
	if err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to create twemproxy switch instance, err:%s", err.Error())
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}
	proxyIns.copySwitchContextFrom(&ins.RedisBaseSwitchInstance)

	// step 3: unbind twemproxy from all entries
	if proxyIns.GetStatus() == dbm.Unavailable {
		ins.ReportLogf(switchlogger.SwitchInfo,
			"skip unbinding failure twemproxy from name service for unavailable status, twemproxy: %s",
			proxyIns.GetInstanceInfo())
		return nil
	}

	if !proxyIns.unbindFromAllEntries() {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to unbind failure twemproxy from name service, twemproxy: %s",
			proxyIns.GetInstanceInfo())
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully unbind failure twemproxy from name service, twemproxy: %s",
		proxyIns.GetInstanceInfo())
	return nil
}

// ProcessFailedTwemproxies unbinds unreachable twemproxies from name services.
func (ins *RedisStorageSwitchInstance) ProcessFailedTwemproxies(
	failedProxies []dbm.DbmMetadataProxyInstance,
) error {
	if len(failedProxies) == 0 {
		ins.ReportLogf(switchlogger.SwitchInfo, "no failed twemproxies to process")
		return nil
	}

	twemproxyListStr, _ := converter.ToJsonLine(failedProxies)
	ins.ReportLogf(switchlogger.SwitchInfo,
		"there are failed twemproxies need to process, total:%d, twemproxyList:%s",
		len(failedProxies), twemproxyListStr)

	successCnt := 0
	unbindFailed := make([]dbm.DbmMetadataProxyInstance, 0)
	for _, proxy := range failedProxies {
		if err := ins.unbindFailedTwemproxyFromNameService(ins.BkCloudID, proxy); err != nil {
			unbindFailed = append(unbindFailed, proxy)
			continue
		}
		successCnt++
	}

	if len(unbindFailed) > 0 {
		failedListStr, _ := converter.ToJsonLine(unbindFailed)
		return gerrors.Newf(gerrors.Failure,
			"failed to process some twemproxies, total:%d, success:%d, failed:%d, failedList:%s",
			len(failedProxies), successCnt, len(unbindFailed), failedListStr)
	}
	return nil
}

// CheckTwemproxyBackends checks backend consistency of running twemproxies.
func (ins *RedisStorageSwitchInstance) CheckTwemproxyBackends() error {
	var wg sync.WaitGroup
	var proxyLock sync.Mutex
	failedProxies := make([]dbm.DbmMetadataProxyInstance, 0) // proxies that failed backend query
	proxyServers := map[string]haredis.TwemproxyServerMap{}  // proxy addr -> backend map
	skipped := 0                                             // skipped proxy count

	for _, proxy := range ins.ProxyList {
		wg.Add(1)
		go func(proxyInfo dbm.DbmMetadataProxyInstance) {
			defer wg.Done()
			serverMap, err := ins.GetTwemProxyBackends(proxyInfo.Ip, proxyInfo.AdminPort)

			proxyLock.Lock()
			defer proxyLock.Unlock()

			if err != nil {
				if !ins.ProxyStatusIsRunning(proxyInfo) {
					skipped++
					ins.ReportLogf(switchlogger.SwitchWarn,
						"skip not running twemproxy after backend query failed, ip:%s, port:%d, status:%s, err:%s",
						proxyInfo.Ip, proxyInfo.AdminPort, proxyInfo.Status, err.Error())
					return
				}

				ins.ReportLogf(switchlogger.SwitchWarn, "failed to query backends from twemproxy, ip:%s, port:%d, err:%s",
					proxyInfo.Ip, proxyInfo.AdminPort, err.Error())
				failedProxies = append(failedProxies, proxyInfo)
				return
			}

			if !ins.ProxyStatusIsRunning(proxyInfo) {
				skipped++
				ins.ReportLogf(switchlogger.SwitchInfo,
					"skip not running twemproxy after backend query success, ip:%s, port:%d, status:%s, backendMD5:%s",
					proxyInfo.Ip, proxyInfo.AdminPort, proxyInfo.Status, serverMap.MD5String())
				return
			}

			proxyAddr := fmt.Sprintf("%s:%d", proxyInfo.Ip, proxyInfo.Port)
			proxyServers[proxyAddr] = serverMap
		}(proxy)
	}
	wg.Wait()

	ins.ReportLogf(switchlogger.SwitchInfo,
		"twemproxy backends query done, total:%d, skipped:%d, success:%d, failed:%d",
		len(ins.ProxyList), skipped, len(proxyServers), len(failedProxies))

	if err := ins.ProcessFailedTwemproxies(failedProxies); err != nil {
		ins.ReportLogf(switchlogger.SwitchWarn,
			"not all failed twemproxies are processed successfully, err:%s", err.Error())
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully processed all the failed twemproxies")

	proxyMd5Map := map[string][]string{} // backend MD5 -> proxy addr list
	for addr, serverMap := range proxyServers {
		pmd5 := serverMap.MD5String()
		proxyMd5Map[pmd5] = append(proxyMd5Map[pmd5], addr)
	}
	proxyMd5MapStr, _ := converter.ToJsonLine(proxyMd5Map)
	ins.ReportLogf(switchlogger.SwitchInfo,
		"twemproxy backends servers md5 summary: %s", proxyMd5MapStr)

	if len(proxyMd5Map) != 1 {
		ins.ReportLogf(switchlogger.SwitchWarn, "expected one twemproxy backend md5, but got %d", len(proxyMd5Map))
		for oneMd5, proxyAddrList := range proxyMd5Map {
			if len(proxyAddrList) > 0 {
				ins.ReportLogf(switchlogger.SwitchWarn,
					"check inconsistent twemproxy backends, md5:%s, backends:%s, proxyCount:%d",
					oneMd5, proxyServers[proxyAddrList[0]], len(proxyAddrList))
			}
		}
		return gerrors.Newf(gerrors.Failure,
			"expected the same twemproxy backend md5, but got different md5s, md5Count:%d", len(proxyMd5Map))
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "backends settings for all running twemproxy are consistent")
	return nil
}

// generateHeartbeatKey generates the heartbeat key.
func (ins *RedisStorageSwitchInstance) generateHeartbeatKey(ip string, port int) string {
	return fmt.Sprintf("%s:%d:time", ip, port)
}

// checkReplicationSync checks the replication sync delay of the slave.
func (ins *RedisStorageSwitchInstance) checkReplicationSync(slaveConn *haredis.Client) error {
	heartbeatKey := ins.generateHeartbeatKey(ins.IP, ins.Port)
	cmdCtx, cancel := ins.commandContext()
	defer cancel()

	heartbeatValue, err := slaveConn.DB().Get(cmdCtx, heartbeatKey).Result()
	if err == haredis.RedisNil {
		return gerrors.Newf(gerrors.Failure,
			"heartbeat key does not exist on slave, heartbeatKey: %s, slaveIp: %s, slavePort: %d",
			heartbeatKey, slaveConn.Host(), slaveConn.Port())
	}
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to get heartbeat value from slave, heartbeatKey: %s, slaveIp: %s, slavePort: %d, err: %s",
			heartbeatKey, slaveConn.Host(), slaveConn.Port(), err.Error())
	}

	masterTime, err := strconv.ParseInt(heartbeatValue, 10, 64)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to parse heartbeat time, heartbeatTime: %s, slaveIp: %s, slavePort: %d, err: %s",
			heartbeatValue, slaveConn.Host(), slaveConn.Port(), err.Error())
	}

	slaveTime := time.Now().Unix()
	slaveMasterDiffTime := math.Abs(float64(slaveTime) - float64(masterTime))
	if slaveMasterDiffTime > maxLastIOSecondsAgo {
		return gerrors.Newf(gerrors.Failure,
			"replication heartbeat delay exceeds allowed time, slaveIp: %s, slavePort: %d, "+
				"heartbeat: %d, now: %d, diff: %.0f, allowedMaxDelay: %d",
			slaveConn.Host(), slaveConn.Port(), masterTime, slaveTime, slaveMasterDiffTime, maxLastIOSecondsAgo)
	}

	ins.ReportLogf(switchlogger.SwitchInfo,
		"replication heartbeat delay is acceptable, slaveIp: %s, slavePort: %d, "+
			"heartbeat: %d, now: %d, diff: %.0f, allowedMaxDelay: %d",
		slaveConn.Host(), slaveConn.Port(), masterTime, slaveTime, slaveMasterDiffTime, maxLastIOSecondsAgo)
	return nil
}

// CheckSlaveSyncStatus checks replication status of the candidate new master.
func (ins *RedisStorageSwitchInstance) CheckSlaveSyncStatus() error {
	if ins.StandBySlave == nil {
		return gerrors.Newf(gerrors.Failure, "standby slave is not set when checking slave sync status")
	}

	slaveIp := ins.StandBySlave.Ip
	slavePort := ins.StandBySlave.Port

	slaveConn, err := ins.buildRedisConn(slaveIp, slavePort, redisHeartbeatDB)
	if err != nil {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to connect to slave when checking sync status, slaveIp: %s, slavePort: %d, err: %s",
			slaveIp, slavePort, err.Error())
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}
	defer slaveConn.Close()

	cmdCtx, cancel := ins.commandContext()
	defer cancel()

	raw, err := slaveConn.DB().Info(cmdCtx, "replication").Result()
	if err != nil {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to query replication info from slave, slaveIp: %s, slavePort: %d, err: %s",
			slaveIp, slavePort, err.Error())
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchInfo,
		"successfully get replication info from slave, slaveIp: %s, slavePort: %d, info: %s",
		slaveIp, slavePort, raw)

	replic := parseRedisInfo(raw)

	if replic["role"] != "slave" {
		retErr := gerrors.Newf(gerrors.Failure,
			"the role of slave is not slave, slaveIp: %s, slavePort: %d, role: %s",
			slaveIp, slavePort, replic["role"])
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	realMasterIP, realMasterPort := replic["master_host"], replic["master_port"]
	if (ins.IP != realMasterIP) || (strconv.Itoa(ins.Port) != realMasterPort) {
		retErr := gerrors.Newf(gerrors.Failure,
			"the slave is replicating from another master, slaveIp: %s, slavePort: %d, realMasterIp: %s, realMasterPort: %s",
			slaveIp, slavePort, realMasterIP, realMasterPort)
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	// check the replication sync delay of the slave
	if err := ins.checkReplicationSync(slaveConn); err != nil {
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return err
	}

	lastIOseconds, _ := strconv.Atoi(replic["master_last_io_seconds_ago"])
	if lastIOseconds > maxLastIOSecondsAgo {
		retErr := gerrors.Newf(gerrors.Failure,
			"master_last_io_seconds_ago of slave exceeds allowed time, "+
				"slaveIp: %s, slavePort: %d, master_last_io_seconds_ago: %d, allowedMax: %d",
			slaveIp, slavePort, lastIOseconds, maxLastIOSecondsAgo)
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	return nil
}

// setStandBySlave picks SlaveList[0] as the candidate new master.
func (ins *RedisStorageSwitchInstance) setStandBySlave() error {
	if len(ins.SlaveList) < 1 {
		ins.StandBySlave = nil
		return gerrors.Newf(gerrors.Failure, "no slave found for the master")
	}

	slave := ins.SlaveList[0]
	ins.StandBySlave = &slave

	slaveList, _ := converter.ToJsonLine(ins.SlaveList)
	standBySlaveStr, _ := converter.ToJsonLine(ins.StandBySlave)
	ins.ReportLogf(switchlogger.SwitchInfo, "slave list: %s, chosen standby slave: %s", slaveList, standBySlaveStr)
	return nil
}

// CheckRedisStorageMaster checks a redis storage master before switch.
func (ins *RedisStorageSwitchInstance) CheckRedisStorageMaster() (switchcore.SwitchCheckCode, error) {
	if err := ins.setStandBySlave(); err != nil {
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	// if the proxy layer is twemproxy, check the twemproxy backends consistency
	if isTwemproxyClusterType(ins.ClusterType) {
		if err := ins.CheckTwemproxyBackends(); err != nil {
			ins.ReportLogf(switchlogger.SwitchWarn, "twemproxy backends check unpass, err:%s", err.Error())
			return switchcore.SwitchCheckUnpass, err
		}
	}

	// check the replication sync status of the slave
	if err := ins.CheckSlaveSyncStatus(); err != nil {
		ins.ReportLogf(switchlogger.SwitchWarn, "slave sync check unpass, err: %s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	ins.ReportLogf(switchlogger.SwitchInfo,
		"redis switch precheck: lock file and check twemproxy and sync status ok; next ^_^")
	return switchcore.SwitchRequired, nil
}

// CheckBeforeSwitch checks redis status before switch.
func (ins *RedisStorageSwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	if isClusterProtocolClusterType(ins.ClusterType) {
		ins.ReportLogf(switchlogger.SwitchInfo, "this is a cluster protocol storage node, no need to switch")
		return switchcore.SwitchNotNeeded, nil
	}

	switch ins.InstanceRole {
	case haprobe.RedisStorageSlave:
		ins.ReportLogf(switchlogger.SwitchInfo, "this is a redis storage slave node, no need to switch")
		return switchcore.SwitchNotNeeded, nil

	case haprobe.RedisStorageMaster:
		return ins.CheckRedisStorageMaster()

	default:
		err := gerrors.Newf(gerrors.Failure, "invalid instance role: %s", ins.InstanceRole)
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}
}

// DoSwitchTwemproxyBackends sends "change nosqlproxy $from $to" and retries on send/read errors.
func (ins *RedisStorageSwitchInstance) DoSwitchTwemproxyBackends(
	ip string, port int, from, to string, maxRetry int,
) (string, error) {
	if maxRetry <= 0 {
		maxRetry = twemproxySwitchMaxRetry
	}

	cli, err := haredis.NewTwemproxyAdminClient(
		haredis.OptionIP(ip),
		haredis.OptionPort(port),
	)
	if err != nil {
		return "", gerrors.Newf(gerrors.Failure,
			"failed to create twemproxy admin client, ip:%s, port:%d, err:%s", ip, port, err.Error())
	}

	var rsp string
	for i := 0; i < maxRetry; i++ { // retry here because of concurrent writers (read: connection reset by peer)
		rsp, err = cli.ChangeBackend(from, to)
		if err == nil {
			return rsp, nil
		}

		ins.ReportLogf(switchlogger.SwitchWarn,
			"failed to switch twemproxy backends, ip:%s, port:%d, from:%s, to:%s, retry:%d, err:%s",
			ip, port, from, to, i+1, err.Error())
		if i+1 < maxRetry {
			time.Sleep(twemproxySwitchRetryWait)
		}
	}
	return rsp, err
}

// SwitchTwemproxyBackends switches backends from master to slave on every twemproxy.
func (ins *RedisStorageSwitchInstance) SwitchTwemproxyBackends(
	masterIp string, masterPort int, slaveIp string, slavePort int,
) error {
	var wg sync.WaitGroup
	var proxyLock sync.Mutex
	failedProxies := make([]dbm.DbmMetadataProxyInstance, 0)
	successCnt := 0
	notRunningCnt := 0

	masterAddr := fmt.Sprintf("%s:%d", masterIp, masterPort)
	slaveAddr := fmt.Sprintf("%s:%d", slaveIp, slavePort)
	ins.ReportLogf(switchlogger.SwitchInfo,
		"start to switch twemproxy backends, from:%s, to:%s, proxyTotalCount:%d",
		masterAddr, slaveAddr, len(ins.ProxyList))

	for _, proxy := range ins.ProxyList {
		if !ins.ProxyStatusIsRunning(proxy) {
			notRunningCnt++
		}

		wg.Add(1)
		go func(proxyInfo dbm.DbmMetadataProxyInstance) {
			defer wg.Done()
			twemproxyInfo := fmt.Sprintf("ip:%s, port:%d, status:%s", proxyInfo.Ip, proxyInfo.AdminPort, proxyInfo.Status)
			switchInfo := fmt.Sprintf("%s -> %s", masterAddr, slaveAddr)

			rsp, err := ins.DoSwitchTwemproxyBackends(
				proxyInfo.Ip, proxyInfo.AdminPort, masterAddr, slaveAddr, twemproxySwitchMaxRetry)

			proxyLock.Lock()
			defer proxyLock.Unlock()

			if (err != nil) || !strings.Contains(rsp, "success") {
				ins.ReportLogf(switchlogger.SwitchWarn,
					"failed to switch twemproxy backends, twemproxy:%s, backendSwitch:%s, resp:%s, err:%s",
					twemproxyInfo, switchInfo, rsp, errorToString(err))
				failedProxies = append(failedProxies, proxyInfo)
				return
			}

			ins.ReportLogf(switchlogger.SwitchInfo,
				"successfully switched twemproxy backends, twemproxy:%s, backendSwitch:%s, resp:%s",
				twemproxyInfo, switchInfo, rsp)
			successCnt++
		}(proxy)
	}
	wg.Wait()

	failedListStr, _ := converter.ToJsonLine(failedProxies)
	ins.ReportLogf(switchlogger.SwitchInfo,
		"twemproxy backends switch done, total:%d, notRunning:%d, success:%d, failed:%d, failedList:%s",
		len(ins.ProxyList), notRunningCnt, successCnt, len(failedProxies), failedListStr)

	if successCnt == len(ins.ProxyList) {
		ins.ReportLogf(switchlogger.SwitchInfo,
			"successfully switched backends for all twemproxies, from:%s, to:%s", masterAddr, slaveAddr)
		return nil
	}

	runningFailed := make([]dbm.DbmMetadataProxyInstance, 0)
	for _, proxy := range failedProxies {
		if ins.ProxyStatusIsRunning(proxy) {
			runningFailed = append(runningFailed, proxy)
		}
	}

	if len(runningFailed) > 0 {
		runningFailedStr, _ := converter.ToJsonLine(runningFailed)
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to switch backends for some running twemproxies, failedCount:%d, failedList:%s",
			len(runningFailed), runningFailedStr)
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchWarn,
		"failed to switch backends for some not running twemproxies, ignore and continue, failedCount:%d, failedList:%s",
		len(failedProxies), failedListStr)
	return nil
}

// DoSwitch promotes the first slave with SLAVEOF NO ONE, then switches twemproxy backends if needed.
func (ins *RedisStorageSwitchInstance) DoSwitch() error {
	ins.ReportLogf(switchlogger.SwitchInfo, "try to switch redis instance, instance info: %s", ins.GetInstanceInfo())

	if ins.StandBySlave == nil {
		retErr := gerrors.Newf(gerrors.Failure, "standby slave is not set when doing switch")
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}
	slaveIp := ins.StandBySlave.Ip
	slavePort := ins.StandBySlave.Port

	slaveConn, err := ins.buildRedisConn(slaveIp, slavePort, redisSwitchDB)
	if err != nil {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to connect to slave when doing switch, slaveIp: %s, slavePort: %d, err: %s",
			slaveIp, slavePort, err.Error())
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}
	defer slaveConn.Close()

	cmdCtx, cancel := ins.commandContext()
	defer cancel()

	// break the replication relationship with the master
	resp, err := slaveConn.DB().SlaveOf(cmdCtx, "no", "one").Result()
	if (err != nil) || !strings.Contains(resp, "OK") {
		retErr := gerrors.Newf(gerrors.Failure,
			"failed to execute 'slaveof no one', slaveIp: %s, slavePort: %d, resp: %s, err: %s",
			slaveIp, slavePort, resp, errorToString(err))
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully executed 'slaveof no one', slaveIp: %s, slavePort: %d, resp: %s",
		slaveIp, slavePort, resp)

	if isTwemproxyClusterType(ins.ClusterType) {
		if err := ins.SwitchTwemproxyBackends(ins.IP, ins.Port, slaveIp, slavePort); err != nil {
			return err
		}
	}
	return nil
}

// UpdateMetaInfo swaps roles of redis master and slave
func (ins *RedisStorageSwitchInstance) UpdateMetaInfo() error {
	if ins.InstanceRole != haprobe.RedisStorageMaster {
		ins.ReportLogf(switchlogger.SwitchInfo, "nothing to do for the instance role(%s) when updating meta info",
			ins.InstanceRole)
		return nil
	}

	if ins.StandBySlave == nil {
		retErr := gerrors.Newf(gerrors.Failure, "standby slave is not set when updating meta info")
		ins.ReportLogf(switchlogger.SwitchWarn, "%s", retErr.Error())
		return retErr
	}

	err := SwapRedisRole(ins.DbmClient, ins.BkCloudID, ins.Cluster, ins.IP, ins.Port,
		ins.StandBySlave.Ip, ins.StandBySlave.Port)
	if err != nil {
		errMsg := fmt.Sprintf("failed to swap roles of redis nodes, master:%s:%d, slave:%s:%d, err:%s",
			ins.IP, ins.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port, err.Error())
		ins.ReportLog(switchlogger.SwitchWarn, errMsg)
		return err
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully swap roles of redis nodes, master:%s:%d, slave:%s:%d",
		ins.IP, ins.Port, ins.StandBySlave.Ip, ins.StandBySlave.Port)
	return nil
}

// GetNewMasterInfo returns the promoted slave after a successful master switch.
func (ins *RedisStorageSwitchInstance) GetNewMasterInfo() (*switchcore.NewMasterInfo, bool) {
	if ins.StandBySlave == nil {
		return nil, false
	}
	return &switchcore.NewMasterInfo{
		Host: ins.StandBySlave.Ip,
		Port: ins.StandBySlave.Port,
	}, true
}
