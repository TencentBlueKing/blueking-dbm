package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// fakeCluster lets fake nodes meet: a meet merges what both sides know, as if gossip finished.
type fakeCluster struct {
	nodes map[string]*fakeNode
}

type fakeNode struct {
	cluster  *fakeCluster
	addr     string
	slots    map[int]bool
	epoch    int
	known    map[string]bool
	role     string
	masterID string
	state    string
	calls    []string
}

func newFakeCluster(plan map[string]string) *fakeCluster {
	c := &fakeCluster{nodes: map[string]*fakeNode{}}
	for addr, slots := range plan {
		n := &fakeNode{cluster: c, addr: addr, slots: map[int]bool{}, known: map[string]bool{addr: true},
			role: consts.RedisMasterRole}
		parsed, _ := ParseSlots(slots)
		for _, s := range parsed {
			n.slots[s] = true
		}
		c.nodes[addr] = n
	}
	return c
}

func (c *fakeCluster) connect(n FormNode) (ClusterNode, error) {
	node, ok := c.nodes[n.Addr()]
	if !ok {
		return nil, fmt.Errorf("no node %s", n.Addr())
	}
	return node, nil
}

func (n *fakeNode) Info() (*myredis.CmdClusterInfo, error) {
	state := n.state
	if state == "" {
		covered := map[int]bool{}
		for addr := range n.known {
			for s := range n.cluster.nodes[addr].slots {
				covered[s] = true
			}
		}
		state = "fail"
		if len(covered) == clusterSlotCount {
			state = clusterStateOK
		}
	}
	return &myredis.CmdClusterInfo{ClusterState: state, ClusterKnownNodes: len(n.known), ClusterMyEpoch: n.epoch}, nil
}

func (n *fakeNode) Nodes() ([]*myredis.ClusterNodeData, error) {
	var out []*myredis.ClusterNodeData
	for addr := range n.known {
		peer := n.cluster.nodes[addr]
		data := myredis.NewDefaultNode()
		data.Addr, data.NodeID, data.IsMyself = addr, "id-"+addr, addr == n.addr
		if data.IsMyself {
			// as tendisplus 2.8.2 shows: myself has no IP until a peer tells it
			data.Addr = addr[strings.Index(addr, ":"):]
		}
		data.Role, data.MasterID = peer.role, peer.masterID
		for s := range peer.slots {
			data.Slots = append(data.Slots, s)
			data.SlotsMap[s] = true
		}
		sort.Ints(data.Slots)
		out = append(out, data)
	}
	return out, nil
}

func (n *fakeNode) AddSlots(slots []int) error {
	n.calls = append(n.calls, "addslots "+myredis.ConvertSlotToStr(slots))
	for _, s := range slots {
		if n.slots[s] {
			return fmt.Errorf("ERR Slot %d is already busy", s)
		}
		n.slots[s] = true
	}
	return nil
}

func (n *fakeNode) DelSlots(slots []int) error {
	n.calls = append(n.calls, "delslots "+myredis.ConvertSlotToStr(slots))
	for _, s := range slots {
		delete(n.slots, s)
	}
	return nil
}

func (n *fakeNode) SetConfigEpoch(epoch int) error {
	n.calls = append(n.calls, fmt.Sprintf("set-config-epoch %d", epoch))
	if len(n.known) > 1 || n.epoch != 0 {
		return fmt.Errorf("ERR the user can assign a config epoch only when the node does not know any other node")
	}
	n.epoch = epoch
	return nil
}

func (n *fakeNode) Meet(ip string, port int) error {
	n.calls = append(n.calls, fmt.Sprintf("meet %s:%d", ip, port))
	peer := n.cluster.nodes[fmt.Sprintf("%s:%d", ip, port)]
	merged := map[string]bool{}
	for addr := range n.known {
		merged[addr] = true
	}
	for addr := range peer.known {
		merged[addr] = true
	}
	for addr := range merged {
		node := n.cluster.nodes[addr]
		for a := range merged {
			node.known[a] = true
		}
	}
	return nil
}

func (n *fakeNode) Close() {}

var threeNodes = []FormNode{
	{IP: "3.3.3.3", Port: 30000, Slots: "10923-16383"},
	{IP: "1.1.1.1", Port: 30000, Slots: "0-5460"},
	{IP: "2.2.2.2", Port: 30000, Slots: "5461-10922"},
}

func plannedCluster(nodes []FormNode) *fakeCluster {
	plan := map[string]string{}
	for _, n := range nodes {
		plan[n.Addr()] = n.Slots
	}
	return newFakeCluster(plan)
}

func TestParseSlots(t *testing.T) {
	got, err := ParseSlots("5,0-2, 2")
	if err != nil || !reflect.DeepEqual(got, []int{0, 1, 2, 5}) {
		t.Fatalf("got %v %v", got, err)
	}
	if got, err = ParseSlots(""); err != nil || len(got) != 0 {
		t.Fatalf("empty: %v %v", got, err)
	}
	for _, bad := range []string{"5-3", "16384", "a", "-1"} {
		if _, err = ParseSlots(bad); err == nil {
			t.Fatalf("%q: want error", bad)
		}
	}
}

func TestSetClusterConfRendersEveryDirective(t *testing.T) {
	conf := filepath.Join(t.TempDir(), "redis.conf")
	_ = os.WriteFile(conf, []byte("port 30000\ncluster-enabled no\ncluster-replica-no-failover no\n"), 0644)
	_ = SetClusterConf(conf)
	raw, _ := os.ReadFile(conf)
	got := string(raw)
	for _, want := range []string{"cluster-enabled yes", "cluster-replica-no-failover yes", "cluster-node-timeout 60000"} {
		if !strings.Contains(got, want) {
			t.Fatalf("missing %q in %s", want, got)
		}
	}
	if strings.Contains(got, "cluster-slave-no-failover") || strings.Contains(got, " no\n") {
		t.Fatalf("stale or duplicate directive in %s", got)
	}

	_ = os.WriteFile(conf, []byte("port 30000\n"), 0644)
	_ = SetClusterConf(conf)
	raw, _ = os.ReadFile(conf)
	if !strings.Contains(string(raw), "cluster-slave-no-failover yes") {
		t.Fatalf("tendisplus name not appended: %s", raw)
	}
}

func TestAssignSlotsAddsMissingAndReleasesStray(t *testing.T) {
	// A Redis node loading its RDB claimed 0-1 and, for keys of a migrating slot, 9000.
	node := newFakeCluster(map[string]string{"1.1.1.1:30000": "0-1,9000"}).nodes["1.1.1.1:30000"]
	planned, _ := ParseSlots("0-5")
	if err := AssignSlots(portLog{}, node, planned); err != nil {
		t.Fatal(err)
	}
	if want := []string{"delslots 9000", "addslots 2-5"}; !reflect.DeepEqual(node.calls, want) {
		t.Fatalf("calls %v, want %v", node.calls, want)
	}
	if err := AssignSlots(portLog{}, node, planned); err != nil || len(node.calls) != 2 {
		t.Fatalf("a second run must change nothing: %v %v", err, node.calls)
	}
}

func TestAssignSlotsRefusesANodeWithPeers(t *testing.T) {
	c := plannedCluster(threeNodes)
	a, b := c.nodes["1.1.1.1:30000"], c.nodes["2.2.2.2:30000"]
	_ = a.Meet("2.2.2.2", 30000)
	planned, _ := ParseSlots("5461-10922")
	err := AssignSlots(portLog{}, b, planned)
	if err == nil || !strings.Contains(err.Error(), "meet only when the cluster is formed") {
		t.Fatalf("err=%v", err)
	}
}

func TestFormClusterSetsEpochsThenMeets(t *testing.T) {
	c := plannedCluster(threeNodes)
	if err := FormCluster(threeNodes, c.connect, time.Second, time.Millisecond); err != nil {
		t.Fatal(err)
	}
	first := c.nodes["1.1.1.1:30000"]
	want := []string{"set-config-epoch 1", "meet 2.2.2.2:30000", "meet 3.3.3.3:30000"}
	if !reflect.DeepEqual(first.calls, want) {
		t.Fatalf("calls %v, want %v", first.calls, want)
	}
	for addr, epoch := range map[string]int{"1.1.1.1:30000": 1, "2.2.2.2:30000": 2, "3.3.3.3:30000": 3} {
		if n := c.nodes[addr]; n.epoch != epoch || len(n.known) != 3 {
			t.Fatalf("%s epoch=%d known=%d", addr, n.epoch, len(n.known))
		}
	}
}

func TestFormClusterRetrySkipsWhatIsDone(t *testing.T) {
	c := plannedCluster(threeNodes)
	if err := FormCluster(threeNodes, c.connect, time.Second, time.Millisecond); err != nil {
		t.Fatal(err)
	}
	for _, n := range c.nodes {
		n.calls = nil
	}
	if err := FormCluster(threeNodes, c.connect, time.Second, time.Millisecond); err != nil {
		t.Fatal(err)
	}
	for _, n := range c.nodes {
		if len(n.calls) != 0 {
			t.Fatalf("%s called %v on retry", n.addr, n.calls)
		}
	}
}

func TestFormClusterRefusesToMeetANodeOffPlan(t *testing.T) {
	c := plannedCluster(threeNodes)
	delete(c.nodes["2.2.2.2:30000"].slots, 6000)
	err := FormCluster(threeNodes, c.connect, time.Second, time.Millisecond)
	if err == nil || !strings.Contains(err.Error(), "2.2.2.2:30000 owns slots") {
		t.Fatalf("err=%v", err)
	}
	for _, n := range c.nodes {
		for _, call := range n.calls {
			if strings.HasPrefix(call, "meet") {
				t.Fatalf("met despite the mismatch: %v", n.calls)
			}
		}
	}
}

func TestFormClusterFailsOnARoleNotInThePlan(t *testing.T) {
	c := plannedCluster(threeNodes)
	c.nodes["3.3.3.3:30000"].role, c.nodes["3.3.3.3:30000"].masterID = consts.RedisSlaveRole, "id-1.1.1.1:30000"
	err := FormCluster(threeNodes, c.connect, time.Second, time.Millisecond)
	if err == nil || !strings.Contains(err.Error(), "sees 3.3.3.3:30000 as slave") {
		t.Fatalf("err=%v", err)
	}
}

func TestVerifyClusterReportsSlotDifferences(t *testing.T) {
	c := plannedCluster(threeNodes)
	if err := FormCluster(threeNodes, c.connect, time.Second, time.Millisecond); err != nil {
		t.Fatal(err)
	}
	var forming []formingNode
	for _, n := range threeNodes {
		planned, _ := ParseSlots(n.Slots)
		conn, _ := c.connect(n)
		forming = append(forming, formingNode{FormNode: n, conn: conn, planned: planned})
	}
	forming[0].planned = forming[0].planned[1:]
	err := verifyCluster(forming)
	if err == nil || !strings.Contains(err.Error(), "with slots 10923-16383, plan 10924-16383") {
		t.Fatalf("err=%v", err)
	}
}

func TestFormClusterTimesOutWhenNotOK(t *testing.T) {
	c := plannedCluster(threeNodes)
	c.nodes["2.2.2.2:30000"].state = "fail"
	err := FormCluster(threeNodes, c.connect, 20*time.Millisecond, time.Millisecond)
	if err == nil || !strings.Contains(err.Error(), "2.2.2.2:30000 state=fail") {
		t.Fatalf("err=%v", err)
	}
}

func TestFormClusterRejectsAPlanThatDoesNotCoverOnce(t *testing.T) {
	gap := []FormNode{threeNodes[1], threeNodes[2]}
	if err := FormCluster(gap, plannedCluster(gap).connect, time.Second, time.Millisecond); err == nil ||
		!strings.Contains(err.Error(), "covers 10923 of 16384") {
		t.Fatalf("err=%v", err)
	}
	overlap := []FormNode{threeNodes[0], threeNodes[1], {IP: "2.2.2.2", Port: 30000, Slots: "5460-10922"}}
	if err := FormCluster(overlap, plannedCluster(overlap).connect, time.Second, time.Millisecond); err == nil ||
		!strings.Contains(err.Error(), "slot 5460 planned for both") {
		t.Fatalf("err=%v", err)
	}
}
