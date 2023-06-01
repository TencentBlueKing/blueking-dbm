package redistest

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisInsKeyPatternJobTest key提取&删除测试
type RedisInsKeyPatternJobTest struct {
	atomredis.RedisInsKeyPatternJobParam
	Err error `json:"-"`
}

// SetBkBizID 设置 BkBizID
func (test *RedisInsKeyPatternJobTest) SetBkBizID(bkBizID string) *RedisInsKeyPatternJobTest {
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
func (test *RedisInsKeyPatternJobTest) SetIP(ip string) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.IP = ip
	return test
}

// SetPorts set ports
// 如果ports=[],startPort=0,instNum=0,则默认startPort=40000,instNum=4
func (test *RedisInsKeyPatternJobTest) SetPorts(ports []int, startPort, instNum int) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	if len(ports) == 0 {
		if startPort == 0 {
			startPort = consts.TestTendisPlusMasterStartPort
		}
		if instNum == 0 {
			instNum = 4
		}
		for i := 0; i < instNum; i++ {
			ports = append(ports, startPort+i)
		}
	}
	test.Ports = ports
	test.StartPort = startPort
	test.InstNum = instNum
	return test
}

// SetPkg set pkg信息,传入为空则pkg=dbtools.tar.gz,pkgMd5=334cf6e3b84d371325052d961584d5aa
func (test *RedisInsKeyPatternJobTest) SetPkg(pkg, pkgMd5 string) *RedisInsKeyPatternJobTest {
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

// SetPath bkrepo 路径
func (test *RedisInsKeyPatternJobTest) SetPath(path string) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	if path == "" {
		path = "/redis/keyfiles/unittest.cache2006.moyecachetest.redistest.db"
	}
	test.Path = path
	return test
}

// SetDomain domain 信息
func (test *RedisInsKeyPatternJobTest) SetDomain(domain string) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	if domain == "" {
		domain = "cache2006.moyecachetest.redistest.db"
	}
	test.Domain = domain
	return test
}

// SetFileServer fileserver 信息
func (test *RedisInsKeyPatternJobTest) SetFileServer(repoUser, repoPassword,
	repoUrl string) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	fileserver := util.FileServerInfo{}
	fileserver.URL = repoUrl
	fileserver.Bucket = "bk-dbm-redistest"
	fileserver.Password = repoPassword
	fileserver.Username = repoUser
	fileserver.Project = "bk-dbm"

	test.FileServer = fileserver
	return test
}

// Setregex 设置key解析黑白名单信息
func (test *RedisInsKeyPatternJobTest) Setregex(whiteKey, blackKey string) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	if whiteKey == "" || blackKey == "" {
		whiteKey = "*hash*\n*set*"
		blackKey = ""
	}
	test.KeyWhiteRegex = whiteKey
	test.KeyBlackRegex = blackKey
	return test
}

// SetDeleteRate 设置删除key且设置key删除速率
func (test *RedisInsKeyPatternJobTest) SetDeleteRate(deleteRate int, keyDel bool) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	if keyDel == false {
		keyDel = true
	}
	test.IsKeysToBeDel = keyDel
	if deleteRate == 0 {
		deleteRate = 2000
	}
	test.DeleteRate = deleteRate
	test.TendisplusDeleteRate = deleteRate
	test.SsdDeleteRate = deleteRate

	return test
}

// checkKeysPatternNums 校验提取结果数量是否符合预期
// 说明：集群写入 400 : *string* ,*hash*,*list*,*set*, 各100个key,提取&删除 *hash* 和 *set* 共200
func (test *RedisInsKeyPatternJobTest) checkKeysPatternNums(startPort int) *RedisInsKeyPatternJobTest {
	if test.Err != nil {
		return test
	}
	var str string
	var len01 int
	mergeFile := filepath.Join("/data/dbbak/get_keys_pattern", fmt.Sprintf("testapp.allPattern.keys.0"))
	var keyFiles string
	if startPort == consts.TestTendisPlusSlaveStartPort {
		str = strconv.Itoa(consts.TestTendisPlusSlaveStartPort)
		len01 = len(str)
		keyFiles = fmt.Sprintf("testapp.%s_%s*.keys", test.IP, str[:len01-1])
	} else if startPort == consts.TestRedisSlaveStartPort {
		str = strconv.Itoa(consts.TestRedisSlaveStartPort)
		len01 = len(str)
		keyFiles = fmt.Sprintf("testapp.%s_%s*.keys.0", test.IP, str[:len01-1])
	} else if startPort == consts.TestTendisSSDSlaveStartPort {
		str = strconv.Itoa(consts.TestTendisSSDSlaveStartPort)
		len01 = len(str)
		keyFiles = fmt.Sprintf("testapp.%s_%s*.keys", test.IP, str[:len01-1])
	}
	fmt.Println("startPort:", startPort)
	mergeCmd := fmt.Sprintf(`cd /data/dbbak/get_keys_pattern 
	flock -x -w 600 ./lock -c  'cat %s > %s '`, keyFiles, mergeFile)
	fmt.Println("mergeCmd:", mergeCmd)
	_, err := util.RunLocalCmd("bash", []string{"-c", mergeCmd}, "", nil, 1*time.Hour)
	if err != nil {
		test.Err = fmt.Errorf("mergeCmd:%s err:%v", mergeCmd, err)
	}

	catCmd := fmt.Sprintf(`cd /data/dbbak/get_keys_pattern 
	flock -x -w 600 ./lock -c  'cat testapp.allPattern.keys.0 |wc -l'`)
	numKeys, err := util.RunLocalCmd("bash", []string{"-c", catCmd}, "", nil, 1*time.Hour)
	if err != nil {
		test.Err = fmt.Errorf("mergeCmd:%s err:%v", mergeCmd, err)
	}
	if numKeys == "200" {
		msg := fmt.Sprintf("numKeys=%s 提取key个数符合预期", numKeys)
		fmt.Println(msg)
	} else {
		msg := fmt.Errorf("提取key个数为%s 不符合预期200个key,请检查写入数据是否有更改或者是否改动提取key部分代码:"+
			"说明：写入 400 : *string* ,*hash*,*list*,*set*, 各100个key,提取&删除 *hash* 和 *set* 共200", numKeys)
		fmt.Printf("checkKeysPatternNums failed: %v", msg)
		test.Err = msg

	}
	return test
}

// RunRedisKeyspattern 执行 redis keyspattern 原子任务
func (test *RedisInsKeyPatternJobTest) RunRedisKeyspattern(startPort int) {

	// 写入 400 : *string* ,*hash*,*list*,*set*, 各100个key,提取"hash* 和 *set* 共200
	msg := fmt.Sprintf("=========keyspattern test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========keyspattern test fail============")
			fmt.Println(test.Err)
		} else {
			msg = fmt.Sprintf("=========keyspattern test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewTendisKeysPattern().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	// 校验提取结果数量是否符合预期
	test.checkKeysPatternNums(startPort)
	return
}

// Keyspattern redis keyspattern 测试
func Keyspattern(serverIP string, ports []int, startPort, instNum int, repoUser,
	repoPassword, repoUrl, dbtoolsPkgName, dbtoolsPkgMd5 string) (err error) {
	keyspatternTest := RedisInsKeyPatternJobTest{}
	var clientPort int
	if startPort == consts.TestTendisPlusSlaveStartPort {
		clientPort = consts.TestTendisPlusMasterStartPort
	} else if startPort == consts.TestRedisSlaveStartPort {
		clientPort = consts.TestRedisMasterStartPort
	} else if startPort == consts.TestTendisSSDSlaveStartPort {
		clientPort = consts.TestTendisSSDMasterStartPort
	} else {
		fmt.Printf("redisKeyspatternTest failed :请确认输入的startPort是否是定义的:TendisPlusSlaveStartPort或者RedisSlaveStartPort")
		keyspatternTest.Err = fmt.Errorf(
			"请确认输入的是否是定义的:TendisPlusSlaveStartPort或者RedisSlaveStartPort或者TestTendisSSDSlaveStartPort")
		return keyspatternTest.Err
	}
	keyspatternTest.SetBkBizID("testapp").
		SetIP(serverIP).SetPorts(ports, startPort, instNum).
		SetPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetPath("").SetDomain("").SetFileServer(repoUser, repoPassword, repoUrl).
		Setregex("", "").SetDeleteRate(0, true)
	keyspatternTest.RunRedisKeyspattern(startPort)
	if keyspatternTest.Err != nil {
		return keyspatternTest.Err
	}

	// 在proxy上验证数据正则提取和删除结果;ssd 不支持scan ,和其他校验不同
	if startPort == consts.TestTendisSSDSlaveStartPort {
		fmt.Printf("-----------SSDDelKeysCheck-----------")
		fmt.Println()
		cmdTest, err := NewCommandTest(serverIP, consts.TestSSDClusterTwemproxyPort, consts.ProxyTestPasswd,
			consts.TendisTypeTwemproxyTendisSSDInstance, 0)

		if err != nil {
			return err
		}
		// err = cmdTest.SSDDelKeysCheck()
		err = cmdTest.KeyTypeCheck()

		if err != nil {
			fmt.Printf("SSDDelKeysCheck failed: %v", err)
			return err
		}
	} else {
		fmt.Printf("-----------DelKeysCheck-----------")
		cmdTest, err := NewCommandTest(serverIP, clientPort, consts.RedisTestPasswd,
			consts.TendisTypeRedisInstance, 0)

		if err != nil {
			return err
		}
		err = cmdTest.DelKeysCheck()
		if err != nil {
			fmt.Printf("DelKeysCheck failed: %v", err)
			return err
		}

	}

	return keyspatternTest.Err
}
