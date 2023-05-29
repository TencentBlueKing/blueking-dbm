package redistest

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-redis/redis/v8"
)

// RedisDtsDataCheckJobTest dts数据校验测试
type RedisDtsDataCheckJobTest struct {
	atomredis.RedisDtsDataCheckAndRpaireParams
	Err error `json:"-"`
}

// SetBkBizID 设置 BkBizID
func (test *RedisDtsDataCheckJobTest) SetBkBizID(bkBizID string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	if bkBizID == "" {
		bkBizID = "testapp"
	}
	test.BkBizID = bkBizID
	return test
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *RedisDtsDataCheckJobTest) SetIP(ip string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.SrcRedisIP = ip
	return test
}

// SetPkg set pkg信息,传入为空则pkg=dbtools.tar.gz,pkgMd5=334cf6e3b84d371325052d961584d5aa
func (test *RedisDtsDataCheckJobTest) SetPkg(pkg, pkgMd5 string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	if pkg == "" || pkgMd5 == "" {
		pkg = "dbtools.tar.gz"
		pkgMd5 = "334cf6e3b84d371325052d961584d5aa"
	}
	test.Pkg = pkg
	test.PkgMd5 = pkgMd5
	return test
}

// SetDtsType set dts type
func (test *RedisDtsDataCheckJobTest) SetDtsType(dtsType string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.DtsCopyType = dtsType
	return test
}

// SetPortSegmentList set ports
func (test *RedisDtsDataCheckJobTest) SetPortSegmentList(ports []atomredis.PortAndSegment) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.SrcRedisPortSegmentList = ports
	return test
}

// SetSrcClusterAddr set src cluster addr
func (test *RedisDtsDataCheckJobTest) SetSrcClusterAddr(srcClusterAddr string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.SrcClusterAddr = srcClusterAddr
	return test
}

// SetSrcReddisPassword set src redis password
func (test *RedisDtsDataCheckJobTest) SetSrcReddisPassword(srcRedisPasswd string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.SrcRedisPassword = srcRedisPasswd
	return test
}

// SetDtsClusterAddr set dst cluster addr
func (test *RedisDtsDataCheckJobTest) SetDtsClusterAddr(dstClusterAddr string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.DstClusterAddr = dstClusterAddr
	return test
}

// SetDstClusterPassword set dst cluster password
func (test *RedisDtsDataCheckJobTest) SetDstClusterPassword(dstClusterPasswd string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.DstClusterPassword = dstClusterPasswd
	return test
}

// SetKeyWhiteRegex  set key white regex
func (test *RedisDtsDataCheckJobTest) SetKeyWhiteRegex(whiteRegex string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.KeyWhiteRegex = whiteRegex
	return test
}

// SetKeyBlackRegex set key black regex
func (test *RedisDtsDataCheckJobTest) SetKeyBlackRegex(blackRegex string) *RedisDtsDataCheckJobTest {
	if test.Err != nil {
		return test
	}
	test.KeyBlackRegex = blackRegex
	return test
}

// RunRedisDtsDataCheck 执行 redis dts datacheck 原子任务
func (test *RedisDtsDataCheckJobTest) RunRedisDtsDataCheck() (ret string) {
	// 写入 400 : *string* ,*hash*,*list*,*set*, 各100个key,提取"hash* 和 *set* 共200
	msg := fmt.Sprintf("=========dtsDataCheck test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========dtsDataCheck test fail============")
			fmt.Println(test.Err)
		} else {
			msg = fmt.Sprintf("=========dtsDataCheck test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	runcmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisDtsDataCheck().Name(), string(paramBytes))
	fmt.Println(runcmd)
	ret, test.Err = util.RunBashCmd(runcmd, "", nil, 1*time.Hour)
	if test.Err != nil && !strings.Contains(test.Err.Error(), "totalDiffKeysCnt:") {
		return
	}
	ret = test.Err.Error()
	test.Err = nil

	return
}

// genSomeDiffKeys 伪造master=>slave之间两条不一致的数据
func genSomeDiffKeys(srcAddr, srcPassword, dstAddr, dtsPassword string) {
	var err error
	var masterCli, slaveCli *myredis.RedisClient
	var member *redis.Z
	masterCli, err = myredis.NewRedisClientWithTimeout(srcAddr, srcPassword, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return
	}
	defer masterCli.Close()

	slaveCli, err = myredis.NewRedisClientWithTimeout(dstAddr, dtsPassword, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return
	}
	defer slaveCli.Close()

	// 伪造master=>slave之间两条不一致的数据
	_, err = slaveCli.ConfigSet("slave-read-only", "no")
	if err != nil {
		return
	}
	keyName := "dts_diff_string"
	_, err = masterCli.Set(keyName, "val100", 0)
	if err != nil {
		return
	}
	_, err = slaveCli.DelForce(keyName)
	if err != nil {
		return
	}
	keyName = "dts_diff_zset"
	todelMems := []interface{}{}
	for idx := 0; idx < 100; idx++ {
		member = &redis.Z{
			Score:  float64(idx),
			Member: "member:" + strconv.Itoa(idx),
		}
		masterCli.Zadd(keyName, []*redis.Z{member})
		if idx%10 == 0 {
			todelMems = append(todelMems, member.Member)
		}
	}
	slaveCli.Zrem(keyName, todelMems...)
}

// RunReplicaPairDataCheck 利用一对主从 做数据校验
func RunReplicaPairDataCheck(masterIP string, masterPort int, masterPasswd,
	slaveIP string, slavePort int, slavePasswd string, dbtoolsPkgName, dbtoolsPkgMd5 string) (err error) {
	masterAddr := masterIP + ":" + strconv.Itoa(masterPort)
	slaveAddr := slaveIP + ":" + strconv.Itoa(slavePort)

	genSomeDiffKeys(masterAddr, masterPasswd, slaveAddr, slavePasswd)

	// 进行数据校验
	dataCheck := RedisDtsDataCheckJobTest{}
	portSegmentList := []atomredis.PortAndSegment{}
	portSegmentList = append(portSegmentList, atomredis.PortAndSegment{
		Port:         masterPort,
		SegmentStart: -1,
		SegmentEnd:   -1,
	})
	dataCheck.SetBkBizID("testapp").SetIP(masterIP).SetPortSegmentList(portSegmentList).
		SetPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetDtsType(consts.DtsTypeOneAppDiffCluster).
		SetSrcClusterAddr(masterAddr).SetSrcReddisPassword(masterPasswd).
		SetDtsClusterAddr(slaveAddr).SetDstClusterPassword(slavePasswd).
		SetKeyWhiteRegex("*").SetKeyBlackRegex("")

	ret := dataCheck.RunRedisDtsDataCheck()
	if dataCheck.Err != nil {
		return dataCheck.Err
	}
	if !strings.Contains(ret, "totalDiffKeysCnt:1") {
		fmt.Printf("====>%s\n", ret)
	}

	return
}
