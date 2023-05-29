package myredis

import (
	"fmt"
	"testing"

	"github.com/smartystreets/goconvey/convey"
)

// test unit
func TestDecodeClusterNodes(t *testing.T) {
	convey.Convey("cluster nodes decode", t, func() {
		clusterNodesStr := `
	17922e98b0b8f7a9d233422cf8ae55f2d22fdab7 127.0.0.4:30003@40003 master - 0 1655005291000 20 connected 7509-8191
	e81c4276dce41ae3ed4a5fe18e460ed5b9f77e8b 127.0.0.3:30003@40003 slave 17922e98b0b8f7a9d233422cf8ae55f2d22fdab7 0 1655005291000 20 connected
	56e53ca70ef13f3ca1817b0746d64319a4b66fed synctest-redis-rdsplus1-0.synctest-svc.vip:30000@40000 myself,slave 72ffcd1f8d39d1b6011ab38f5e1a42dd6f66f765 0 1655006313000 3 connected
	72ffcd1f8d39d1b6011ab38f5e1a42dd6f66f765 synctest-redis-rdsplus1-1.synctest-svc.vip:30000@40000 master - 0 1655006315419 7 connected 5461-10921
	`
		nodes, err := DecodeClusterNodes(clusterNodesStr)
		if err != nil {
			t.Fatalf(err.Error())
		}
		convey.So(len(nodes), convey.ShouldEqual, 4)
		convey.So(nodes[0].NodeID, convey.ShouldEqual, "17922e98b0b8f7a9d233422cf8ae55f2d22fdab7")
		convey.So(nodes[0].IP, convey.ShouldEqual, "127.0.0.4")
		convey.So(nodes[0].Port, convey.ShouldEqual, 30003)
		convey.So(nodes[0].SlotsMap, convey.ShouldContainKey, 7560)
		convey.So(nodes[1].MasterID, convey.ShouldEqual, "17922e98b0b8f7a9d233422cf8ae55f2d22fdab7")
		convey.So(IsMasterWithSlot(nodes[0]), convey.ShouldBeTrue)
		convey.So(nodes[2].IP, convey.ShouldEqual, "synctest-redis-rdsplus1-0")
		convey.So(IsMasterWithSlot(nodes[3]), convey.ShouldBeTrue)
		convey.So(nodes[3].SlotsMap, convey.ShouldContainKey, 5470)
	})

	convey.Convey("cluster nodes decode2", t, func() {
		clusterNodesStr := `36b96240e16051711d2391472cfd5900d33dc8bd 127.0.0.5:46000@56000 master - 0 1660014754278 5 connected
a32f9cb266d85ea96a1a87ce56872f339e2a257f 127.0.0.5:45001@55001 master - 0 1660014755280 4 connected 5462-10923
5d555b4ab569de196f71afd275c1edf8c046959a 127.0.0.5:45000@55000 myself,master - 0 1660014753000 1 connected 0-5461
90ed7be9db5e4b78e959ad3b40253c2ffb3d5845 127.0.0.5:46002@56002 master - 0 1660014752269 3 connected
dcff36cc5e915024d12173b1c5a3235e9186f193 127.0.0.5:46001@56001 master - 0 1660014753273 2 connected
ff29e2e2782916a0451d5f4064cb55483f4b2a97 127.0.0.5:45002@55002 master - 0 1660014753000 0 connected 10924-16383
`
		nodes, err := DecodeClusterNodes(clusterNodesStr)
		if err != nil {
			t.Fatalf(err.Error())
		}
		var selfNode *ClusterNodeData = nil
		for _, node01 := range nodes {
			nodeItem := node01
			if nodeItem.IsMyself {
				selfNode = nodeItem
				break
			}
		}
		fmt.Printf("%s\n", selfNode.String())
		convey.So(IsMasterWithSlot(selfNode), convey.ShouldBeTrue)
	})

	convey.Convey("decode slots from string", t, func() {
		slotStr := "0-10,12,100-200"
		slots, slotMap, _, _, err := DecodeSlotsFromStr(slotStr, ",")
		if err != nil {
			t.Fatalf(err.Error())
		}
		convey.So(len(slots), convey.ShouldEqual, 11+1+101)
		convey.So(slotMap, convey.ShouldContainKey, 12)
		convey.So(slotMap, convey.ShouldNotContainKey, 11)
		// convey.So(len(migratingSlots), convey.ShouldEqual, 0)
		// convey.So(len(importingSlots), convey.ShouldEqual, 0)

		slotStr = "[93-<-292f8b365bb7edb5e285caf0b7e6ddc7265d2f4f] [77->-e7d1eecce10fd6bb5eb35b9f99a514335d9ba9ca]"
		_, _, migratingSlots, importingSlots, err := DecodeSlotsFromStr(slotStr, " ")
		if err != nil {
			t.Fatalf(err.Error())
		}
		// convey.So(len(slots), convey.ShouldEqual, 0)
		// convey.So(len(slotMap), convey.ShouldEqual, 0)
		convey.So(migratingSlots, convey.ShouldContainKey, 77)
		convey.So(importingSlots, convey.ShouldContainKey, 93)
		convey.So(importingSlots[93], convey.ShouldEqual, "292f8b365bb7edb5e285caf0b7e6ddc7265d2f4f")
	})
	convey.Convey("convert slot slice to string", t, func() {
		slots := []int{0, 1, 2, 3, 4, 10, 11, 12, 13, 17}
		str01 := ConvertSlotToStr(slots)
		convey.So(str01, convey.ShouldEqual, "0-4,10-13,17")
	})
}
