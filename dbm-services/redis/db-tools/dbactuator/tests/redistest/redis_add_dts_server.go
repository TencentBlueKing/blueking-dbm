package redistest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisAddDtsServerTest dts添加服务测试
type RedisAddDtsServerTest struct {
	atomredis.RedisAddDtsServerParams
	Err error `json:"-"`
}

// SetPkg set pkg信息
func (test *RedisAddDtsServerTest) SetPkg(pkg, pkgMd5 string) *RedisAddDtsServerTest {
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

// SetBkDbmNginxURL set bk dbm nginx url
func (test *RedisAddDtsServerTest) SetBkDbmNginxURL(dbmNginxURL string) *RedisAddDtsServerTest {
	if test.Err != nil {
		return test
	}
	test.BkDbmNginxURL = dbmNginxURL
	return test
}

// SetBkDbmCloudID set bk dbm cloud id
func (test *RedisAddDtsServerTest) SetBkDbmCloudID(dbmCloudID int64) *RedisAddDtsServerTest {
	if test.Err != nil {
		return test
	}
	test.BkDbmCloudID = dbmCloudID
	return test
}

// SetBkDbmCloudToken set bk dbm cloud token
func (test *RedisAddDtsServerTest) SetBkDbmCloudToken(dbmCloudToken string) *RedisAddDtsServerTest {
	if test.Err != nil {
		return test
	}
	test.BkDbmCloudToken = dbmCloudToken
	return test
}

// SetSystemUser set system user
func (test *RedisAddDtsServerTest) SetSystemUser(systemUser string) *RedisAddDtsServerTest {
	if test.Err != nil {
		return test
	}
	test.SystemUser = systemUser
	return test
}

// SetSystemPassword set system password
func (test *RedisAddDtsServerTest) SetSystemPassword(systemPassword string) *RedisAddDtsServerTest {
	if test.Err != nil {
		return test
	}
	test.SystemPassword = systemPassword
	return test
}

// SetCityName set city name
func (test *RedisAddDtsServerTest) SetCityName(cityName string) *RedisAddDtsServerTest {
	if test.Err != nil {
		return test
	}
	test.CityName = cityName
	return test
}

// SetWarningMsgNotifiers set warning msg notifiers
func (test *RedisAddDtsServerTest) SetWarningMsgNotifiers(notifiers string) *RedisAddDtsServerTest {
	if test.Err != nil {
		return test
	}
	test.WarningMsgNotifiers = notifiers
	return test
}

// RunRedisAddDtsServer 执行 redis add dts_server 原子任务
func (test *RedisAddDtsServerTest) RunRedisAddDtsServer() (err error) {
	msg := fmt.Sprintf("=========AddDtsServer test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========AddDtsServer test fail============")
			fmt.Println(test.Err)
		} else {
			msg = fmt.Sprintf("=========AddDtsServer test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	runcmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisAddDtsServer().Name(), string(paramBytes))
	fmt.Println(runcmd)
	_, test.Err = util.RunBashCmd(runcmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return test.Err
	}

	return test.Err
}

// RedisAddDtsServer dts服务部署测试
func RedisAddDtsServer(pkgName, pkgMD5, dbmNginxURL string, dbmCloudID int64,
	dbmCloudToken, systemUser, systemPassword, cityName, notifiers string) (err error) {
	test := &RedisAddDtsServerTest{}
	test.SetPkg(pkgName, pkgMD5).
		SetBkDbmNginxURL(dbmNginxURL).
		SetBkDbmCloudID(dbmCloudID).SetBkDbmCloudToken(dbmCloudToken).
		SetSystemUser(systemUser).SetSystemPassword(systemPassword).
		SetCityName(cityName).SetWarningMsgNotifiers(notifiers)
	if test.Err != nil {
		return test.Err
	}
	err = test.RunRedisAddDtsServer()
	return
}
