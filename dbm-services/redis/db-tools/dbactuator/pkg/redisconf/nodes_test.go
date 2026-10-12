package redisconf

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

const (
	testNodeID   = "e7d1eecce10fd6bb5eb35b9f99a514335d9ba9ca"
	orphanNodeID = "07c37dfeb235213a872192d90877d0cd55635b91"
)

// nodesFileContent 一份 redis 4.0 写出的节点文件, myself 是 nodeID
func nodesFileContent(nodeID string) string {
	return strings.Join([]string{
		nodeID + " 1.1.1.1:30000@40000 myself,slave 292f8b365bb7edb5e285caf0b7e6ddc7265d2f4f 0 0 3 connected",
		"292f8b365bb7edb5e285caf0b7e6ddc7265d2f4f 2.2.2.2:30000@40000 master - 0 1700000000000 3 connected 0-16383",
		"vars currentEpoch 3 lastVoteEpoch 0",
	}, "\n") + "\n"
}

func testLogger() *logger.Logger {
	return logger.New(io.Discard, false, logger.InfoLevel)
}

func clusterReq() Request {
	return Request{Port: 30000, ClusterType: consts.TendisTypePredixyRedisCluster, Logger: testLogger()}
}

func TestReadNodesFileMyself(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "nodes.conf")
	writeTestFile(t, path, nodesFileContent(testNodeID))
	if got, err := readNodesFileMyself(path); err != nil || got != testNodeID {
		t.Errorf("readNodesFileMyself = (%q,%v), want %q", got, err, testNodeID)
	}

	// redis 3.x 的地址不带 @cport, 也要读得出来
	legacy := filepath.Join(dir, "legacy.conf")
	writeTestFile(t, legacy, testNodeID+" 1.1.1.1:30000 myself,master - 0 0 1 connected 0-16383\n")
	if got, err := readNodesFileMyself(legacy); err != nil || got != testNodeID {
		t.Errorf("legacy nodes file = (%q,%v), want %q", got, err, testNodeID)
	}

	noMyself := filepath.Join(dir, "empty.conf")
	writeTestFile(t, noMyself, "vars currentEpoch 0 lastVoteEpoch 0\n")
	if _, err := readNodesFileMyself(noMyself); err == nil {
		t.Error("nodes file without myself line should fail")
	}
}

func TestCanonicalNodesFile(t *testing.T) {
	const rendered = "port 30000\ncluster-enabled yes\ncluster-config-file nodes-30000.conf\n"

	req := clusterReq()
	req.OldConfData = "dir /data/redis/30000/data\ncluster-config-file nodes-30000.conf\n"
	got := StepCanonicalNodesFile.Apply(req, rendered)
	if ParseDirectives(got).Has(clusterConfigFileDirective) {
		t.Errorf("cluster-config-file should be dropped for cache cluster:\n%s", got)
	}

	// dbconfig 里写着缺省值, 旧配置没声明: 同样去掉, 新配置只有一种写法
	req.OldConfData = "dir /data/redis/30000/data\n"
	if got = StepCanonicalNodesFile.Apply(req, "port 30000\ncluster-config-file nodes.conf\n"); strings.Contains(
		got, clusterConfigFileDirective) {
		t.Errorf("default cluster-config-file should be dropped:\n%s", got)
	}

	// 不是 cache cluster 的不碰: tendisplus 的身份在 rocksdb 里, 主从版没有节点文件
	for _, clusterType := range []string{consts.TendisTypePredixyTendisplusCluster, consts.TendisTypeTwemproxyRedisInstance} {
		req.ClusterType = clusterType
		if got = StepCanonicalNodesFile.Apply(req, rendered); got != rendered {
			t.Errorf("%s should be left untouched:\n%s", clusterType, got)
		}
	}
}

func TestNodesFilePath(t *testing.T) {
	cases := []struct {
		conf string
		want string
	}{
		{"dir /data/redis/30000/data\n", "/data/redis/30000/data/nodes.conf"},
		{"dir /data/redis/30000/data\ncluster-config-file nodes-30000.conf\n", "/data/redis/30000/data/nodes-30000.conf"},
		{"dir /data/redis/30000/data\ncluster-config-file \"/data/redis/30000/nodes.conf\"\n", "/data/redis/30000/nodes.conf"},
	}
	for _, tc := range cases {
		if got := nodesFilePath(ParseDirectives(tc.conf)); got != tc.want {
			t.Errorf("nodesFilePath(%q) = %q, want %q", tc.conf, got, tc.want)
		}
	}
}

func TestPlanNodesFileMove(t *testing.T) {
	dataDir := t.TempDir()
	legacy := filepath.Join(dataDir, "nodes-30000.conf")
	writeTestFile(t, legacy, nodesFileContent(testNodeID))
	oldDirs := ParseDirectives("dir " + dataDir + "\ncluster-config-file nodes-30000.conf\n")
	newDirs := ParseDirectives("dir " + dataDir + "\n")

	move, err := planNodesFileMove(clusterReq(), oldDirs, newDirs)
	if err != nil {
		t.Fatalf("planNodesFileMove err:%v", err)
	}
	if move == nil || move.From != legacy || move.To != filepath.Join(dataDir, "nodes.conf") || move.NodeID != testNodeID {
		t.Fatalf("move = %+v", move)
	}

	// 旧配置本来就落在缺省位置: 不需要迁
	if move, err = planNodesFileMove(clusterReq(),
		ParseDirectives("dir "+dataDir+"\ncluster-config-file nodes.conf\n"), newDirs); err != nil || move != nil {
		t.Errorf("same nodes file should need no move, got (%+v,%v)", move, err)
	}

	// 主从版不管节点文件, 即使旧配置里写了也不读
	req := clusterReq()
	req.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	if move, err = planNodesFileMove(req,
		ParseDirectives("dir "+dataDir+"\ncluster-config-file missing.conf\n"), newDirs); err != nil || move != nil {
		t.Errorf("non cluster should need no move, got (%+v,%v)", move, err)
	}
}

func TestPlanNodesFileMoveRefusesUnreadableLegacyFile(t *testing.T) {
	dataDir := t.TempDir()
	oldDirs := ParseDirectives("dir " + dataDir + "\ncluster-config-file nodes-30000.conf\n")
	newDirs := ParseDirectives("dir " + dataDir + "\n")
	_, err := planNodesFileMove(clusterReq(), oldDirs, newDirs)
	if err == nil || !strings.Contains(err.Error(), "new cluster node") {
		t.Errorf("err = %v, want refusal when legacy nodes file is missing", err)
	}
}

func TestNodesFileMoveApplyUndo(t *testing.T) {
	dataDir := t.TempDir()
	from := filepath.Join(dataDir, "nodes-30000.conf")
	to := filepath.Join(dataDir, "nodes.conf")
	writeTestFile(t, from, nodesFileContent(testNodeID))
	move := &NodesFileMove{From: from, To: to, NodeID: testNodeID}

	if err := move.Apply(testLogger()); err != nil {
		t.Fatalf("Apply err:%v", err)
	}
	if got := readTestFile(t, to); got != nodesFileContent(testNodeID) {
		t.Errorf("copied nodes file differs:\n%s", got)
	}
	if got := readTestFile(t, from); got != nodesFileContent(testNodeID) {
		t.Error("source nodes file must stay in place")
	}
	if err := move.Undo(testLogger()); err != nil {
		t.Fatalf("Undo err:%v", err)
	}
	if _, err := os.Stat(to); !os.IsNotExist(err) {
		t.Errorf("copied nodes file should be removed by Undo,stat err:%v", err)
	}
}

func TestNodesFileMoveKeepsIdenticalCopy(t *testing.T) {
	// 重试场景: 上一次已经复制过, 目标位置与源文件一模一样
	dataDir := t.TempDir()
	from := filepath.Join(dataDir, "nodes-30000.conf")
	to := filepath.Join(dataDir, "nodes.conf")
	writeTestFile(t, from, nodesFileContent(testNodeID))
	writeTestFile(t, to, nodesFileContent(testNodeID))
	move := &NodesFileMove{From: from, To: to, NodeID: testNodeID}

	if err := move.Apply(testLogger()); err != nil {
		t.Fatalf("Apply err:%v", err)
	}
	if orphans, _ := filepath.Glob(to + ".orphan.*.bak"); len(orphans) != 0 {
		t.Errorf("identical copy should not be moved aside, got %v", orphans)
	}
	if err := move.Undo(testLogger()); err != nil {
		t.Fatalf("Undo err:%v", err)
	}
	if got := readTestFile(t, to); got != nodesFileContent(testNodeID) {
		t.Error("Undo must not remove a nodes file it did not write")
	}
}

func TestNodesFileMoveReplacesStaleSnapshotOfSameIdentity(t *testing.T) {
	// 很早以前用过缺省 nodes.conf, 后来改成 nodes-30000.conf 但旧文件没清: 同一 node id, 内容过期
	dataDir := t.TempDir()
	from := filepath.Join(dataDir, "nodes-30000.conf")
	to := filepath.Join(dataDir, "nodes.conf")
	writeTestFile(t, from, nodesFileContent(testNodeID))
	stale := testNodeID + " 1.1.1.1:30000@40000 myself,master - 0 0 1 connected 0-16383\n" +
		"vars currentEpoch 1 lastVoteEpoch 0\n"
	writeTestFile(t, to, stale)
	move := &NodesFileMove{From: from, To: to, NodeID: testNodeID}

	if err := move.Apply(testLogger()); err != nil {
		t.Fatalf("Apply err:%v", err)
	}
	if got := readTestFile(t, to); got != nodesFileContent(testNodeID) {
		t.Errorf("stale snapshot should be replaced by the source:\n%s", got)
	}
	orphans, _ := filepath.Glob(to + ".orphan.*.bak")
	if len(orphans) != 1 || readTestFile(t, orphans[0]) != stale {
		t.Fatalf("stale snapshot should be kept aside, got %v", orphans)
	}

	if err := move.Undo(testLogger()); err != nil {
		t.Fatalf("Undo err:%v", err)
	}
	if got := readTestFile(t, to); got != stale {
		t.Errorf("Undo should put the stale snapshot back:\n%s", got)
	}
}

func TestNodesFileMoveSetsOrphanAside(t *testing.T) {
	// 上一次没带身份起来, 生成了一个孤立节点的 nodes.conf
	dataDir := t.TempDir()
	from := filepath.Join(dataDir, "nodes-30000.conf")
	to := filepath.Join(dataDir, "nodes.conf")
	writeTestFile(t, from, nodesFileContent(testNodeID))
	writeTestFile(t, to, nodesFileContent(orphanNodeID))
	move := &NodesFileMove{From: from, To: to, NodeID: testNodeID}

	if err := move.Apply(testLogger()); err != nil {
		t.Fatalf("Apply err:%v", err)
	}
	if got, _ := readNodesFileMyself(to); got != testNodeID {
		t.Errorf("nodes.conf node id = %q, want %q", got, testNodeID)
	}
	orphans, _ := filepath.Glob(to + ".orphan.*.bak")
	if len(orphans) != 1 || readTestFile(t, orphans[0]) != nodesFileContent(orphanNodeID) {
		t.Fatalf("orphan nodes file should be kept aside, got %v", orphans)
	}

	if err := move.Undo(testLogger()); err != nil {
		t.Fatalf("Undo err:%v", err)
	}
	if got, _ := readNodesFileMyself(to); got != orphanNodeID {
		t.Errorf("Undo should put the orphan back, node id = %q", got)
	}
	if orphans, _ = filepath.Glob(to + ".orphan.*.bak"); len(orphans) != 0 {
		t.Errorf("no orphan copy should remain after Undo, got %v", orphans)
	}
}

func TestNodesFileMoveFinalizeRemovesSource(t *testing.T) {
	dataDir := t.TempDir()
	from := filepath.Join(dataDir, "nodes-30000.conf")
	to := filepath.Join(dataDir, "nodes.conf")
	writeTestFile(t, from, nodesFileContent(testNodeID))
	applied, err := ApplyChanges([]Change{&NodesFileMove{From: from, To: to, NodeID: testNodeID}}, testLogger())
	if err != nil {
		t.Fatalf("ApplyChanges err:%v", err)
	}

	applied.Finalize(testLogger())
	if _, err = os.Stat(from); !os.IsNotExist(err) {
		t.Errorf("legacy nodes file should be removed after Finalize,stat err:%v", err)
	}
	if got, _ := readNodesFileMyself(to); got != testNodeID {
		t.Errorf("nodes.conf node id = %q, want %q", got, testNodeID)
	}
	// 重复收尾不报错
	applied.Finalize(testLogger())
}

func TestNodesFileMoveFinalizeKeepsSourceOnIdentityMismatch(t *testing.T) {
	dataDir := t.TempDir()
	from := filepath.Join(dataDir, "nodes-30000.conf")
	to := filepath.Join(dataDir, "nodes.conf")
	writeTestFile(t, from, nodesFileContent(testNodeID))
	move := &NodesFileMove{From: from, To: to, NodeID: testNodeID}
	if err := move.Apply(testLogger()); err != nil {
		t.Fatalf("Apply err:%v", err)
	}
	// 起来的进程没认这份身份, 生成了新节点
	writeTestFile(t, to, nodesFileContent(orphanNodeID))

	move.Finalize(testLogger())
	if got := readTestFile(t, from); got != nodesFileContent(testNodeID) {
		t.Error("legacy nodes file must be kept when nodes.conf holds another identity")
	}
}
