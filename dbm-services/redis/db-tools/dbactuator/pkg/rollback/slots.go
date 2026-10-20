// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"context"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// Cluster protocol temp instances start with cluster-enabled but alone: each restores its data,
// then takes its planned slots, and they meet only in FormCluster once every port is done. Nothing
// runs cluster reset, which is what let v1 nodes be demoted to replicas.

const (
	clusterSlotCount = 16384
	// The default 15000 is raised: temp clusters have no replicas, and a node too busy to answer
	// pings, e.g. on a full disk, must not be marked failed.
	clusterNodeTimeoutMs = 60000
	addSlotsBatch        = 2000
	clusterCmdTimeout    = 30 * time.Second
	clusterStateOK       = "ok"
)

// ClusterNode is what slot assignment and formation need from one temp instance.
type ClusterNode interface {
	Info() (*myredis.CmdClusterInfo, error)
	Nodes() ([]*myredis.ClusterNodeData, error)
	AddSlots(slots []int) error
	DelSlots(slots []int) error
	SetConfigEpoch(epoch int) error
	Meet(ip string, port int) error
	Close()
}

type redisClusterNode struct {
	cli *myredis.RedisClient
}

// ClusterNodeConnector connects FormCluster to the temp instances with their shared password.
func ClusterNodeConnector(password string) func(FormNode) (ClusterNode, error) {
	return func(n FormNode) (ClusterNode, error) {
		return connectClusterNode(n.Addr(), password)
	}
}

// connectClusterNode connects one temp instance; dbType only picks a standalone client.
func connectClusterNode(addr, password string) (ClusterNode, error) {
	cli, err := myredis.NewRedisClientWithRetry(addr, password, 0, consts.TendisTypeRedisInstance, clusterCmdTimeout)
	if err != nil {
		return nil, err
	}
	return redisClusterNode{cli: cli}, nil
}

func (n redisClusterNode) Info() (*myredis.CmdClusterInfo, error) {
	return n.cli.ClusterInfo()
}

func (n redisClusterNode) Nodes() ([]*myredis.ClusterNodeData, error) {
	return n.cli.GetClusterNodes()
}

func (n redisClusterNode) AddSlots(slots []int) error {
	_, err := n.cli.ClusterAddSlots(slots)
	return err
}

func (n redisClusterNode) DelSlots(slots []int) error {
	if err := n.cli.InstanceClient.ClusterDelSlots(context.TODO(), slots...).Err(); err != nil {
		return fmt.Errorf("redis(%s) cluster delslots %s failed: %v", n.cli.Addr, myredis.ConvertSlotToStr(slots), err)
	}
	return nil
}

func (n redisClusterNode) SetConfigEpoch(epoch int) error {
	if err := n.cli.InstanceClient.Do(context.TODO(), "cluster", "set-config-epoch", epoch).Err(); err != nil {
		return fmt.Errorf("redis(%s) cluster set-config-epoch %d failed: %v", n.cli.Addr, epoch, err)
	}
	return nil
}

func (n redisClusterNode) Meet(ip string, port int) error {
	_, err := n.cli.ClusterMeet(ip, strconv.Itoa(port))
	return err
}

func (n redisClusterNode) Close() {
	n.cli.Close()
}

// SetClusterConf writes the cluster directives of a temp instance into redis.conf before it starts.
// Redis 5+ reads cluster-slave-no-failover as an alias, so whichever name the template uses is set.
func SetClusterConf(confFile string) error {
	raw, err := os.ReadFile(confFile)
	if err != nil {
		return err
	}
	content := renderDirective(string(raw), "cluster-enabled", "yes")
	content = renderDirective(content, "cluster-node-timeout", strconv.Itoa(clusterNodeTimeoutMs))
	noFailover := false
	for _, name := range []string{"cluster-replica-no-failover", "cluster-slave-no-failover"} {
		if hasDirective(content, name) {
			content = renderDirective(content, name, "yes")
			noFailover = true
		}
	}
	if !noFailover {
		content = renderDirective(content, "cluster-slave-no-failover", "yes")
	}
	if err = os.WriteFile(confFile, []byte(content), 0644); err != nil {
		return err
	}
	return util.LocalDirChownMysql(confFile)
}

func hasDirective(content, name string) bool {
	for _, line := range strings.Split(content, "\n") {
		if fields := strings.Fields(line); len(fields) > 0 && fields[0] == name {
			return true
		}
	}
	return false
}

// ParseSlots reads "0-100,200" into sorted, distinct slots.
func ParseSlots(s string) ([]int, error) {
	seen := map[int]bool{}
	for _, item := range strings.Split(s, ",") {
		item = strings.TrimSpace(item)
		if item == "" {
			continue
		}
		bounds := strings.SplitN(item, "-", 2)
		start, err := strconv.Atoi(bounds[0])
		end := start
		if err == nil && len(bounds) == 2 {
			end, err = strconv.Atoi(bounds[1])
		}
		if err != nil || start < 0 || end >= clusterSlotCount || start > end {
			return nil, fmt.Errorf("invalid slots %q in %q", item, s)
		}
		for slot := start; slot <= end; slot++ {
			seen[slot] = true
		}
	}
	slots := make([]int, 0, len(seen))
	for slot := range seen {
		slots = append(slots, slot)
	}
	sort.Ints(slots)
	return slots, nil
}

func myself(node ClusterNode) (*myredis.ClusterNodeData, error) {
	nodes, err := node.Nodes()
	if err != nil {
		return nil, err
	}
	for _, n := range nodes {
		if n.IsMyself {
			return n, nil
		}
	}
	return nil, fmt.Errorf("no myself line in cluster nodes")
}

func slotDiff(owned []int, planned []int) (missing, extra []int) {
	have := make(map[int]bool, len(owned))
	for _, s := range owned {
		have[s] = true
	}
	want := make(map[int]bool, len(planned))
	for _, s := range planned {
		want[s] = true
		if !have[s] {
			missing = append(missing, s)
		}
	}
	for _, s := range owned {
		if !want[s] {
			extra = append(extra, s)
		}
	}
	sort.Ints(extra)
	return missing, extra
}

// AssignSlots makes a still lonely node own exactly planned. A Redis node that loads an RDB claims
// every unassigned slot it holds keys for, so some are owned already; keys of a slot that was
// migrating at backup time may claim one outside the plan, which is released.
func AssignSlots(log portLog, node ClusterNode, planned []int) error {
	info, err := node.Info()
	if err != nil {
		return err
	}
	if info.ClusterKnownNodes > 1 {
		return fmt.Errorf("already knows %d cluster nodes, temp instances meet only when the cluster is formed",
			info.ClusterKnownNodes)
	}
	me, err := myself(node)
	if err != nil {
		return err
	}
	missing, extra := slotDiff(me.Slots, planned)
	if len(extra) > 0 {
		log.Warn("owns slots %s outside the plan, likely keys of a slot migrating at backup time; releasing them",
			myredis.ConvertSlotToStr(extra))
		if err = node.DelSlots(extra); err != nil {
			return err
		}
	}
	for start := 0; start < len(missing); start += addSlotsBatch {
		end := start + addSlotsBatch
		if end > len(missing) {
			end = len(missing)
		}
		if err = node.AddSlots(missing[start:end]); err != nil {
			return err
		}
	}
	if me, err = myself(node); err != nil {
		return err
	}
	if missing, extra = slotDiff(me.Slots, planned); len(missing) > 0 || len(extra) > 0 {
		return fmt.Errorf("owns slots %s after addslots, plan %s", myredis.ConvertSlotToStr(sortedCopy(me.Slots)),
			myredis.ConvertSlotToStr(planned))
	}
	log.Info("owns its planned slots %s", myredis.ConvertSlotToStr(planned))
	return nil
}

func sortedCopy(slots []int) []int {
	out := append([]int{}, slots...)
	sort.Ints(out)
	return out
}

// assignPortSlotsFn is replaced in tests, which have no instance to connect to.
var assignPortSlotsFn = assignPortSlots

// assignPortSlots gives the restored instance on inst's port the slots of its plan.
func assignPortSlots(log portLog, destIP string, inst InstanceRestore) error {
	planned, err := ParseSlots(inst.Slots)
	if err != nil {
		return err
	}
	if len(planned) == 0 {
		return fmt.Errorf("no slots planned for port %d", inst.DestPort)
	}
	password, err := myredis.GetRedisPasswdFromConfFile(inst.DestPort)
	if err != nil {
		return err
	}
	node, err := connectClusterNode(fmt.Sprintf("%s:%d", destIP, inst.DestPort), password)
	if err != nil {
		return err
	}
	defer node.Close()
	return AssignSlots(log, node, planned)
}

// FormNode is a temp instance and the slots the plan gives it.
type FormNode struct {
	IP    string `json:"ip" validate:"required"`
	Port  int    `json:"port" validate:"required"`
	Slots string `json:"slots"`
}

// Addr is ip:port.
func (n FormNode) Addr() string {
	return fmt.Sprintf("%s:%d", n.IP, n.Port)
}

type formingNode struct {
	FormNode
	conn    ClusterNode
	planned []int
}

// FormCluster joins the restored temp instances into one cluster. Each must still be alone and own
// exactly its planned slots; each gets a distinct config epoch, then all meet. The cluster must
// reach state ok with every node a master holding its planned slots, or the differences are
// returned. A retry skips what an earlier attempt did, and never touches data.
func FormCluster(nodes []FormNode, connect func(FormNode) (ClusterNode, error), timeout, poll time.Duration) error {
	if len(nodes) == 0 {
		return fmt.Errorf("no nodes to form a cluster")
	}
	sorted := append([]FormNode{}, nodes...)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i].Addr() < sorted[j].Addr() })

	forming := make([]formingNode, 0, len(sorted))
	defer func() {
		for _, n := range forming {
			n.conn.Close()
		}
	}()
	owner := make(map[int]string, clusterSlotCount)
	for _, n := range sorted {
		planned, err := ParseSlots(n.Slots)
		if err != nil {
			return err
		}
		for _, slot := range planned {
			if prev, ok := owner[slot]; ok {
				return fmt.Errorf("slot %d planned for both %s and %s", slot, prev, n.Addr())
			}
			owner[slot] = n.Addr()
		}
		conn, err := connect(n)
		if err != nil {
			return err
		}
		forming = append(forming, formingNode{FormNode: n, conn: conn, planned: planned})
	}
	if len(owner) != clusterSlotCount {
		return fmt.Errorf("plan covers %d of %d slots", len(owner), clusterSlotCount)
	}

	if err := setConfigEpochs(forming); err != nil {
		return err
	}
	if err := meetAll(forming); err != nil {
		return err
	}
	if err := waitClusterOK(forming, timeout, poll); err != nil {
		return err
	}
	return verifyCluster(forming)
}

// setConfigEpochs gives every lonely node epoch 1..N in address order. Epochs only matter if two
// masters ever claim one slot, which disjoint plans rule out, but distinct ones keep gossip from
// changing anything on its own.
func setConfigEpochs(nodes []formingNode) error {
	for i, n := range nodes {
		info, err := n.conn.Info()
		if err != nil {
			return err
		}
		if info.ClusterKnownNodes > 1 {
			continue
		}
		me, err := myself(n.conn)
		if err != nil {
			return err
		}
		if missing, extra := slotDiff(me.Slots, n.planned); len(missing) > 0 || len(extra) > 0 {
			return fmt.Errorf("%s owns slots %s, plan %s; the restore node assigns them", n.Addr(),
				myredis.ConvertSlotToStr(sortedCopy(me.Slots)), myredis.ConvertSlotToStr(n.planned))
		}
		if info.ClusterMyEpoch == 0 {
			if err = n.conn.SetConfigEpoch(i + 1); err != nil {
				return err
			}
		}
	}
	seen := map[int]string{}
	for _, n := range nodes {
		info, err := n.conn.Info()
		if err != nil {
			return err
		}
		if prev, ok := seen[info.ClusterMyEpoch]; ok {
			return fmt.Errorf("%s and %s share config epoch %d", prev, n.Addr(), info.ClusterMyEpoch)
		}
		seen[info.ClusterMyEpoch] = n.Addr()
	}
	return nil
}

// meetAll has the first node meet every node it does not know yet.
func meetAll(nodes []formingNode) error {
	known, err := nodes[0].conn.Nodes()
	if err != nil {
		return err
	}
	seen := map[string]bool{}
	for _, n := range known {
		seen[n.Addr] = true
	}
	for _, n := range nodes[1:] {
		if seen[n.Addr()] {
			continue
		}
		mylog.Logger.Info("RedisRollback form cluster: %s meet %s", nodes[0].Addr(), n.Addr())
		if err = nodes[0].conn.Meet(n.IP, n.Port); err != nil {
			return err
		}
	}
	return nil
}

func waitClusterOK(nodes []formingNode, timeout, poll time.Duration) error {
	deadline := time.Now().Add(timeout)
	for {
		var pending []string
		for _, n := range nodes {
			info, err := n.conn.Info()
			switch {
			case err != nil:
				pending = append(pending, fmt.Sprintf("%s: %v", n.Addr(), err))
			case info.ClusterState != clusterStateOK || info.ClusterKnownNodes != len(nodes):
				pending = append(pending, fmt.Sprintf("%s state=%s known_nodes=%d", n.Addr(), info.ClusterState,
					info.ClusterKnownNodes))
			}
		}
		if len(pending) == 0 {
			mylog.Logger.Info("RedisRollback form cluster: %d nodes, state ok", len(nodes))
			return nil
		}
		if !time.Now().Before(deadline) {
			return fmt.Errorf("temp cluster not ok after %v, want %d nodes: %s", timeout, len(nodes),
				strings.Join(pending, "; "))
		}
		time.Sleep(poll)
	}
}

// verifyCluster checks every node's view: all nodes known, each a master with no failure flag,
// holding exactly its planned slots.
func verifyCluster(nodes []formingNode) error {
	var diffs []string
	for _, viewer := range nodes {
		view, err := viewer.conn.Nodes()
		if err != nil {
			return err
		}
		byAddr := make(map[string]*myredis.ClusterNodeData, len(view))
		for _, n := range view {
			// A node lists itself as ":port" until a peer tells it its address.
			if n.IsMyself {
				byAddr[viewer.Addr()] = n
				continue
			}
			byAddr[n.Addr] = n
		}
		if len(view) != len(nodes) {
			diffs = append(diffs, fmt.Sprintf("%s sees %d nodes, want %d", viewer.Addr(), len(view), len(nodes)))
		}
		for _, want := range nodes {
			got, ok := byAddr[want.Addr()]
			switch {
			case !ok:
				diffs = append(diffs, fmt.Sprintf("%s does not see %s", viewer.Addr(), want.Addr()))
				continue
			case got.GetRole() != consts.RedisMasterRole || got.MasterID != "":
				diffs = append(diffs, fmt.Sprintf("%s sees %s as %s of %s", viewer.Addr(), want.Addr(), got.GetRole(),
					got.MasterID))
			case len(got.FailStatus) > 0:
				diffs = append(diffs, fmt.Sprintf("%s sees %s %v", viewer.Addr(), want.Addr(), got.FailStatus))
			}
			if missing, extra := slotDiff(got.Slots, want.planned); len(missing) > 0 || len(extra) > 0 {
				diffs = append(diffs, fmt.Sprintf("%s sees %s with slots %s, plan %s", viewer.Addr(), want.Addr(),
					myredis.ConvertSlotToStr(sortedCopy(got.Slots)), myredis.ConvertSlotToStr(want.planned)))
			}
		}
	}
	if len(diffs) > 0 {
		return fmt.Errorf("temp cluster differs from the plan: %s", strings.Join(diffs, "; "))
	}
	return nil
}
