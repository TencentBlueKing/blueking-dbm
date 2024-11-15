// Package myredis 该文件中保存一些公共函数
package myredis

import (
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
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

func GetRedisPasswd(confFile string) (password string, err error) {
	cmd01 := fmt.Sprintf(`grep -E '^requirepass' %s|awk '{print $2}'|head -1`, confFile)
	password, err = util.RunBashCmd(cmd01, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	password = strings.TrimPrefix(password, "\"")
	password = strings.TrimSuffix(password, "\"")
	return
}

// GetRedisPasswdFromConfFile (从配置文件中)获取本地redis实例密码
func GetRedisPasswdFromConfFile(port int) (password string, err error) {
	// config rewrite的时候，重写的东西是写进redis.conf, 原来的实现方式如果存在instance.conf，就会获取到老的配置。
	// 默认先从redis.conf中获取密码
	dataDir := consts.GetRedisDataDir()
	redisConf := filepath.Join(dataDir, "redis", strconv.Itoa(port), "redis.conf")
	instConf := filepath.Join(dataDir, "redis", strconv.Itoa(port), "instance.conf")
	if util.FileExists(redisConf) {
		password, err = GetRedisPasswd(redisConf)
		if err == nil && password != "" {
			mylog.Logger.Info(fmt.Sprintf("get pwd success from redis.conf"))
			return
		}
	}
	// 尝试从instance.conf中获取密码
	if util.FileExists(instConf) {
		password, err = GetRedisPasswd(instConf)
		if err == nil && password != "" {
			mylog.Logger.Info(fmt.Sprintf("get pwd success from instance.conf"))
			return
		}
	}
	//	文件都不存在
	if !util.FileExists(instConf) && !util.FileExists(redisConf) {
		err = fmt.Errorf("[%s,%s] not exists", instConf, redisConf)
		mylog.Logger.Error(err.Error())
		return
	}
	// 有可能存在redis实例密码确实为空的情况。。
	mylog.Logger.Info(fmt.Sprintf("get pwd success. but pwd is empty"))
	return
}

// GetRedisPasswdFromConfFile (从配置文件中)获取本地redis实例密码
//func GetRedisPasswdFromConfFile(port int) (password string, err error) {
//	confFile, err := GetRedisLoccalConfFile(port)
//	if err != nil {
//		err = fmt.Errorf("get redis local config file failed,err:%v,port:%d", err, port)
//		mylog.Logger.Error(err.Error())
//		return
//	}
//	cmd01 := fmt.Sprintf(`grep -E '^requirepass' %s|awk '{print $2}'|head -1`, confFile)
//	password, err = util.RunBashCmd(cmd01, "", nil, 10*time.Second)
//	if err != nil {
//		return
//	}
//	password = strings.TrimPrefix(password, "\"")
//	password = strings.TrimSuffix(password, "\"")
//	return
//}

// GetTwemproxyLocalConfFile 本地获取twemproxy实例配置文件
func GetTwemproxyLocalConfFile(port int) (confFile string, err error) {
	psCmd := fmt.Sprintf(`
	ps aux|grep nutcracker|grep %d|grep yml|grep -v grep\
|head -1|grep --only-match -P '\-c\s+.*.yml'|awk '{print $2}'
	`, port)
	confFile, err = util.RunBashCmd(psCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	confFile = strings.TrimSpace(confFile)
	if confFile == "" {
		lsCmd := fmt.Sprintf(`ls %s/twemproxy*/%d/nutcracker.%d.yml|head -1`, consts.GetRedisDataDir(), port, port)
		confFile, err = util.RunBashCmd(lsCmd, "", nil, 10*time.Second)
		if err != nil {
			return
		}
	}
	return confFile, nil
}

// GetPredixyLocalConfFile 本地获取predixy实例配置文件
func GetPredixyLocalConfFile(port int) (confFile string, err error) {
	psCmd := fmt.Sprintf(`
ps aux|grep predixy|grep %d|grep predixy.conf|grep -v grep|head -1|awk '{print $NF}'
	`, port)
	confFile, err = util.RunBashCmd(psCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	confFile = strings.TrimSpace(confFile)
	if confFile == "" {
		lsCmd := fmt.Sprintf(`ls %s/predixy/%d/predixy.conf|head -1`, consts.GetRedisDataDir(), port)
		confFile, err = util.RunBashCmd(lsCmd, "", nil, 10*time.Second)
		if err != nil {
			return
		}
	}
	return confFile, nil
}

// GetProxyPasswdFromConfFlie (从配置文件中)获取本地proxy实例密码
func GetProxyPasswdFromConfFlie(port int, role string) (password string, err error) {
	var grepCmd, confFile string
	if role == consts.MetaRoleTwemproxy {
		confFile, err = GetTwemproxyLocalConfFile(port)
		if err != nil {
			return
		}
		grepCmd = fmt.Sprintf(`grep -w "password" %s|grep -vE "#\s*password" |awk '{print $NF}'`, confFile)
	} else if role == consts.MetaRolePredixy {
		confFile, err = GetPredixyLocalConfFile(port)
		if err != nil {
			return
		}
		grepCmd = fmt.Sprintf(`grep -Pi -B 2 "Mode\s*?write" %s|grep -iw "auth"|awk '{print $2}'`, confFile)
	}
	password, err = util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	password = strings.TrimPrefix(password, "\"")
	password = strings.TrimSuffix(password, "\"")
	password = strings.TrimPrefix(password, "'")
	password = strings.TrimSuffix(password, "'")
	return
}

// GetPredixyAdminPasswdFromConfFlie 从配置文件中获取本地predixy实例admin密码
func GetPredixyAdminPasswdFromConfFlie(port int) (adminPasswd string, err error) {
	var grepCmd, confFile string
	confFile, err = GetPredixyLocalConfFile(port)
	if err != nil {
		return
	}
	grepCmd = fmt.Sprintf(`grep -Pi -B 2 "Mode\s*?admin" %s|grep -iw "auth"|awk '{print $2}'`, confFile)
	adminPasswd, err = util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	if adminPasswd == "" {
		err = fmt.Errorf("get predixy admin password  empty record,confFile:%s", confFile)
		return
	}
	adminPasswd = strings.TrimPrefix(adminPasswd, "\"")
	adminPasswd = strings.TrimSuffix(adminPasswd, "\"")
	adminPasswd = strings.TrimPrefix(adminPasswd, "'")
	adminPasswd = strings.TrimSuffix(adminPasswd, "'")
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
func LocalRedisConnectTest(ip string, ports []int, password string) (err error) {
	if len(ports) == 0 {
		err = fmt.Errorf("LocalRedisConnectTest ports(%+v) cannot be empty", ports)
		return
	}
	l01 := make([]*connTestItem, 0, len(ports))
	for _, port := range ports {
		if password == "" {
			password, err = GetRedisPasswdFromConfFile(port)
			if err != nil {
				return
			}
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
			cli01, err := NewRedisClientWithTimeout(test01.addr(), test01.Password, 0,
				consts.TendisTypeRedisInstance, 10*time.Second)
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

// CheckMultiRedisConnected 检查多个redis是否可连接
func CheckMultiRedisConnected(addrs []string, password string) (err error) {
	l01 := make([]*connTestItem, 0, len(addrs))
	for _, addr := range addrs {
		ip, port, err := util.AddrToIpPort(addr)
		if err != nil {
			return err
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
			cli01, err := NewRedisClientWithTimeout(test01.addr(), test01.Password, 0,
				consts.TendisTypeRedisInstance, 10*time.Second)
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
