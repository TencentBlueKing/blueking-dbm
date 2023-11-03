// Package myredis 该文件中保存一些公共函数
package myredis

import (
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"
)

// GetRedisLoccalConfFile 本地获取redis实例配置文件
func GetRedisLoccalConfFile(port int) (confFile string, err error) {
	dataDir := consts.GetRedisDataDir()
	instConf := filepath.Join(dataDir, "redis", strconv.Itoa(port), "instance.conf")
	redisConf := filepath.Join(dataDir, "redis", strconv.Itoa(port), "redis.conf")
	if util.FileExists(instConf) {
		return instConf, nil
	}
	if util.FileExists(redisConf) {
		return redisConf, nil
	}
	err = fmt.Errorf("[%s,%s] not exists", instConf, redisConf)
	mylog.Logger.Error(err.Error())
	return
}

// GetRedisPasswdFromConfFile (从配置文件中)获取本地redis实例密码
func GetRedisPasswdFromConfFile(port int) (password string, err error) {
	confFile, err := GetRedisLoccalConfFile(port)
	if err != nil {
		err = fmt.Errorf("get redis local config file failed,err:%v,port:%d", err, port)
		mylog.Logger.Error(err.Error())
		return
	}
	cmd01 := fmt.Sprintf(`grep -E '^requirepass' %s|awk '{print $2}'|head -1`, confFile)
	password, err = util.RunBashCmd(cmd01, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	password = strings.TrimPrefix(password, "\"")
	password = strings.TrimSuffix(password, "\"")
	return
}

// GetProxyPasswdFromConfFlie (从配置文件中)获取本地proxy实例密码
func GetProxyPasswdFromConfFlie(port int, role string) (password string, err error) {
	var grepCmd string
	if role == consts.MetaRoleTwemproxy {
		grepCmd = fmt.Sprintf(`grep -w "password" %s/twemproxy*/%d/nutcracker.%d.yml|grep -vE "#"|awk '{print $2}'`,
			consts.DataPath, port, port)
	} else if role == consts.MetaRolePredixy {
		grepCmd = fmt.Sprintf(`grep -iw "auth" %s/predixy/%d/predixy.conf|awk '{print $2}'`,
			consts.Data1Path, port)
	}
	password, err = util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	password = strings.TrimPrefix(password, "\"")
	password = strings.TrimSuffix(password, "\"")
	return
}

type connTestItem struct {
	IP       string
	Port     int
	Password string
	Err      error
}

func (c *connTestItem) addr() string {
	return c.IP + ":" + strconv.Itoa(c.Port)
}

// LocalRedisConnectTest 本地Redis连接性测试
// 从本地获取redis的password,并确认每个redis是否可链接
func LocalRedisConnectTest(ip string, ports []int) (err error) {
	if len(ports) == 0 {
		err = fmt.Errorf("LocalRedisConnectTest ports(%+v) cannot be empty", ports)
		return
	}
	l01 := make([]*connTestItem, 0, len(ports))
	var password string
	for _, port := range ports {
		password, err = GetRedisPasswdFromConfFile(port)
		if err != nil {
			return
		}
		l01 = append(l01, &connTestItem{
			IP:       ip,
			Port:     port,
			Password: password,
		})
	}
	// 并发测试
	wg := sync.WaitGroup{}
	for _, item := range l01 {
		test01 := item
		wg.Add(1)
		go func(test01 *connTestItem) {
			defer wg.Done()
			cli01, err := NewRedisClient(test01.addr(), test01.Password, 0, consts.TendisTypeRedisInstance)
			if err != nil {
				test01.Err = err
				return
			}
			cli01.Close()
		}(test01)
	}
	wg.Wait()

	for _, item := range l01 {
		test01 := item
		if test01.Err != nil {
			return test01.Err
		}
	}
	return
}
