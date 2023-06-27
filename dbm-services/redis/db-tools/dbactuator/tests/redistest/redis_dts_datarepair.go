package redistest

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisDtsDataRepairJobTest dts数据修复测试
type RedisDtsDataRepairJobTest struct {
	RedisDtsDataCheckJobTest
}

// RunRedisDtsDataRepair 执行 redis dts datarepair原子任务
func (test *RedisDtsDataCheckJobTest) RunRedisDtsDataRepair() (ret string) {
	// 写入 400 : *string* ,*hash*,*list*,*set*, 各100个key,提取"hash* 和 *set* 共200
	msg := fmt.Sprintf("=========dtsDataRepair test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========dtsDataRepair test fail============")
			fmt.Println(test.Err)
		} else {
			msg = fmt.Sprintf("=========dtsDataRepair test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	runcmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisDtsDataRepair().Name(), string(paramBytes))
	fmt.Println(runcmd)
	ret, test.Err = util.RunBashCmd(runcmd, "", nil, 1*time.Hour)
	if test.Err != nil && !strings.Contains(test.Err.Error(), "totalHotKeysCnt:") {
		return
	} else if test.Err != nil {
		ret = test.Err.Error()
		test.Err = nil
	}

	return
}

// RunReplicaPairDataRepair 利用一对主从 做数据修复
func RunReplicaPairDataRepair(masterIP string, masterPort int, masterPasswd,
	slaveIP string, slavePort int, slavePasswd string, dbtoolsPkgName, dbtoolsPkgMd5 string) (err error) {
	masterAddr := masterIP + ":" + strconv.Itoa(masterPort)
	slaveAddr := slaveIP + ":" + strconv.Itoa(slavePort)

	// 进行数据校验
	dataRepair := RedisDtsDataRepairJobTest{}
	portSegmentList := []atomredis.PortAndSegment{}
	portSegmentList = append(portSegmentList, atomredis.PortAndSegment{
		Port:         masterPort,
		SegmentStart: -1,
		SegmentEnd:   -1,
	})
	dataRepair.SetBkBizID("testapp").SetIP(masterIP).SetPortSegmentList(portSegmentList).
		SetPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetDtsType(consts.DtsTypeOneAppDiffCluster).
		SetSrcClusterAddr(masterAddr).SetSrcReddisPassword(masterPasswd).
		SetDtsClusterAddr(slaveAddr).SetDstClusterPassword(slavePasswd).
		SetKeyWhiteRegex("*").SetKeyBlackRegex("")

	dataRepair.RunRedisDtsDataRepair()
	if dataRepair.Err != nil {
		return dataRepair.Err
	}

	return
}
