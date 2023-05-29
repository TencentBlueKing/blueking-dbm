package redistest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisRemoveDtsServerTest dts添加服务测试
type RedisRemoveDtsServerTest struct {
	atomredis.RedisRemoveDtsServerParams
	Err error `json:"-"`
}

// SetPkg set pkg信息
func (test *RedisRemoveDtsServerTest) SetPkg(pkg, pkgMd5 string) *RedisRemoveDtsServerTest {
	if test.Err != nil {
		return test
	}
	if pkg == "" || pkgMd5 == "" {
		pkg = "redis_dts.tar.gz"
		pkgMd5 = "b816b2d47357c3ed7a7864d6730fd33f"
	}
	test.Pkg = pkg
	test.PkgMd5 = pkgMd5
	return test
}

// RunRedisRemoveDtsServer 执行 redis remove dts_server 原子任务
func (test *RedisRemoveDtsServerTest) RunRedisRemoveDtsServer() (err error) {
	msg := fmt.Sprintf("=========RemoveDtsServer test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RemoveDtsServer test fail============")
			fmt.Println(test.Err)
		} else {
			msg = fmt.Sprintf("=========RemoveDtsServer test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	runcmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisRemoveDtsServer().Name(), string(paramBytes))
	fmt.Println(runcmd)
	_, test.Err = util.RunBashCmd(runcmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return test.Err
	}

	return test.Err
}

// RedisRemoveDtsServer dts服务移除测试
func RedisRemoveDtsServer(pkgName, pkgMD5 string) (err error) {
	test := &RedisRemoveDtsServerTest{}
	test.SetPkg(pkgName, pkgMD5)
	if test.Err != nil {
		return test.Err
	}
	err = test.RunRedisRemoveDtsServer()
	return
}
