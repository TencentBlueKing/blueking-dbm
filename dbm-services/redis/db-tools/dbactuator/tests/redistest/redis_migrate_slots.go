package redistest

import (
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"strconv"
	"time"
)

// TendisPlusMigrateSlotsTest slots 迁移测试
type TendisPlusMigrateSlotsTest struct {
	atomredis.TendisPlusMigrateSlotsParams
	Err error `json:"-"`
}

// SetMigrateSpecifiedSlot set MigrateSpecifiedSlot
func (test *TendisPlusMigrateSlotsTest) SetMigrateSpecifiedSlot(migrateSpecifiedSlot bool) *TendisPlusMigrateSlotsTest {
	if test.Err != nil {
		return test
	}
	test.MigrateSpecifiedSlot = migrateSpecifiedSlot
	return test
}

// SetSlots 设置迁移slots
func (test *TendisPlusMigrateSlotsTest) SetSlots(slots string) *TendisPlusMigrateSlotsTest {
	if test.Err != nil {
		return test
	}
	if slots == "" {
		test.Err = fmt.Errorf("TendisPlusMigrateSlotsTest Slots(%s) cannot be empty", slots)
		fmt.Println(test.Err.Error())
		return test
	}
	test.Slots = slots
	return test
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *TendisPlusMigrateSlotsTest) SetIP(ip string) *TendisPlusMigrateSlotsTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.SrcNode.IP = ip
	test.DstNode.IP = ip
	return test
}

// SetSrcNodeItem 设置迁移slots目标节点
func (test *TendisPlusMigrateSlotsTest) SetSrcNodeItem(password string, port int) *TendisPlusMigrateSlotsTest {
	if test.Err != nil {
		return test
	}

	if password == "" {
		test.Err = fmt.Errorf("ClusterMeetTest password(%s) cannot be empty", password)
		fmt.Println(test.Err.Error())
		return test
	}
	test.SrcNode.Password = password
	if port == 0 {
		test.Err = fmt.Errorf("ClusterMeetTest port(%d) cannot be empty", port)
		fmt.Println(test.Err.Error())
		return test
	}
	test.SrcNode.Port = port
	return test
}

// SetDstNodeItem 设置迁移slots源节点
func (test *TendisPlusMigrateSlotsTest) SetDstNodeItem(password string, port int) *TendisPlusMigrateSlotsTest {
	if test.Err != nil {
		return test
	}

	if password == "" {
		test.Err = fmt.Errorf("ClusterMeetTest password(%s) cannot be empty", password)
		fmt.Println(test.Err.Error())
		return test
	}
	test.DstNode.Password = password
	if port == 0 {
		test.Err = fmt.Errorf("ClusterMeetTest port(%d) cannot be empty", port)
		fmt.Println(test.Err.Error())
		return test
	}
	test.DstNode.Port = port
	return test
}

// MigrateSpecificSlots redis slots 迁移 测试
func MigrateSpecificSlots(localIP, password string, srcPort, dstPort int) (err error) {
	migrateSlotsTest := TendisPlusMigrateSlotsTest{}
	// SlotsMigrateTest             = "0-100"
	migrateSlotsTest.SetSlots(consts.SlotsMigrateTest).
		SetMigrateSpecifiedSlot(true).
		SetIP(localIP).
		SetSrcNodeItem(password, srcPort).
		SetDstNodeItem(password, dstPort)

	if migrateSlotsTest.Err != nil {
		return migrateSlotsTest.Err
	}
	migrateSlotsTest.RunTendisPlusMigrateSlotsTest()
	if migrateSlotsTest.Err != nil {
		return migrateSlotsTest.Err
	}

	srcNodeAddr := localIP + ":" + strconv.Itoa(dstPort)

	// 获取源节点连接&信息
	dstNodeCli, err := myredis.NewRedisClient(srcNodeAddr,
		password, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		err = fmt.Errorf("get dst NewRedisClient Err:%v", err)
		fmt.Println(err.Error())
		return
	}
	slots, _, _, _, err := myredis.DecodeSlotsFromStr(consts.SlotsMigrateTest, " ")
	if err != nil {
		fmt.Println(err.Error())
		return err
	}
	// job.runtime.Logger.Info("clusterNodes:%+v", clusterNodes)
	allBelong, notBelongList, err := dstNodeCli.IsSlotsBelongMaster(srcNodeAddr, slots)
	if err != nil {
		err = fmt.Errorf("check  IsSlotsBelongMaster  Err:%v", err)
		fmt.Println(err.Error())
		return err
	}
	if allBelong == false {
		err = fmt.Errorf("check slots:%s not belong to srcNode:%s",
			util.IntSliceToString(notBelongList, ","), srcNodeAddr)
		fmt.Println(err.Error())
		return err
	}
	msg := fmt.Sprintf("consts.SlotsMigrateTest Is Belong dstMaster MigrateSpecificSlots success ")
	fmt.Println(msg)
	return migrateSlotsTest.Err
}

// Rebalance redis slots 迁移扩容 测试
func Rebalance(localIP, password string, srcPort, dstPort int) (err error) {
	migrateSlotsTest := TendisPlusMigrateSlotsTest{}

	migrateSlotsTest.SetSlots(consts.SlotsMigrateTest).
		SetMigrateSpecifiedSlot(false).
		SetIP(localIP).
		SetSrcNodeItem(password, srcPort).
		SetDstNodeItem(password, dstPort)

	if migrateSlotsTest.Err != nil {
		return migrateSlotsTest.Err
	}
	migrateSlotsTest.RunTendisPlusMigrateSlotsTest()
	if migrateSlotsTest.Err != nil {
		return migrateSlotsTest.Err
	}
	return migrateSlotsTest.Err
}

// RunTendisPlusMigrateSlotsTest 建立集群关系和slots分配
func (test *TendisPlusMigrateSlotsTest) RunTendisPlusMigrateSlotsTest() {
	msg := fmt.Sprintf("=========TendisPlusMigrateSlotsTest test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========TendisPlusMigrateSlotsTest  fail============")
		} else {
			msg = fmt.Sprintf("=========TendisPlusMigrateSlotsTest  success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewTendisPlusMigrateSlots().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}
