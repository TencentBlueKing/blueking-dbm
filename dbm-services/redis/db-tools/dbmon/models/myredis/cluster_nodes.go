package myredis

import (
	"fmt"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"
)

const (
	slotSeparator      = "-"
	importingSeparator = "-<-"
	migratingSeparator = "->-"
)

// ClusterNodeData 获取并解析 cluster nodes命令结果
type ClusterNodeData struct {
	NodeID         string         `json:"ID"`
	Addr           string         `json:"addr"`
	IP             string         `json:"ip"` // 如果是k8s中的redis cluster,则ip代表节点的pod名,否则ip表示redis IP
	Port           int            `json:"port"`
	CPort          int            `json:"cport"`
	Role           string         `json:"role"` // master or slave
	IsMyself       bool           `json:"is_myself"`
	LinkState      string         `json:"link_state"` // connected or disconnected
	MasterID       string         `json:"master_iD"`
	FailStatus     []string       `json:"fail_status"`
	PingSent       int64          `json:"ping_sent"`
	PongRecv       int64          `json:"pong_recv"`
	ConfigEpoch    int64          `json:"config_epoch"`
	SlotSrcStr     string         `json:"slot_src_str"`
	Slots          []int          `json:"slots"`
	SlotsMap       map[int]bool   `json:"slots_map"`       // convenient to know whether certain slots belong to the node
	MigratingSlots map[int]string `json:"migrating_slots"` // key:slot,value:dst redis ID
	ImportingSlots map[int]string `json:"importing_slots"` // key:slot.value:src redis ID

	balance    int `json:"-"` // (扩缩容)迁移slot时使用
	endSlotIdx int `json:"-"`
}

// NewDefaultNode builds and returns new defaultNode instance
func NewDefaultNode() *ClusterNodeData {
	return &ClusterNodeData{
		Slots:          []int{},
		SlotsMap:       map[int]bool{},
		MigratingSlots: map[int]string{},
		ImportingSlots: map[int]string{},
	}
}

// String 用于打印
func (n *ClusterNodeData) String() string {
	return fmt.Sprintf(
		`{Redis ID:%s,Addr:%s,role:%s,master:%s,link:%s,status:%s,slots:%s,len(migratingSlots):%d,len(importingSlots):%d}`,
		n.NodeID, n.Addr, n.GetRole(), n.MasterID, n.LinkState, n.FailStatus,
		ConvertSlotToStr(n.Slots), len(n.MigratingSlots), len(n.ImportingSlots))
}

// SetRole from a flags string list set the Node's role
func (n *ClusterNodeData) SetRole(flags string) error {
	n.Role = "" // reset value before setting the new one
	vals := strings.Split(flags, ",")
	for _, val := range vals {
		switch val {
		case consts.RedisMasterRole:
			n.Role = consts.RedisMasterRole
		case consts.RedisSlaveRole:
			n.Role = consts.RedisSlaveRole
		}
	}

	if n.Role == "" {
		err := fmt.Errorf("node setRole failed,addr:%s,flags:%s", n.Addr, flags)
		return err
	}

	return nil
}

// GetRole return the Redis Cluster Node GetRole
func (n *ClusterNodeData) GetRole() string {
	switch n.Role {
	case consts.RedisMasterRole:
		return consts.RedisMasterRole
	case consts.RedisSlaveRole:
		return consts.RedisSlaveRole
	default:
		if n.MasterID != "" {
			return consts.RedisSlaveRole
		}
		if len(n.Slots) > 0 {
			return consts.RedisMasterRole
		}
	}

	return consts.RedisNoneRole
}

// SlotCnt slot count
func (n *ClusterNodeData) SlotCnt() int {
	return len(n.Slots)
}

// SetLinkStatus set the Node link status
func (n *ClusterNodeData) SetLinkStatus(status string) error {
	n.LinkState = "" // reset value before setting the new one
	switch status {
	case consts.RedisLinkStateConnected:
		n.LinkState = consts.RedisLinkStateConnected
	case consts.RedisLinkStateDisconnected:
		n.LinkState = consts.RedisLinkStateDisconnected
	}

	if n.LinkState == "" {
		err := fmt.Errorf("Node SetLinkStatus failed,addr:%s,status:%s", n.Addr, status)
		return err
	}

	return nil
}

// SetFailureStatus set from inputs flags the possible failure status
func (n *ClusterNodeData) SetFailureStatus(flags string) {
	n.FailStatus = []string{} // reset value before setting the new one
	vals := strings.Split(flags, ",")
	for _, val := range vals {
		switch val {
		case consts.NodeStatusFail:
			n.FailStatus = append(n.FailStatus, consts.NodeStatusFail)
		case consts.NodeStatusPFail:
			n.FailStatus = append(n.FailStatus, consts.NodeStatusPFail)
		case consts.NodeStatusHandshake:
			n.FailStatus = append(n.FailStatus, consts.NodeStatusHandshake)
		case consts.NodeStatusNoAddr:
			n.FailStatus = append(n.FailStatus, consts.NodeStatusNoAddr)
		case consts.NodeStatusNoFlags:
			n.FailStatus = append(n.FailStatus, consts.NodeStatusNoFlags)
		}
	}
}

// SetReferentMaster set the redis node parent referent
func (n *ClusterNodeData) SetReferentMaster(ref string) {
	n.MasterID = ""
	if ref == "-" {
		return
	}
	n.MasterID = ref
}

// DecodeClusterNodes decode from the cmd output the Redis nodes info.
// Second argument is the node on which we are connected to request info
func DecodeClusterNodes(input string) ([]*ClusterNodeData, error) {
	infos := []*ClusterNodeData{}
	lines := strings.Split(input, "\n")
	for _, line := range lines {
		values := strings.Fields(line)
		if len(values) < 8 {
			// last line is always empty
			// not enough values in line split, skip line
			mylog.Logger.Info(fmt.Sprintf("not enough values in line split, ignoring line: '%s'", line))
			continue
		} else {
			node := NewDefaultNode()

			node.NodeID = values[0]
			// remove trailing port for cluster internal protocol
			ipPort := strings.Split(values[1], "@")
			node.Addr = ipPort[0]
			if node.Addr != "" {
				list02 := strings.Split(node.Addr, ":")
				if util.IsValidIP(list02[0]) {
					node.IP = list02[0]
				} else {
					l01 := strings.Split(node.Addr, ".")
					if len(l01) > 0 {
						node.IP = l01[0]
					}
				}
				node.Port, _ = strconv.Atoi(list02[1])
			}
			node.CPort, _ = strconv.Atoi(ipPort[1])
			node.SetRole(values[2])
			node.SetFailureStatus(values[2])
			node.SetReferentMaster(values[3])
			if i, err := strconv.ParseInt(values[4], 10, 64); err == nil {
				node.PingSent = i
			}
			if i, err := strconv.ParseInt(values[5], 10, 64); err == nil {
				node.PongRecv = i
			}
			if i, err := strconv.ParseInt(values[6], 10, 64); err == nil {
				node.ConfigEpoch = i
			}
			node.SetLinkStatus(values[7])

			for _, slot := range values[8:] {
				if node.SlotSrcStr == "" {
					node.SlotSrcStr = slot
				} else {
					node.SlotSrcStr = fmt.Sprintf("%s %s", node.SlotSrcStr, slot)
				}
				slots01, _, importingSlots, migratingSlots, err := DecodeSlotsFromStr(slot, " ")
				if err != nil {
					return infos, err
				}
				node.Slots = append(node.Slots, slots01...)
				for _, s01 := range slots01 {
					node.SlotsMap[s01] = true
				}
				for s01, nodeid := range importingSlots {
					node.ImportingSlots[s01] = nodeid
				}
				for s01, nodeid := range migratingSlots {
					node.MigratingSlots[s01] = nodeid
				}
			}

			if strings.HasPrefix(values[2], "myself") {
				node.IsMyself = true
			}
			infos = append(infos, node)
		}
	}

	return infos, nil
}

// IsRunningMaster anonymous function for searching running Master Node
var IsRunningMaster = func(n *ClusterNodeData) bool {
	if (n.GetRole() == consts.RedisMasterRole) &&
		(len(n.FailStatus) == 0) && (n.LinkState == consts.RedisLinkStateConnected) {
		return true
	}
	return false
}

// IsMasterWithSlot anonymous function for searching Master Node withslot
var IsMasterWithSlot = func(n *ClusterNodeData) bool {
	if (n.GetRole() == consts.RedisMasterRole) && (len(n.FailStatus) == 0) &&
		(n.LinkState == consts.RedisLinkStateConnected) && (n.SlotCnt() > 0) {
		return true
	}
	return false
}

// IsRunningNode  anonymous function for searching running  Node
var IsRunningNode = func(n *ClusterNodeData) bool {
	if (len(n.FailStatus) == 0) && (n.LinkState == consts.RedisLinkStateConnected) {
		return true
	}
	return false
}

// DecodeSlotsFromStr 解析 slot 字符串,如 0-10,12,100-200,seq为','
// 同时可以解析:
// migrating slot: ex: [42->-67ed2db8d677e59ec4a4cefb06858cf2a1a89fa1]
// importing slot: ex: [42-<-67ed2db8d677e59ec4a4cefb06858cf2a1a89fa1]
func DecodeSlotsFromStr(slotStr string, seq string) (slots []int, slotMap map[int]bool, migratingSlots,
	importingSlots map[int]string, err error) {
	slotMap = make(map[int]bool)
	migratingSlots = make(map[int]string)
	importingSlots = make(map[int]string)
	var items []string
	var slot int
	if seq == "" || seq == " " || seq == "\t" || seq == "\n" {
		items = strings.Fields(slotStr)
	} else {
		items = strings.Split(slotStr, seq)
	}
	for _, slotItem := range items {
		slotItem = strings.TrimSpace(slotItem)
		list02 := strings.Split(slotItem, slotSeparator)
		if len(list02) == 3 {
			separator := slotSeparator + list02[1] + slotSeparator
			slot, err = strconv.Atoi(strings.TrimPrefix(list02[0], "["))
			if err != nil {
				err = fmt.Errorf("DecodeSlotsFromStr fail,strconv.Atoi err:%v,str:%s", err, slotItem)
				mylog.Logger.Error(err.Error())
				return
			}
			nodeID := strings.TrimSuffix(list02[2], "]")
			if separator == importingSeparator {
				importingSlots[slot] = nodeID
			} else if separator == migratingSeparator {
				migratingSlots[slot] = nodeID
			} else {
				err = fmt.Errorf("impossible to decode slotStr:%s", slotItem)
				mylog.Logger.Error(err.Error())
				return
			}
		} else if len(list02) == 1 {
			num01, _ := strconv.Atoi(list02[0])
			if num01 < consts.DefaultMinSlots || num01 > consts.DefaultMaxSlots {
				err = fmt.Errorf("slot:%d in param:%s not correct,valid range [%d,%d]", num01, slotStr,
					consts.DefaultMinSlots, consts.DefaultMaxSlots)
				mylog.Logger.Error(err.Error())
				return
			}
			slots = append(slots, num01)
			slotMap[num01] = true
		} else if len(list02) == 2 {
			start, _ := strconv.Atoi(list02[0])
			end, _ := strconv.Atoi(list02[1])
			if start < consts.DefaultMinSlots || start > consts.DefaultMaxSlots {
				err = fmt.Errorf("slot:%d in param:%s not correct,valid range [%d,%d]", start, slotStr,
					consts.DefaultMinSlots, consts.DefaultMaxSlots)
				mylog.Logger.Error(err.Error())
				return
			}
			if end < consts.DefaultMinSlots || end > consts.DefaultMaxSlots {
				err = fmt.Errorf("slot:%d in param:%s not correct,valid range [%d,%d]", end, slotStr,
					consts.DefaultMinSlots, consts.DefaultMaxSlots)
				mylog.Logger.Error(err.Error())
				return
			}
			for num01 := start; num01 <= end; num01++ {
				slots = append(slots, num01)
				slotMap[num01] = true
			}
		}
	}
	return
}

// ConvertSlotToStr 将slots:[0,1,2,3,4,10,11,12,13,17] 按照 0-4,10-13,17 打印
func ConvertSlotToStr(slots []int) string {
	if len(slots) == 0 {
		return ""
	}
	str01 := ""
	start := slots[0]
	curr := slots[0]
	for _, item := range slots {
		next := item
		if next == curr {
			continue
		}
		if curr == next-1 {
			// slot连续,继续
			curr = next
			continue
		}
		// slot不连续了
		if start == curr {
			str01 = fmt.Sprintf("%s,%d", str01, start)
		} else {
			str01 = fmt.Sprintf("%s,%d-%d", str01, start, curr)
		}
		start = next
		curr = next
	}
	// 最后再处理一次start curr
	if start == curr {
		str01 = fmt.Sprintf("%s,%d", str01, start)
	} else {
		str01 = fmt.Sprintf("%s,%d-%d", str01, start, curr)
	}
	str01 = strings.Trim(str01, ",")
	return str01
}

// ConvertSlotToShellFormat 将slots:[0,1,2,3,4,10,11,12,13,17] 按照 {0..4} {10..13} 17 打印
func ConvertSlotToShellFormat(slots []int) string {
	if len(slots) == 0 {
		return ""
	}
	str01 := ""
	start := slots[0]
	curr := slots[0]
	for _, item := range slots {
		next := item
		if next == curr {
			continue
		}
		if curr == next-1 {
			// slot连续,继续
			curr = next
			continue
		}
		// slot不连续了
		if start == curr {
			str01 = fmt.Sprintf("%s %d", str01, start)
		} else {
			str01 = fmt.Sprintf("%s {%d..%d}", str01, start, curr)
		}
		start = next
		curr = next
	}
	// 最后再处理一次start curr
	if start == curr {
		str01 = fmt.Sprintf("%s %d", str01, start)
	} else {
		str01 = fmt.Sprintf("%s {%d..%d}", str01, start, curr)
	}
	str01 = strings.Trim(str01, " ")
	return str01
}

// SlotSliceDiff 寻找在slotB中存在,但在 slotA中不存在的slots
func SlotSliceDiff(slotsA []int, slotsB []int) (diffSlots []int) {
	if len(slotsA) == 0 {
		return slotsB
	}
	aMap := make(map[int]struct{})
	for _, slot := range slotsA {
		aMap[slot] = struct{}{}
	}
	for _, slot := range slotsB {
		if _, ok := aMap[slot]; !ok {
			diffSlots = append(diffSlots, slot)
		}
	}
	return
}
