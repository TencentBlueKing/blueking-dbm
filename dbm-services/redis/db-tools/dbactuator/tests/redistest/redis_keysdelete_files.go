package redistest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisKeysFilesDeleteJobTest key提取&删除测试
type RedisKeysFilesDeleteJobTest struct {
	atomredis.TendisKeysFilesDeleteParams
	Err error `json:"-"`
}

// SetBkBizID 设置 BkBizID
func (test *RedisKeysFilesDeleteJobTest) SetBkBizID(bkBizID string) *RedisKeysFilesDeleteJobTest {
	if test.Err != nil {
		return test
	}
	if bkBizID == "" {
		bkBizID = "testapp"
	}
	test.BkBizID = bkBizID
	return test
}

// SetDomain domain 信息
func (test *RedisKeysFilesDeleteJobTest) SetDomain(domain string) *RedisKeysFilesDeleteJobTest {
	if test.Err != nil {
		return test
	}
	// 不传domain 则测试本地创建集群，传线上域名，开通访问也是可以的
	if domain == "" {
		domain, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.Domain = domain
	return test
}

// SetDbType 设置DbType,默认为 TendisplusInstance
func (test *RedisKeysFilesDeleteJobTest) SetDbType(dbType string) *RedisKeysFilesDeleteJobTest {
	if test.Err != nil {
		return test
	}
	if dbType == "" {
		dbType = "TendisplusInstance"
	}
	test.TendisType = dbType
	return test
}

// SetPorts 设置 proxyPort 传入0 则默认为 proxyPort =consts.TestPredixyPort
func (test *RedisKeysFilesDeleteJobTest) SetPorts(proxyPort int) *RedisKeysFilesDeleteJobTest {
	if test.Err != nil {
		return test
	}
	// 不传端口， 则测试本地创建集群，传线上端口，开通访问也是可以的
	if proxyPort == 0 {
		proxyPort = consts.TestPredixyPort
	}
	test.ProxyPort = proxyPort
	return test

}

// SetPkg 设置 pkg信息,传入为空则pkg=dbtools.tar.gz,pkgMd5=334cf6e3b84d371325052d961584d5aa
func (test *RedisKeysFilesDeleteJobTest) SetPkg(pkg, pkgMd5 string) *RedisKeysFilesDeleteJobTest {
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

// SetPath  设置 bkrepo 路径
func (test *RedisKeysFilesDeleteJobTest) SetPath(path string) *RedisKeysFilesDeleteJobTest {
	if test.Err != nil {
		return test
	}
	if path == "" {
		// 包含 *string* 的key
		path = "/redis/keyfiles/fileDeleteUnitTest.cache2006.moyecachetest.redistest.db"
	}
	test.Path = path
	return test
}

// SetFileServer fileserver 信息
func (test *RedisKeysFilesDeleteJobTest) SetFileServer(repoUser, repoPassword,
	repoUrl string) *RedisKeysFilesDeleteJobTest {
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

// SetDeleteRate 设置删除key且设置key删除速率
func (test *RedisKeysFilesDeleteJobTest) SetDeleteRate(deleteRate int) *RedisKeysFilesDeleteJobTest {
	if test.Err != nil {
		return test
	}
	if deleteRate == 0 {
		deleteRate = 2000
	}
	test.DeleteRate = deleteRate
	test.TendisplusDeleteRate = deleteRate
	return test
}

// SetProxyPassword set proxy password,传入为空则password=xxxx
func (test *RedisKeysFilesDeleteJobTest) SetProxyPassword(proxyPasswd string) *RedisKeysFilesDeleteJobTest {
	if test.Err != nil {
		return test
	}
	// 这里需要和test.go 里定义保持一致
	if proxyPasswd == "" {
		proxyPasswd = "proxyPassTest"
	}
	test.ProxyPassword = proxyPasswd
	return test
}

// RunRedisKeysFilesDelete 执行 redis keysfiles delete 原子任务
func (test *RedisKeysFilesDeleteJobTest) RunRedisKeysFilesDelete() {
	msg := fmt.Sprintf("=========redis keysfiles deletetest start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========redis keysfiles delete test fail============")
		} else {
			msg = fmt.Sprintf("=========redis keysfiles delete test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewTendisKeysFilesDelete().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// KeysFilesDelete redis keysfiles delete test 测试
func KeysFilesDelete(serverIP string, proxyPort int,
	repoUser, repoPassword, repoUrl, dbtoolsPkgName, dbtoolsPkgMd5 string) (err error) {
	keysFilesDeleteTest := RedisKeysFilesDeleteJobTest{}
	var clientPort int
	if proxyPort == consts.TestPredixyPort {
		clientPort = consts.TestTendisPlusMasterStartPort
	} else if proxyPort == consts.TestTwemproxyPort {
		clientPort = consts.TestRedisMasterStartPort
	} else if proxyPort == consts.TestSSDClusterTwemproxyPort {
		clientPort = consts.TestTendisSSDMasterStartPort
	} else {
		fmt.Printf("redisKeyspatternTest failed :请确认输入的proxyPort是否是定义的:TemproxyPort或者PredixyPort")
		keysFilesDeleteTest.Err = fmt.Errorf("请确认输入的是否是定义的:TemproxyPort或者PredixyPort或者TestSSDClusterTwemproxyPort")
		return keysFilesDeleteTest.Err
	}
	keysFilesDeleteTest.SetBkBizID("testapp").
		SetDomain("").SetDbType("").
		SetPorts(proxyPort).
		SetPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetPath("").SetFileServer(repoUser, repoPassword, repoUrl).
		SetDeleteRate(0).SetProxyPassword("")
	keysFilesDeleteTest.RunRedisKeysFilesDelete()
	if keysFilesDeleteTest.Err != nil {
		return keysFilesDeleteTest.Err
	}

	// 在proxy上验证数据正则提取和删除结果;ssd 不支持scan ,和其他校验不同
	if proxyPort == consts.TestSSDClusterTwemproxyPort {
		fmt.Printf("-----------SSD FileDelKeyTypeCheck -----------")
		fmt.Println()
		cmdTest, err := NewCommandTest(serverIP, consts.TestSSDClusterTwemproxyPort, consts.ProxyTestPasswd,
			consts.TendisTypeTwemproxyTendisSSDInstance, 0)

		if err != nil {
			return err
		}
		err = cmdTest.FileDelKeyTypeCheck()

		if err != nil {
			fmt.Printf("SSDDelKeysCheck failed: %v", err)
			return err
		}

	} else {
		cmdTest, err := NewCommandTest(serverIP, clientPort, consts.RedisTestPasswd,
			consts.TendisTypeRedisInstance, 0)
		if err != nil {
			return err
		}
		// 选一个节点验证数据正则提取和删除结果
		err = cmdTest.FileDelKeysCheck()
		if err != nil {
			fmt.Printf("file delete fail:%v", err)
			return err
		}

	}
	return keysFilesDeleteTest.Err
}
