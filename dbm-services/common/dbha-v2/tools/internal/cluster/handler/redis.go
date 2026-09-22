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

package handler

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/safe"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"dbm-services/common/dbha-v2/pkg/storage/haredis"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/dbm"
)

const (
	redisConnectTimeout = 5 * time.Second
	redisCommandTimeout = 10 * time.Second

	// redisSlaveOfDB is the db index used by SLAVEOF and INFO, matching the switch side.
	redisSlaveOfDB = 0

	// redisSyncWaitTimeout bounds how long a slave may take to report master_link_status:up.
	redisSyncWaitTimeout  = 90 * time.Second
	redisSyncPollInterval = 2 * time.Second

	twemproxyChangeMaxRetry  = 3
	twemproxyChangeRetryWait = 1 * time.Second
)

// RedisClusterHandler resets the redis clusters that dbha-v2 switches.
//
// It only undoes what the switch does. Cluster-protocol clusters
// (PredixyRedisCluster / PredixyTendisplusCluster) elect a new master by themselves and
// dbha-v2 never switches their storage, so this handler never issues CLUSTER commands
// against them and only restores their predixy name-service bindings.
// Predixy backends are likewise left alone: the switch does not rewrite predixy.conf either.
type RedisClusterHandler struct {
	baseHandler
	// clusterType is empty to cover every redis cluster, or one canonical type name.
	clusterType haprobe.DbmMetadataClusterType
}

// NewRedisClusterHandler creates a RedisClusterHandler covering every redis cluster type.
func NewRedisClusterHandler() *RedisClusterHandler {
	return &RedisClusterHandler{baseHandler: newBaseHandler()}
}

// NewRedisClusterHandlerOfType creates a RedisClusterHandler for one redis cluster type.
func NewRedisClusterHandlerOfType(clusterType haprobe.DbmMetadataClusterType) *RedisClusterHandler {
	return &RedisClusterHandler{baseHandler: newBaseHandler(), clusterType: clusterType}
}

var _ ClusterHandler = (*RedisClusterHandler)(nil)

// Reset resets the redis clusters selected by this handler.
func (hdl *RedisClusterHandler) Reset() error {
	return hdl.ResetRedisClusters(hdl.clusterType)
}

func redisAddr(host string, port int) string {
	return host + ":" + strconv.Itoa(port)
}

// storagePassword fetches the password shared by every storage node of the cluster.
func (hdl *RedisClusterHandler) storagePassword(cluster *config.RedisCluster) (string, error) {
	machineType, err := config.RedisStorageMachineType(cluster.ClusterType)
	if err != nil {
		return "", err
	}

	passwd, err := hdl.dbmClient.QueryRedisPassword(cluster.BkCloudId, cluster.ClusterId, machineType)
	if err != nil {
		return "", gerrors.Newf(gerrors.Failure,
			"failed to get %s password of cluster %s (clusterId=%d), errmsg: %s",
			machineType, cluster.Domain, cluster.ClusterId, err.Error())
	}

	return passwd, nil
}

func connectRedis(host string, port int, passwd string) (*haredis.Client, error) {
	cli, err := haredis.NewClient(
		haredis.OptionIP(host),
		haredis.OptionPort(port),
		haredis.OptionPassword(passwd),
		haredis.OptionDB(redisSlaveOfDB),
		haredis.OptionDialTimeout(redisConnectTimeout),
		haredis.OptionReadWriteTimeout(redisCommandTimeout),
	)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to connect to redis node(%s:%d), errmsg: %s",
			host, port, err.Error())
	}
	return cli, nil
}

// parseRedisInfo turns an INFO section into a key-value map. The returned map is never nil.
func parseRedisInfo(info string) map[string]string {
	infoRet := make(map[string]string)
	for _, line := range strings.Split(info, "\n") {
		line = strings.TrimSpace(line)
		if len(line) == 0 || strings.HasPrefix(line, "#") {
			continue
		}
		kv := strings.SplitN(line, ":", 2)
		if len(kv) < 2 {
			continue
		}
		infoRet[strings.TrimSpace(kv[0])] = strings.TrimSpace(kv[1])
	}
	return infoRet
}

func redisReplicationInfo(cli *haredis.Client) (map[string]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), redisCommandTimeout)
	defer cancel()

	info, err := cli.DB().Info(ctx, "replication").Result()
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to get replication info of node(%s:%d), errmsg: %s",
			cli.Host(), cli.Port(), err.Error())
	}

	return parseRedisInfo(info), nil
}

// getInstanceList returns every instance whose DBM status the reset flow updates.
// Storage nodes of a cluster-protocol cluster are left out even when shards are
// configured, because the switch never marks them unavailable in the first place.
func (hdl *RedisClusterHandler) getInstanceList(cluster *config.RedisCluster) []config.InstanceAddress {
	instanceList := hdl.getProxyList(cluster)
	if config.IsClusterProtocolRedisClusterType(cluster.ClusterType) {
		return instanceList
	}

	for _, shard := range cluster.Shards {
		instanceList = append(instanceList, shard.Master)
		instanceList = append(instanceList, shard.Slave...)
	}
	return instanceList
}

func (hdl *RedisClusterHandler) getProxyList(cluster *config.RedisCluster) []config.InstanceAddress {
	return getProxyList(cluster)
}

func (hdl *RedisClusterHandler) printOneCluster(cluster *config.RedisCluster) {
	fmt.Printf("Cluster: %s (%s)\n", cluster.Domain, cluster.ClusterType)
	for _, proxy := range cluster.Proxy {
		fmt.Printf("  Proxy: %s:%d (adminPort: %d)\n", proxy.Host, proxy.Port, proxy.AdminPort)
	}

	// A cluster-protocol cluster keeps its own topology, so any configured shard is
	// reported here and then left untouched for the rest of the reset.
	shardNote := ""
	if config.IsClusterProtocolRedisClusterType(cluster.ClusterType) && len(cluster.Shards) > 0 {
		shardNote = " (ignored: this cluster type manages its own topology)"
	}

	for i, shard := range cluster.Shards {
		fmt.Printf("  Shard[%d] master: %s%s\n", i, redisAddr(shard.Master.Host, shard.Master.Port), shardNote)
		for _, slave := range shard.Slave {
			fmt.Printf("  Shard[%d] slave:  %s%s\n", i, redisAddr(slave.Host, slave.Port), shardNote)
		}
	}
}

// promoteShardMaster makes the configured master writable again with SLAVEOF NO ONE.
func promoteShardMaster(master config.InstanceAddress, passwd string) error {
	cli, err := connectRedis(master.Host, master.Port, passwd)
	if err != nil {
		return err
	}
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), redisCommandTimeout)
	defer cancel()

	if _, err := cli.DB().SlaveOf(ctx, "no", "one").Result(); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to run SLAVEOF NO ONE on node(%s:%d), errmsg: %s",
			master.Host, master.Port, err.Error())
	}

	infoMap, err := redisReplicationInfo(cli)
	if err != nil {
		return err
	}

	if role := infoMap["role"]; role != "master" {
		return gerrors.Newf(gerrors.Failure,
			"node(%s:%d) is still in role %q after SLAVEOF NO ONE", master.Host, master.Port, role)
	}

	return nil
}

// attachShardSlave points one slave at the configured master and waits for the link to come up.
func attachShardSlave(slave, master config.InstanceAddress, passwd string) error {
	cli, err := connectRedis(slave.Host, slave.Port, passwd)
	if err != nil {
		return err
	}
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), redisCommandTimeout)
	defer cancel()

	if _, err := cli.DB().SlaveOf(ctx, master.Host, strconv.Itoa(master.Port)).Result(); err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to run SLAVEOF %s:%d on node(%s:%d), errmsg: %s",
			master.Host, master.Port, slave.Host, slave.Port, err.Error())
	}

	return waitSlaveLinkUp(cli, slave, master)
}

// waitSlaveLinkUp polls INFO replication until the slave reports a live link to the expected master.
func waitSlaveLinkUp(cli *haredis.Client, slave, master config.InstanceAddress) error {
	deadline := time.Now().Add(redisSyncWaitTimeout)

	for {
		infoMap, err := redisReplicationInfo(cli)
		if err != nil {
			return err
		}

		masterPort, _ := strconv.Atoi(infoMap["master_port"])
		if infoMap["role"] == "slave" && infoMap["master_host"] == master.Host &&
			masterPort == master.Port && infoMap["master_link_status"] == "up" {
			return nil
		}

		if time.Now().After(deadline) {
			return gerrors.Newf(gerrors.Failure,
				"timed out after %s waiting for node(%s:%d) to sync from %s:%d, "+
					"last state: role=%s, master=%s:%s, master_link_status=%s",
				redisSyncWaitTimeout, slave.Host, slave.Port, master.Host, master.Port,
				infoMap["role"], infoMap["master_host"], infoMap["master_port"],
				infoMap["master_link_status"])
		}

		time.Sleep(redisSyncPollInterval)
	}
}

// restoreShardReplication rebuilds one master-slave group as described in the config file.
func restoreShardReplication(shard *config.RedisShard, passwd string) error {
	if err := promoteShardMaster(shard.Master, passwd); err != nil {
		return err
	}

	for _, slave := range shard.Slave {
		if slave.Host == shard.Master.Host && slave.Port == shard.Master.Port {
			continue
		}
		if err := attachShardSlave(slave, shard.Master, passwd); err != nil {
			return err
		}
	}

	return nil
}

// restoreReplicationTopology rebuilds every shard concurrently.
//
// While this runs, the proxies still point at whichever node the switch promoted, and that
// node is demoted back to a read-only replica here, so writes fail for a short window. This
// mirrors the window MySQL reset opens when it blackholes the proxy backends.
//
// Demoting that node also makes it resync from the configured master, which drops whatever
// it took after the switch. Reset restores the topology the config file declares, so this
// belongs on a test bed, not on a cluster holding data worth keeping.
func (hdl *RedisClusterHandler) restoreReplicationTopology(cluster *config.RedisCluster, passwd string) error {
	sem := make(chan struct{}, getClusterMaxConcurrency())
	errCh := make(chan error, len(cluster.Shards))
	var wg sync.WaitGroup

	for i := range cluster.Shards {
		wg.Add(1)
		sem <- struct{}{}

		go func(shard *config.RedisShard) {
			defer wg.Done()
			defer func() { <-sem }()

			if err := restoreShardReplication(shard, passwd); err != nil {
				errCh <- err
			}
		}(&cluster.Shards[i])
	}

	wg.Wait()
	close(errCh)

	for err := range errCh {
		if err != nil {
			return err
		}
	}

	return nil
}

// queryShardRoles fetches the DBM role of every storage node of the cluster in one call.
// A redis host usually carries many instances, so asking per instance would multiply the
// requests while each answer already covers the whole host.
func (hdl *RedisClusterHandler) queryShardRoles(cluster *config.RedisCluster) (
	map[string]haprobe.DbmMetadataInstanceRole, error) {
	ipSet := make(map[string]struct{})
	for _, shard := range cluster.Shards {
		ipSet[shard.Master.Host] = struct{}{}
		for _, slave := range shard.Slave {
			ipSet[slave.Host] = struct{}{}
		}
	}

	ips := make([]string, 0, len(ipSet))
	for ip := range ipSet {
		ips = append(ips, ip)
	}

	metadataList, err := hdl.dbmClient.QueryMetadataFromDbm(cluster.BkCloudId, ips)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to query metadata of cluster %s, errmsg: %s", cluster.Domain, err.Error())
	}

	roleMap := make(map[string]haprobe.DbmMetadataInstanceRole, len(metadataList))
	for _, metadata := range metadataList {
		roleMap[redisAddr(metadata.IP, metadata.Port)] = haprobe.DbmMetadataInstanceRole(metadata.InstanceRole)
	}

	return roleMap, nil
}

// correctShardRoles puts the DBM metadata back in line with the config file.
// The swap API takes the pair as DBM currently sees it and swaps the two roles.
func (hdl *RedisClusterHandler) correctShardRoles(cluster *config.RedisCluster) error {
	roleMap, err := hdl.queryShardRoles(cluster)
	if err != nil {
		return err
	}

	for _, shard := range cluster.Shards {
		masterAddr := redisAddr(shard.Master.Host, shard.Master.Port)
		masterRole, ok := roleMap[masterAddr]
		if !ok {
			return gerrors.Newf(gerrors.Failure,
				"node(%s) of cluster %s is unknown to dbm", masterAddr, cluster.Domain)
		}

		if masterRole == haprobe.RedisStorageMaster {
			continue
		}

		curMaster, ok := findShardNodeOfRole(shard, roleMap, haprobe.RedisStorageMaster)
		if !ok {
			return gerrors.Newf(gerrors.Failure,
				"node(%s) is %s in dbm but no slave of the same shard holds role %s",
				masterAddr, masterRole, haprobe.RedisStorageMaster)
		}

		if err := hdl.dbmClient.SwapRedisRole(cluster.BkCloudId, cluster.Domain,
			curMaster.Host, curMaster.Port, shard.Master.Host, shard.Master.Port); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to swap role of (%s:%d) and (%s), errmsg: %s",
				curMaster.Host, curMaster.Port, masterAddr, err.Error())
		}
	}

	return nil
}

// findShardNodeOfRole looks for the shard slave that DBM currently labels with targetRole.
func findShardNodeOfRole(shard config.RedisShard, roleMap map[string]haprobe.DbmMetadataInstanceRole,
	targetRole haprobe.DbmMetadataInstanceRole) (config.InstanceAddress, bool) {
	for _, slave := range shard.Slave {
		if roleMap[redisAddr(slave.Host, slave.Port)] == targetRole {
			return slave, true
		}
	}

	return config.InstanceAddress{}, false
}

// buildTwemproxyBackendMap maps every node of the cluster to the master its shard should serve.
func buildTwemproxyBackendMap(cluster *config.RedisCluster) map[string]string {
	backendMap := make(map[string]string)
	for i := range cluster.Shards {
		shard := &cluster.Shards[i]
		masterAddr := redisAddr(shard.Master.Host, shard.Master.Port)

		backendMap[masterAddr] = masterAddr
		for _, slave := range shard.Slave {
			backendMap[redisAddr(slave.Host, slave.Port)] = masterAddr
		}
	}
	return backendMap
}

// changeTwemproxyBackend sends "change nosqlproxy $from $to", retrying because concurrent
// writers on the admin port make the connection drop with "connection reset by peer".
func changeTwemproxyBackend(host string, adminPort int, from, to string) error {
	cli, err := haredis.NewTwemproxyAdminClient(
		haredis.OptionIP(host),
		haredis.OptionPort(adminPort),
	)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to create twemproxy admin client for %s:%d, errmsg: %s", host, adminPort, err.Error())
	}

	for i := 0; i < twemproxyChangeMaxRetry; i++ {
		if _, err = cli.ChangeBackend(from, to); err == nil {
			return nil
		}
		if i+1 < twemproxyChangeMaxRetry {
			time.Sleep(twemproxyChangeRetryWait)
		}
	}

	return gerrors.Newf(gerrors.Failure,
		"failed to change backend of twemproxy(%s:%d) from %s to %s after %d tries, errmsg: %s",
		host, adminPort, from, to, twemproxyChangeMaxRetry, err.Error())
}

// resetTwemproxyBackends points every twemproxy segment back at its configured shard master.
// The segment id is irrelevant here: the current backend address alone identifies the shard.
func (hdl *RedisClusterHandler) resetTwemproxyBackends(cluster *config.RedisCluster) error {
	backendMap := buildTwemproxyBackendMap(cluster)

	for _, proxy := range cluster.Proxy {
		cli, err := haredis.NewTwemproxyAdminClient(
			haredis.OptionIP(proxy.Host),
			haredis.OptionPort(proxy.AdminPort),
		)
		if err != nil {
			return gerrors.Newf(gerrors.Failure,
				"failed to create twemproxy admin client for %s:%d, errmsg: %s",
				proxy.Host, proxy.AdminPort, err.Error())
		}

		serverMap, err := cli.GetServerMap()
		if err != nil {
			return gerrors.Newf(gerrors.Failure,
				"failed to get backends of twemproxy(%s:%d), errmsg: %s",
				proxy.Host, proxy.AdminPort, err.Error())
		}

		// "change nosqlproxy" matches on the backend address, so a backend serving
		// several segments must be moved once, not once per segment.
		moves := make(map[string]string)
		for seg, curAddr := range serverMap {
			wantAddr, ok := backendMap[curAddr]
			if !ok {
				return gerrors.Newf(gerrors.Failure,
					"twemproxy(%s:%d) serves segment %s from %s, which belongs to no shard in the config file",
					proxy.Host, proxy.AdminPort, seg, curAddr)
			}

			if curAddr != wantAddr {
				moves[curAddr] = wantAddr
			}
		}

		for curAddr, wantAddr := range moves {
			if err := changeTwemproxyBackend(proxy.Host, proxy.AdminPort, curAddr, wantAddr); err != nil {
				return err
			}
		}
	}

	return nil
}

// resetSingleRedisCluster resets a single redis cluster.
// Step 1: update all instances status to unavailable
// Step 2: restore the master-slave topology (skipped for cluster-protocol types)
// Step 3: correct the instance roles in dbm metadata (skipped for cluster-protocol types)
// Step 4: point twemproxy backends back at the configured masters (twemproxy clusters only)
// Step 5: update all instances status to running
// Step 6: add proxies back to the cluster domain
// Step 7: reset clb binding (optional; skip when clb is omitted or empty)
func (hdl *RedisClusterHandler) resetSingleRedisCluster(cluster *config.RedisCluster) error {
	hdl.printOneCluster(cluster)
	logResetf("start to reset cluster, domain: %s, cluster_type: %s", cluster.Domain, cluster.ClusterType)
	instanceList := hdl.getInstanceList(cluster)

	if err := hdl.dbmClient.UpdateAllInstancesStatusInCloud(
		cluster.BkCloudId, instanceList, dbm.StatusUnavailable); err != nil {
		logResetStep(1, "failed to update all instances status to unavailable, domain: %s, errmsg: %s",
			cluster.Domain, err.Error())
		return err
	}
	logResetStep(1, "successfully updated all instances status to unavailable, domain: %s", cluster.Domain)

	switch {
	case config.IsClusterProtocolRedisClusterType(cluster.ClusterType):
		logResetf("reset step 2-4: skip restore storage topology, domain: %s, cluster_type: %s, "+
			"reason: elects a new master by itself", cluster.Domain, cluster.ClusterType)

	case len(cluster.Shards) == 0:
		logResetf("reset step 2-4: skip restore storage topology, domain: %s, reason: no shards configured",
			cluster.Domain)

	default:
		passwd, err := hdl.storagePassword(cluster)
		if err != nil {
			logResetStep(2, "failed to restore master-slave topology, domain: %s, errmsg: %s",
				cluster.Domain, err.Error())
			return err
		}

		if err := hdl.restoreReplicationTopology(cluster, passwd); err != nil {
			logResetStep(2, "failed to restore master-slave topology, domain: %s, errmsg: %s",
				cluster.Domain, err.Error())
			return err
		}
		logResetStep(2, "successfully restored master-slave topology, domain: %s", cluster.Domain)

		if err := hdl.correctShardRoles(cluster); err != nil {
			logResetStep(3, "failed to correct instance roles in dbm, domain: %s, errmsg: %s",
				cluster.Domain, err.Error())
			return err
		}
		logResetStep(3, "successfully corrected instance roles in dbm, domain: %s", cluster.Domain)

		if config.IsTwemproxyRedisClusterType(cluster.ClusterType) {
			if err := hdl.resetTwemproxyBackends(cluster); err != nil {
				logResetStep(4, "failed to reset twemproxy backends, domain: %s, errmsg: %s",
					cluster.Domain, err.Error())
				return err
			}
			logResetStep(4, "successfully reset twemproxy backends, domain: %s", cluster.Domain)
		} else {
			logResetStep(4, "skip reset twemproxy backends, domain: %s, cluster_type: %s, "+
				"reason: no twemproxy layer", cluster.Domain, cluster.ClusterType)
		}
	}

	if err := hdl.dbmClient.UpdateAllInstancesStatusInCloud(
		cluster.BkCloudId, instanceList, dbm.StatusRunning); err != nil {
		logResetStep(5, "failed to update all instances status to running, domain: %s, errmsg: %s",
			cluster.Domain, err.Error())
		return err
	}
	logResetStep(5, "successfully updated all instances status to running, domain: %s", cluster.Domain)

	// Only proxies are unbound from the name service by the switch, so a proxyless
	// cluster type such as RedisInstance has no domain binding to restore.
	if proxyList := hdl.getProxyList(cluster); len(proxyList) > 0 {
		if err := hdl.addNodesToDomainInCloud(
			cluster.BkCloudId, proxyList, cluster.Domain, cluster.BkBizId); err != nil {
			logResetStep(6, "failed to add proxies to cluster domain, domain: %s, errmsg: %s",
				cluster.Domain, err.Error())
			return err
		}
		logResetStep(6, "successfully added proxies to cluster domain, domain: %s", cluster.Domain)
	} else {
		logResetStep(6, "skip add proxies to cluster domain, domain: %s, cluster_type: %s, "+
			"reason: no proxy layer", cluster.Domain, cluster.ClusterType)
	}

	if len(cluster.Clb) > 0 {
		if err := hdl.resetAllClbBindings(cluster.Clb); err != nil {
			logResetStep(7, "failed to reset clb binding, domain: %s, errmsg: %s",
				cluster.Domain, err.Error())
			return err
		}
		logResetStep(7, "successfully reset clb binding, domain: %s", cluster.Domain)
	}

	return nil
}

// ResetRedisClusters resets the configured redis clusters.
// An empty clusterType resets every redis cluster in the config file, otherwise only
// the clusters of that exact type are reset.
func (hdl *RedisClusterHandler) ResetRedisClusters(clusterType haprobe.DbmMetadataClusterType) error {
	if config.ClusterConfig == nil {
		return gerrors.Newf(gerrors.Failure, "config is not loaded")
	}

	if hdl.dbmClient == nil {
		return gerrors.Newf(gerrors.Failure, "dbm client is nil")
	}

	clusterKind := resetClusterKindRedis
	if clusterType != "" {
		clusterKind = clusterType.String()
	}

	targets := config.ClusterConfig.RedisClustersOfType(clusterType)
	if len(targets) == 0 {
		logResetf("no %s clusters to reset", clusterKind)
		return nil
	}

	failCount := 0
	logResetClustersStart(clusterKind, len(targets))
	for _, cluster := range targets {
		if err := hdl.resetSingleRedisCluster(cluster); err != nil {
			failCount++
			logResetf("failed to reset cluster, domain: %s, errmsg: %s", cluster.Domain, err.Error())
			continue
		}
		logResetf("successfully reset cluster, domain: %s", cluster.Domain)
	}
	logResetClustersDone(clusterKind, len(targets), failCount, len(targets)-failCount)

	return nil
}

// redisSessionTarget is one Redis-protocol endpoint to query with CLIENT LIST.
type redisSessionTarget struct {
	host     string
	port     int
	password string
}

func (hdl *RedisClusterHandler) redisShowReady() error {
	if config.ClusterConfig == nil {
		return gerrors.New(gerrors.Failure, "config is not loaded")
	}
	if hdl.dbmClient == nil {
		return gerrors.New(gerrors.Failure, "dbm client is nil")
	}
	return nil
}

func (hdl *RedisClusterHandler) redisShowTargets() ([]*config.RedisCluster, error) {
	if err := hdl.redisShowReady(); err != nil {
		return nil, err
	}
	return config.ClusterConfig.RedisClustersOfType(hdl.clusterType), nil
}

func uniqueHosts(addrs []config.InstanceAddress) []string {
	seen := make(map[string]struct{}, len(addrs))
	hosts := make([]string, 0, len(addrs))
	for _, addr := range addrs {
		if addr.Host == "" {
			continue
		}
		if _, ok := seen[addr.Host]; ok {
			continue
		}
		seen[addr.Host] = struct{}{}
		hosts = append(hosts, addr.Host)
	}
	return hosts
}

// redisConfiguredStorageNodes returns every storage node listed in cluster shards.
func redisConfiguredStorageNodes(cluster *config.RedisCluster) []config.InstanceAddress {
	if cluster == nil {
		return nil
	}

	seen := make(map[string]struct{})
	nodes := make([]config.InstanceAddress, 0)
	add := func(node config.InstanceAddress) {
		if node.Host == "" || node.Port <= 0 {
			return
		}
		key := redisAddr(node.Host, node.Port)
		if _, ok := seen[key]; ok {
			return
		}
		seen[key] = struct{}{}
		nodes = append(nodes, node)
	}

	for _, shard := range cluster.Shards {
		add(shard.Master)
		for _, slave := range shard.Slave {
			add(slave)
		}
	}
	return nodes
}

func redisShowMetadataHosts(cluster *config.RedisCluster) []string {
	addrs := append(getProxyList(cluster), redisConfiguredStorageNodes(cluster)...)
	return uniqueHosts(addrs)
}

func getProxyList(cluster *config.RedisCluster) []config.InstanceAddress {
	proxyList := make([]config.InstanceAddress, 0, len(cluster.Proxy))
	for _, proxy := range cluster.Proxy {
		proxyList = append(proxyList, config.InstanceAddress{Host: proxy.Host, Port: proxy.Port})
	}
	return proxyList
}

func domainInstanceListOf(domain string, instList []dbm.InstanceInfoInDomain) DomainInstanceList {
	instanceList := make([]string, 0, len(instList))
	for _, inst := range instList {
		instanceList = append(instanceList, fmt.Sprintf("%s:%d", inst.Ip, inst.Port))
	}
	return DomainInstanceList{Domain: domain, InstanceList: instanceList}
}

func (hdl *RedisClusterHandler) proxyPassword(cluster *config.RedisCluster) (string, error) {
	machineType, ok := config.RedisProxyMachineType(cluster.ClusterType)
	if !ok {
		return "", gerrors.Newf(gerrors.Failure,
			"cluster type has no proxy password, cluster: %s, cluster_type: %s",
			cluster.Domain, cluster.ClusterType)
	}
	if cluster.ClusterId <= 0 {
		return "", gerrors.Newf(gerrors.Failure,
			"clusterId is required to query the proxy password of cluster %s", cluster.Domain)
	}

	passwd, err := hdl.dbmClient.QueryRedisPassword(cluster.BkCloudId, cluster.ClusterId, machineType)
	if err != nil {
		return "", gerrors.Newf(gerrors.Failure,
			"failed to get proxy password of cluster %s (clusterId=%d), errmsg: %s",
			cluster.Domain, cluster.ClusterId, err.Error())
	}
	return passwd, nil
}

// redisSessionTargets lists Redis-protocol endpoints: every configured storage node,
// plus every proxy data port. Admin ports are intentionally excluded.
func redisSessionTargets(cluster *config.RedisCluster, storagePass, proxyPass string) []redisSessionTarget {
	targets := make([]redisSessionTarget, 0)

	for _, node := range redisConfiguredStorageNodes(cluster) {
		targets = append(targets, redisSessionTarget{
			host:     node.Host,
			port:     node.Port,
			password: storagePass,
		})
	}

	if !config.HasRedisProxy(cluster.ClusterType) {
		return targets
	}

	for _, proxy := range cluster.Proxy {
		if proxy.Host == "" || proxy.Port <= 0 {
			continue
		}
		targets = append(targets, redisSessionTarget{
			host:     proxy.Host,
			port:     proxy.Port,
			password: proxyPass,
		})
	}
	return targets
}

func parseClientListFields(line string) map[string]string {
	fields := make(map[string]string)
	for _, part := range strings.Fields(line) {
		kv := strings.SplitN(part, "=", 2)
		if len(kv) != 2 {
			continue
		}
		fields[kv[0]] = kv[1]
	}
	return fields
}

func stringPtrValue(value string) *string {
	return &value
}

func clientListFirstField(fields map[string]string, keys ...string) string {
	for _, key := range keys {
		if value, ok := fields[key]; ok {
			return value
		}
	}
	return ""
}

func clientListInt64Field(fields map[string]string, keys ...string) int64 {
	raw := clientListFirstField(fields, keys...)
	if raw == "" {
		return 0
	}
	value, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return 0
	}
	return value
}

// parseClientList turns CLIENT LIST output into processlist-shaped rows.
// Redis, Tendisplus and Predixy use different key sets; missing fields stay at zero values.
func parseClientList(output string) []ProcesslistEntry {
	entries := make([]ProcesslistEntry, 0)
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		fields := parseClientListFields(line)
		entries = append(entries, ProcesslistEntry{
			ID:      clientListInt64Field(fields, "id"),
			User:    clientListFirstField(fields, "user"),
			Host:    clientListFirstField(fields, "addr"),
			DB:      stringPtrValue(clientListFirstField(fields, "db")),
			Command: clientListFirstField(fields, "cmd", "command"),
			Time:    clientListInt64Field(fields, "idle", "age"),
			State:   stringPtrValue(clientListFirstField(fields, "flags", "state")),
			Info:    stringPtrValue(clientListFirstField(fields, "name", "argv")),
		})
	}
	return entries
}

// normalizeClientListReply converts CLIENT LIST responses to newline-separated text.
// Standard Redis returns one bulk string; Predixy may return an array of bulk strings.
func normalizeClientListReply(raw interface{}) (string, error) {
	switch value := raw.(type) {
	case string:
		return value, nil
	case []byte:
		return string(value), nil
	case []interface{}:
		lines := make([]string, 0, len(value))
		for _, item := range value {
			line, err := clientListLineFromReplyItem(item)
			if err != nil {
				return "", err
			}
			if line == "" {
				continue
			}
			lines = append(lines, line)
		}
		return strings.Join(lines, "\n"), nil
	default:
		return "", gerrors.Newf(gerrors.Failure, "unexpected CLIENT LIST response type %T", raw)
	}
}

func clientListLineFromReplyItem(item interface{}) (string, error) {
	switch line := item.(type) {
	case string:
		return line, nil
	case []byte:
		return string(line), nil
	case []interface{}:
		parts := make([]string, 0, len(line))
		for _, part := range line {
			text, err := clientListLineFromReplyItem(part)
			if err != nil {
				return "", err
			}
			if text != "" {
				parts = append(parts, text)
			}
		}
		return strings.Join(parts, " "), nil
	default:
		return "", gerrors.Newf(gerrors.Failure, "unexpected CLIENT LIST item type %T", item)
	}
}

func buildClientListArgs(where string) []interface{} {
	args := []interface{}{"CLIENT", "LIST"}
	for _, field := range strings.Fields(where) {
		args = append(args, field)
	}
	return args
}

func queryRedisClientList(target redisSessionTarget, where string) ([]ProcesslistEntry, error) {
	cli, err := connectRedis(target.host, target.port, target.password)
	if err != nil {
		return nil, err
	}
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), redisCommandTimeout)
	defer cancel()

	args := buildClientListArgs(where)
	raw, err := cli.DB().Do(ctx, args...).Result()
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to run CLIENT LIST on node(%s:%d), errmsg: %s",
			target.host, target.port, err.Error())
	}

	output, err := normalizeClientListReply(raw)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to parse CLIENT LIST on node(%s:%d), errmsg: %s",
			target.host, target.port, err.Error())
	}

	return parseClientList(output), nil
}

func queryRedisNodesClientList(targets []redisSessionTarget, where string) []InstanceSessionInfo {
	if len(targets) == 0 {
		return []InstanceSessionInfo{}
	}

	type sessionResult struct {
		index int
		info  InstanceSessionInfo
	}
	resultCh := make(chan sessionResult, len(targets))
	sem := make(chan struct{}, getClusterMaxConcurrency())

	for i, target := range targets {
		sem <- struct{}{}

		info := InstanceSessionInfo{
			IP:       target.host,
			Port:     target.port,
			Sessions: make([]ProcesslistEntry, 0),
		}
		send := func() { resultCh <- sessionResult{index: i, info: info} }

		safe.Go(func() {
			defer func() { <-sem }()

			entries, err := queryRedisClientList(target, where)
			if err != nil {
				info.Errmsg = err.Error()
			} else {
				info.Result = true
				info.Sessions = entries
				info.Total = len(entries)
			}
			send()
		},
			safe.WithLabel(fmt.Sprintf("query-client-list(%s:%d)", target.host, target.port)),
			safe.WithOnPanic(func(pi safe.PanicInfo) {
				info.Errmsg = fmt.Sprintf("panic while querying node(%s:%d): %v",
					target.host, target.port, pi.Reason)
				send()
			}),
		)
	}

	infos := make([]InstanceSessionInfo, len(targets))
	for range targets {
		result := <-resultCh
		infos[result.index] = result.info
	}
	return infos
}

func redisNodeReplication(host string, port int, passwd string) (*RedisReplicationInfo, error) {
	cli, err := connectRedis(host, port, passwd)
	if err != nil {
		return nil, err
	}
	defer cli.Close()

	infoMap, err := redisReplicationInfo(cli)
	if err != nil {
		return nil, err
	}

	masterPort, _ := strconv.Atoi(infoMap["master_port"])
	return &RedisReplicationInfo{
		IP:               host,
		Port:             port,
		Role:             infoMap["role"],
		MasterIP:         infoMap["master_host"],
		MasterPort:       masterPort,
		MasterLinkStatus: infoMap["master_link_status"],
	}, nil
}

func (hdl *RedisClusterHandler) collectRedisClustersDomain() ([]ClusterDomainInfo, error) {
	targets, err := hdl.redisShowTargets()
	if err != nil {
		return nil, err
	}

	clusterDomainInfoList := make([]ClusterDomainInfo, 0, len(targets))
	for _, cluster := range targets {
		clusterDomainInfo := ClusterDomainInfo{
			Cluster: cluster.Domain,
			Domains: make([]DomainInstanceList, 0),
		}

		if cluster.Domain != "" {
			instList, err := hdl.dbmClient.GetAllInstancesOfDomainInCloud(cluster.BkCloudId, cluster.Domain)
			if err != nil {
				return nil, gerrors.Newf(gerrors.Failure, "failed to get instances of domain(%s), errmsg: %s",
					cluster.Domain, err.Error())
			}
			clusterDomainInfo.Domains = append(clusterDomainInfo.Domains,
				domainInstanceListOf(cluster.Domain, instList))
		}

		clusterDomainInfoList = append(clusterDomainInfoList, clusterDomainInfo)
	}

	return clusterDomainInfoList, nil
}

func (hdl *RedisClusterHandler) collectRedisClustersClb() ([]ClusterClbInfo, error) {
	targets, err := hdl.redisShowTargets()
	if err != nil {
		return nil, err
	}

	clusterClbInfoList := make([]ClusterClbInfo, 0)
	for _, cluster := range targets {
		if len(cluster.Clb) == 0 {
			continue
		}
		info, err := hdl.buildClusterClbInfo(cluster.Domain, cluster.Clb)
		if err != nil {
			return nil, err
		}
		clusterClbInfoList = append(clusterClbInfoList, info)
	}

	return clusterClbInfoList, nil
}

func (hdl *RedisClusterHandler) collectRedisClustersNodes() ([]ClusterNodeInfo, error) {
	targets, err := hdl.redisShowTargets()
	if err != nil {
		return nil, err
	}

	clusterNodeInfoList := make([]ClusterNodeInfo, 0, len(targets))
	for _, cluster := range targets {
		clusterNodeInfo := ClusterNodeInfo{
			Cluster: cluster.Domain,
			Nodes:   make([]NodeInfo, 0),
		}

		hosts := redisShowMetadataHosts(cluster)
		if len(hosts) == 0 {
			clusterNodeInfoList = append(clusterNodeInfoList, clusterNodeInfo)
			continue
		}

		metadataList, err := hdl.dbmClient.QueryMetadataFromDbm(cluster.BkCloudId, hosts)
		if err != nil {
			return nil, gerrors.Newf(gerrors.Failure, "failed to query metadata for cluster(%s), errmsg: %s",
				cluster.Domain, err.Error())
		}

		for _, meta := range metadataList {
			if meta.Cluster != cluster.Domain {
				continue
			}
			clusterNodeInfo.Nodes = append(clusterNodeInfo.Nodes, NodeInfo{
				IP:     meta.IP,
				Port:   meta.Port,
				Status: meta.Status,
				Role:   meta.GetRedisRole(),
			})
		}

		clusterNodeInfoList = append(clusterNodeInfoList, clusterNodeInfo)
	}

	return clusterNodeInfoList, nil
}

func (hdl *RedisClusterHandler) collectOneClusterMasterSlaveReplication(
	cluster *config.RedisCluster) (*ClusterRedisReplicationInfo, error) {
	clusterRepl := &ClusterRedisReplicationInfo{
		Cluster:      cluster.Domain,
		Replications: make([]RedisReplicationInfo, 0),
	}

	nodes := redisConfiguredStorageNodes(cluster)
	if len(nodes) == 0 {
		return clusterRepl, nil
	}

	passwd, err := hdl.storagePassword(cluster)
	if err != nil {
		return nil, err
	}

	type replResult struct {
		index    int
		replInfo *RedisReplicationInfo
		err      error
	}
	resultCh := make(chan replResult, len(nodes))
	sem := make(chan struct{}, getClusterMaxConcurrency())

	for i, node := range nodes {
		sem <- struct{}{}
		go func(idx int, host string, port int) {
			defer func() { <-sem }()
			replInfo, queryErr := redisNodeReplication(host, port, passwd)
			resultCh <- replResult{index: idx, replInfo: replInfo, err: queryErr}
		}(i, node.Host, node.Port)
	}

	results := make([]*RedisReplicationInfo, len(nodes))
	for range nodes {
		result := <-resultCh
		if result.err != nil {
			return nil, result.err
		}
		results[result.index] = result.replInfo
	}

	for _, replInfo := range results {
		clusterRepl.Replications = append(clusterRepl.Replications, *replInfo)
	}
	return clusterRepl, nil
}

func (hdl *RedisClusterHandler) collectOneClusterClusterNodesReplication(
	cluster *config.RedisCluster) (*ClusterRedisClusterNodesInfo, error) {
	clusterNodes := &ClusterRedisClusterNodesInfo{
		Cluster: cluster.Domain,
		Nodes:   make([]haredis.ClusterNode, 0),
	}

	nodes := redisConfiguredStorageNodes(cluster)
	if len(nodes) == 0 {
		return clusterNodes, nil
	}

	passwd, err := hdl.storagePassword(cluster)
	if err != nil {
		return nil, err
	}

	type nodesResult struct {
		source string
		nodes  []haredis.ClusterNode
		err    error
	}
	resultCh := make(chan nodesResult, len(nodes))
	sem := make(chan struct{}, getClusterMaxConcurrency())

	for _, node := range nodes {
		sem <- struct{}{}
		go func(host string, port int) {
			defer func() { <-sem }()
			source := redisAddr(host, port)
			cli, connErr := connectRedis(host, port, passwd)
			if connErr != nil {
				resultCh <- nodesResult{source: source, err: connErr}
				return
			}
			defer cli.Close()

			parsed, queryErr := haredis.GetClusterNodes(cli)
			resultCh <- nodesResult{source: source, nodes: parsed, err: queryErr}
		}(node.Host, node.Port)
	}

	var lastErr error
	best := nodesResult{}
	for range nodes {
		result := <-resultCh
		if result.err != nil {
			lastErr = result.err
			continue
		}
		if len(result.nodes) > len(best.nodes) {
			best = result
		}
	}
	if len(best.nodes) == 0 {
		if lastErr != nil {
			return nil, lastErr
		}
		return clusterNodes, nil
	}

	clusterNodes.QueriedFrom = best.source
	clusterNodes.Nodes = best.nodes
	return clusterNodes, nil
}

func (hdl *RedisClusterHandler) collectOneClusterReplication(cluster *config.RedisCluster) (any, error) {
	if config.IsClusterProtocolRedisClusterType(cluster.ClusterType) {
		return hdl.collectOneClusterClusterNodesReplication(cluster)
	}
	return hdl.collectOneClusterMasterSlaveReplication(cluster)
}

func (hdl *RedisClusterHandler) collectRedisClustersReplication() ([]any, error) {
	targets, err := hdl.redisShowTargets()
	if err != nil {
		return nil, err
	}

	clusterReplList := make([]any, 0, len(targets))
	for _, cluster := range targets {
		clusterRepl, collectErr := hdl.collectOneClusterReplication(cluster)
		if collectErr != nil {
			return nil, collectErr
		}
		clusterReplList = append(clusterReplList, clusterRepl)
	}
	return clusterReplList, nil
}

func twemproxyRoutingEntry(proxy config.ProxyAddress) (*TwemproxyProxyRouting, error) {
	cli, err := haredis.NewTwemproxyAdminClient(
		haredis.OptionIP(proxy.Host),
		haredis.OptionPort(proxy.AdminPort),
	)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to create twemproxy admin client for %s:%d, errmsg: %s",
			proxy.Host, proxy.AdminPort, err.Error())
	}

	serverMap, err := cli.GetServerMap()
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get backends of twemproxy(%s:%d), errmsg: %s",
			proxy.Host, proxy.AdminPort, err.Error())
	}

	segments := make([]string, 0, len(serverMap))
	for seg := range serverMap {
		segments = append(segments, seg)
	}
	sort.Strings(segments)

	entry := &TwemproxyProxyRouting{
		ProxyIP:        proxy.Host,
		ProxyAdminPort: proxy.AdminPort,
		MD5:            serverMap.MD5String(),
		Backends:       make([]TwemproxyBackend, 0, len(segments)),
	}
	for _, seg := range segments {
		entry.Backends = append(entry.Backends, TwemproxyBackend{
			Segment: seg,
			Address: serverMap[seg],
		})
	}
	return entry, nil
}

func predixyRoutingServersForShow(servers haredis.PredixyServerList) []PredixyRoutingServer {
	out := make([]PredixyRoutingServer, 0, len(servers))
	for _, server := range servers {
		if server == nil {
			continue
		}
		out = append(out, PredixyRoutingServer{
			Server:        server.Server,
			Role:          server.Role,
			CurrentIsFail: server.CurrentIsFail,
		})
	}
	return out
}

func predixyRoutingEntry(host string, port int, passwd string) (*PredixyProxyRouting, error) {
	cli, err := connectRedis(host, port, passwd)
	if err != nil {
		return nil, err
	}
	defer cli.Close()

	servers, err := haredis.GetPredixyInfoServers(cli)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to get INFO Servers of predixy(%s:%d), errmsg: %s",
			host, port, err.Error())
	}

	return &PredixyProxyRouting{
		ProxyIP:   host,
		ProxyPort: port,
		MD5:       servers.MD5String(),
		Servers:   predixyRoutingServersForShow(servers),
	}, nil
}

func routingCheckResult(md5s map[string]struct{}) string {
	if len(md5s) > 1 {
		return "failed"
	}
	return "ok"
}

func unavailableProxyAddrs(
	hdl *RedisClusterHandler, cluster *config.RedisCluster,
) (map[string]struct{}, error) {
	proxyIPs := uniqueHosts(hdl.getProxyList(cluster))
	if len(proxyIPs) == 0 {
		return map[string]struct{}{}, nil
	}

	metadataList, err := hdl.dbmClient.QueryMetadataFromDbm(cluster.BkCloudId, proxyIPs)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to query metadata for cluster(%s), errmsg: %s",
			cluster.Domain, err.Error())
	}

	unavailable := make(map[string]struct{}, len(metadataList))
	for _, meta := range metadataList {
		if meta.Cluster != cluster.Domain || meta.Status != string(dbm.StatusUnavailable) {
			continue
		}
		unavailable[redisAddr(meta.IP, meta.Port)] = struct{}{}
	}
	return unavailable, nil
}

func (hdl *RedisClusterHandler) collectOneClusterTwemproxyRouting(
	cluster *config.RedisCluster) (*TwemproxyRoutingInfo, error) {
	clusterRouting := &TwemproxyRoutingInfo{
		Cluster:     cluster.Domain,
		Routing:     make([]TwemproxyProxyRouting, 0),
		CheckResult: "ok",
	}
	if len(cluster.Proxy) == 0 {
		return clusterRouting, nil
	}

	unavailable, err := unavailableProxyAddrs(hdl, cluster)
	if err != nil {
		return nil, err
	}

	entries := make([]TwemproxyProxyRouting, 0)
	md5s := make(map[string]struct{})
	queryErrs := make([]string, 0)
	for _, proxy := range cluster.Proxy {
		if _, skip := unavailable[redisAddr(proxy.Host, proxy.Port)]; skip {
			continue
		}
		entry, queryErr := twemproxyRoutingEntry(proxy)
		if queryErr != nil {
			queryErrs = append(queryErrs, queryErr.Error())
			continue
		}
		entries = append(entries, *entry)
		if entry.MD5 != "" {
			md5s[entry.MD5] = struct{}{}
		}
	}
	if len(queryErrs) > 0 {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to query routing of cluster(%s), errmsg: %s",
			cluster.Domain, strings.Join(queryErrs, "; "))
	}

	clusterRouting.Routing = entries
	clusterRouting.CheckResult = routingCheckResult(md5s)
	return clusterRouting, nil
}

func (hdl *RedisClusterHandler) collectOneClusterPredixyRouting(
	cluster *config.RedisCluster) (*PredixyRoutingInfo, error) {
	clusterRouting := &PredixyRoutingInfo{
		Cluster:     cluster.Domain,
		Routing:     make([]PredixyProxyRouting, 0),
		CheckResult: "ok",
	}
	if len(cluster.Proxy) == 0 {
		return clusterRouting, nil
	}

	passwd, err := hdl.proxyPassword(cluster)
	if err != nil {
		return nil, err
	}

	unavailable, err := unavailableProxyAddrs(hdl, cluster)
	if err != nil {
		return nil, err
	}

	entries := make([]PredixyProxyRouting, 0)
	md5s := make(map[string]struct{})
	queryErrs := make([]string, 0)
	for _, proxy := range cluster.Proxy {
		if _, skip := unavailable[redisAddr(proxy.Host, proxy.Port)]; skip {
			continue
		}
		entry, queryErr := predixyRoutingEntry(proxy.Host, proxy.Port, passwd)
		if queryErr != nil {
			queryErrs = append(queryErrs, queryErr.Error())
			continue
		}
		entries = append(entries, *entry)
		if entry.MD5 != "" {
			md5s[entry.MD5] = struct{}{}
		}
	}
	if len(queryErrs) > 0 {
		return nil, gerrors.Newf(gerrors.Failure,
			"failed to query routing of cluster(%s), errmsg: %s",
			cluster.Domain, strings.Join(queryErrs, "; "))
	}

	clusterRouting.Routing = entries
	clusterRouting.CheckResult = routingCheckResult(md5s)
	return clusterRouting, nil
}

func (hdl *RedisClusterHandler) collectOneClusterRouting(cluster *config.RedisCluster) (any, error) {
	switch {
	case config.IsTwemproxyRedisClusterType(cluster.ClusterType):
		return hdl.collectOneClusterTwemproxyRouting(cluster)
	case config.IsPredixyRedisClusterType(cluster.ClusterType):
		return hdl.collectOneClusterPredixyRouting(cluster)
	default:
		return nil, nil
	}
}

func (hdl *RedisClusterHandler) collectRedisClustersRouting() ([]any, error) {
	targets, err := hdl.redisShowTargets()
	if err != nil {
		return nil, err
	}

	clusterRoutingList := make([]any, 0, len(targets))
	for _, cluster := range targets {
		routing, collectErr := hdl.collectOneClusterRouting(cluster)
		if collectErr != nil {
			return nil, collectErr
		}
		if routing != nil {
			clusterRoutingList = append(clusterRoutingList, routing)
		}
	}
	return clusterRoutingList, nil
}

func (hdl *RedisClusterHandler) collectRedisClustersSession(where string) ([]ClusterSessionInfo, error) {
	targets, err := hdl.redisShowTargets()
	if err != nil {
		return nil, err
	}

	clusterSessionList := make([]ClusterSessionInfo, 0, len(targets))
	for _, cluster := range targets {
		needStorage := len(redisConfiguredStorageNodes(cluster)) > 0
		needProxy := config.HasRedisProxy(cluster.ClusterType) && len(cluster.Proxy) > 0

		var storagePass, proxyPass string
		if needStorage {
			storagePass, err = hdl.storagePassword(cluster)
			if err != nil {
				return nil, err
			}
		}
		if needProxy {
			proxyPass, err = hdl.proxyPassword(cluster)
			if err != nil {
				return nil, err
			}
		}

		clusterSessionList = append(clusterSessionList, ClusterSessionInfo{
			Cluster: cluster.Domain,
			Instances: queryRedisNodesClientList(
				redisSessionTargets(cluster, storagePass, proxyPass), where),
		})
	}

	return clusterSessionList, nil
}

// ShowDomain shows domain binding information for the selected Redis clusters.
func (hdl *RedisClusterHandler) ShowDomain() ([]ClusterDomainInfo, error) {
	return hdl.collectRedisClustersDomain()
}

// ShowClb shows CLB binding information for the selected Redis clusters.
func (hdl *RedisClusterHandler) ShowClb() ([]ClusterClbInfo, error) {
	return hdl.collectRedisClustersClb()
}

// ShowNodes shows node status and role for the selected Redis clusters.
func (hdl *RedisClusterHandler) ShowNodes() ([]ClusterNodeInfo, error) {
	return hdl.collectRedisClustersNodes()
}

// ShowReplication shows replication or CLUSTER NODES status for the selected Redis clusters.
func (hdl *RedisClusterHandler) ShowReplication() (any, error) {
	return hdl.collectRedisClustersReplication()
}

// ShowRouting shows proxy routing information for the selected Redis clusters.
func (hdl *RedisClusterHandler) ShowRouting() (any, error) {
	return hdl.collectRedisClustersRouting()
}

// ShowSession shows CLIENT LIST sessions for the selected Redis clusters.
func (hdl *RedisClusterHandler) ShowSession(where string) ([]ClusterSessionInfo, error) {
	return hdl.collectRedisClustersSession(where)
}
