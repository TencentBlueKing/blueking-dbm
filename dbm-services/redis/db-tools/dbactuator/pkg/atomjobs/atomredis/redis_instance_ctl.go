package atomredis

import (
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// portInUse 本机端口是否被占用. connection refused 仍是 inUse=false;
// 探测出错(超时/无路由/fd 耗尽)必须原样返回, 不得当成"没在跑".
func portInUse(ip string, port int) (bool, error) {
	return util.CheckPortIsInUse(ip, strconv.Itoa(port))
}

// knownRedisStorageClusterType 升级/刷新配置能处理的存储端 cluster_type.
func knownRedisStorageClusterType(dbType string) bool {
	return consts.IsRedisInstanceDbType(dbType) ||
		consts.IsTendisplusInstanceDbType(dbType) ||
		consts.IsTendisSSDInstanceDbType(dbType) ||
		consts.IsClusterDbType(dbType) ||
		consts.IsTwemproxyClusterType(dbType) ||
		consts.IsPredixyClusterType(dbType)
}

// writeRedisConfFile 先写临时文件再 rename, 避免截断后写一半.
// 权限沿用原 redis.conf, 避免升级把线上已有的 mode 改掉.
func writeRedisConfFile(confFile string, confData []byte) error {
	perm := os.FileMode(0644)
	if info, err := os.Stat(confFile); err == nil {
		perm = info.Mode().Perm()
	}
	tmpFile := confFile + ".tmp"
	if err := os.WriteFile(tmpFile, confData, perm); err != nil {
		return fmt.Errorf("write redis conf tmp(%s) failed,err:%v", tmpFile, err)
	}
	if err := os.Chmod(tmpFile, perm); err != nil {
		_ = os.Remove(tmpFile)
		return fmt.Errorf("chmod redis conf tmp(%s) to %v failed,err:%v", tmpFile, perm, err)
	}
	if err := os.Rename(tmpFile, confFile); err != nil {
		_ = os.Remove(tmpFile)
		return fmt.Errorf("rename redis conf tmp(%s) to %s failed,err:%v", tmpFile, confFile, err)
	}
	return chownMysqlOrErr(confFile)
}

// chownMysqlOrErr 把文件属主改成 mysql.
// 本机没有 mysql 用户, 或当前不是 root(改不了属主, 单测常见), 跳过.
func chownMysqlOrErr(path string) error {
	if _, err := user.Lookup(consts.MysqlAaccount); err != nil {
		return nil
	}
	if os.Geteuid() != 0 {
		return nil
	}
	if err := util.LocalDirChownMysql(path); err != nil {
		return fmt.Errorf("chown %s to %s failed,err:%v", path, consts.MysqlAaccount, err)
	}
	return nil
}

// readLocalRedisPkgBaseName 读 /usr/local/redis 软链当前指向的包名, 形如 redis-6.2.7.
// 配置渲染用它决定写 replicaof 还是 slaveof, 填错实例直接起不来.
func readLocalRedisPkgBaseName() (string, error) {
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	if _, err := os.Stat(redisSoftLink); err != nil && os.IsNotExist(err) {
		return "", fmt.Errorf("redis soft link(%s) not exist", redisSoftLink)
	}
	realLink, err := os.Readlink(redisSoftLink)
	if err != nil {
		return "", fmt.Errorf("readlink redis soft link(%s) failed,err:%+v", redisSoftLink, err)
	}
	return filepath.Base(realLink), nil
}

// countLocalRedisInstDirs 数本机 /data/redis 下的数字端口目录.
// tendisplus 的 blockcache 按实例数分摊: 任务只刷新部分端口时, 不能用 len(ports) 当 InstCount.
func countLocalRedisInstDirs() uint64 {
	dir := filepath.Join(consts.GetRedisDataDir(), "redis")
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0
	}
	var n uint64
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		if _, err := strconv.Atoi(entry.Name()); err == nil {
			n++
		}
	}
	return n
}

// connectLocalRedis 连本机一个 redis 实例, 密码从磁盘配置文件取.
func connectLocalRedis(addr string, port int, timeout time.Duration) (*myredis.RedisClient, error) {
	password, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return nil, err
	}
	return myredis.NewRedisClientWithRetry(addr, password, 0, consts.TendisTypeRedisInstance, timeout)
}

// stopRedisViaScript 调 stop-redis.sh 停实例, 再等到端口释放. 密码从磁盘配置文件取.
func stopRedisViaScript(ip string, port int, log *logger.Logger) error {
	password, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return err
	}
	return stopRedisViaScriptWithPassword(ip, port, password, log)
}

// stopRedisViaScriptWithPassword 用调用方给定的密码停实例.
//
// 改密码场景必须用它: 新密码此时已经写进配置文件, 而运行中的进程还只认旧密码,
// 再从文件读密码去 SHUTDOWN 会认证失败, 实例停不下来.
func stopRedisViaScriptWithPassword(ip string, port int, password string, log *logger.Logger) error {
	var err error
	stopScript := filepath.Join(consts.UsrLocal, "redis", "bin", "stop-redis.sh")
	if _, err = os.Stat(stopScript); err != nil && os.IsNotExist(err) {
		err = fmt.Errorf("%s not exist", stopScript)
		log.Error("%s", err)
		return err
	}
	log.Info("su %s -c \"%s\"",
		consts.MysqlAaccount, stopScript+" "+strconv.Itoa(port)+" xxxx")
	_, err = util.RunLocalCmdReplacePkey("su",
		[]string{consts.MysqlAaccount, "-c", fmt.Sprintf("%s %d %q", stopScript, port, password)}, password,
		"", nil, 10*time.Minute)
	if err != nil && !strings.Contains(err.Error(), "Warning: Using a password") {
		return err
	}
	maxRetryTimes := 5
	inUse := false
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		inUse, err = util.CheckPortIsInUse(ip, strconv.Itoa(port))
		if err != nil {
			log.Error("check %s:%d inUse failed,err:%v", ip, port, err)
			return err
		}
		if !inUse {
			break
		}
		time.Sleep(2 * time.Second)
	}
	if inUse {
		err = fmt.Errorf("stop redis instance(%s:%d) failed,port:%d still using", ip, port, port)
		log.Error("%s", err)
		return err
	}
	log.Info("stop redis instance(%s:%d) success", ip, port)
	return nil
}

// startRedisAndWaitRepl 调 start-redis.sh 拉起实例, 连上后钉死复制状态.
//
// 返回已连上的 client (失败时也可能非 nil: 进程起来了但同步还没好).
func startRedisAndWaitRepl(ip string, port int, expect replSnapshot, metaRole string,
	timeout time.Duration, log *logger.Logger) (*myredis.RedisClient, error) {
	startScript := filepath.Join(consts.UsrLocal, "redis", "bin", "start-redis.sh")
	log.Info("su %s -c \"%s\" 2>/dev/null",
		consts.MysqlAaccount, startScript+" "+strconv.Itoa(port))
	_, err := util.RunLocalCmd("su",
		[]string{consts.MysqlAaccount, "-c", startScript + " " + strconv.Itoa(port) + " 2>/dev/null"},
		"", nil, 10*time.Minute)
	if err != nil {
		return nil, err
	}
	addr := fmt.Sprintf("%s:%d", ip, port)
	cli, err := connectLocalRedis(addr, port, 10*time.Second)
	if err != nil && strings.Contains(err.Error(), "LOADING Redis is loading") {
		log.Warn("redis:%s conn warn,err:%v", addr, err)
		err = nil
	}
	if err != nil {
		return cli, err
	}
	if cli == nil {
		err = fmt.Errorf("redis(%s) started but got no client,cannot verify repl state after restart", addr)
		log.Error("%s", err)
		return nil, err
	}
	log.Info("start redis instance(%s:%d) success", ip, port)

	if err = settleReplication(cli, expect, metaRole, timeout, log); err != nil {
		return cli, err
	}
	return cli, nil
}

// backupCacheMasterBeforeStop cache 类型的 master 停机前先 bgsave.
// 这份 rdb 是 master 重启后唯一的数据来源, 存不下来就不该继续停实例.
func backupCacheMasterBeforeStop(role, addr string, cli *myredis.RedisClient, log *logger.Logger) error {
	if role != consts.MetaRoleRedisMaster {
		log.Info("redis instance(%s) is not master,skip backup", addr)
		return nil
	}
	if cli == nil {
		return fmt.Errorf("redis instance(%s) not connected,cannot bgsave before stop", addr)
	}
	dbType, err := cli.GetTendisType()
	if err != nil {
		return err
	}
	if dbType != consts.TendisTypeRedisInstance {
		log.Info("redis instance(%s) is not cache,skip backup", addr)
		return nil
	}
	log.Info("redis instance(%s) is cache,start bgsave", addr)
	if err = cli.BgSaveAndWaitForFinish(); err != nil {
		log.Error("redis instance(%s) bgsave failed,err:%v", addr, err)
		return err
	}
	return nil
}
