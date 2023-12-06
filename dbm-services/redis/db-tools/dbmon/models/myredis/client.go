package myredis

import (
	"context"
	"fmt"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"

	"github.com/go-redis/redis/v8"
)

// RedisClient redis连接信息
type RedisClient struct {
	Addr             string                      `json:"addr"`
	Password         string                      `json:"password"`
	DB               int                         `json:"db"`
	MaxRetryTime     int                         `json:"maxRetryTimes"`
	DbType           string                      `json:"dbType"` // db类型
	InstanceClient   *redis.Client               `json:"-"`
	ClusterClient    *redis.ClusterClient        `json:"-"`
	addrMapToNodes   map[string]*ClusterNodeData `json:"-"`
	nodeIDMapToNodes map[string]*ClusterNodeData `json:"-"`
	nodesMu          *sync.Mutex                 // 写入/读取 AddrMapToNodes NodeIDMapToNodes 时加锁
}

// NewRedisClient 建redis客户端
func NewRedisClient(addr, passwd string, db int, dbType string) (conn *RedisClient, err error) {
	conn = &RedisClient{
		Addr:         addr,
		Password:     passwd,
		DB:           db,
		MaxRetryTime: 60, // 默认重试60次
		DbType:       dbType,
		nodesMu:      &sync.Mutex{},
	}
	err = conn.newConn()
	if err != nil {
		return nil, err
	}
	return
}

// NewRedisClientWithTimeout 建redis客户端,可指定超时时间
func NewRedisClientWithTimeout(addr, passwd string, db int, dbType string, timeout time.Duration) (
	conn *RedisClient, err error) {
	conn = &RedisClient{
		Addr:         addr,
		Password:     passwd,
		DB:           db,
		MaxRetryTime: int(timeout.Seconds()),
		DbType:       dbType,
		nodesMu:      &sync.Mutex{},
	}
	err = conn.newConn()
	if err != nil {
		return nil, err
	}
	return
}

func (db *RedisClient) newConn() (err error) {
	// 执行命令失败重连,确保重连后,databases正确
	var redisConnHook = func(ctx context.Context, cn *redis.Conn) error {
		pipe01 := cn.Pipeline()
		_, err := pipe01.Select(context.TODO(), db.DB).Result()
		if err != nil {
			err = fmt.Errorf("newConnct pipeline change db fail,err:%v", err)
			mylog.Logger.Error(err.Error())
			return err
		}
		_, err = pipe01.Exec(context.TODO())
		if err != nil {
			err = fmt.Errorf("newConnct pipeline.exec db fail,err:%v", err)
			mylog.Logger.Error(err.Error())
			return err
		}
		return nil
	}
	redisOpt := &redis.Options{
		Addr:            db.Addr,
		DB:              db.DB,
		DialTimeout:     1 * time.Minute,
		ReadTimeout:     1 * time.Minute,
		MaxConnAge:      24 * time.Hour,
		MaxRetries:      db.MaxRetryTime, // 失败自动重试,重试次数
		MinRetryBackoff: 1 * time.Second, // 重试间隔
		MaxRetryBackoff: 1 * time.Second,
		PoolSize:        2,
		OnConnect:       redisConnHook,
	}
	clusterOpt := &redis.ClusterOptions{
		Addrs:           []string{db.Addr},
		DialTimeout:     1 * time.Minute,
		ReadTimeout:     1 * time.Minute,
		MaxConnAge:      24 * time.Hour,
		MaxRetries:      db.MaxRetryTime, // 失败自动重试,重试次数
		MinRetryBackoff: 1 * time.Second, // 重试间隔
		MaxRetryBackoff: 1 * time.Second,
		PoolSize:        2,
		OnConnect:       redisConnHook,
	}
	if db.Password != "" {
		redisOpt.Password = db.Password
		clusterOpt.Password = db.Password
	}
	if db.DbType == consts.TendisTypeRedisCluster {
		db.ClusterClient = redis.NewClusterClient(clusterOpt)
		_, err = db.ClusterClient.Ping(context.TODO()).Result()
	} else {
		db.InstanceClient = redis.NewClient(redisOpt)
		_, err = db.InstanceClient.Ping(context.TODO()).Result()
	}
	if err != nil {
		errStr := fmt.Sprintf("redis new conn fail,sleep 10s then retry.err:%v,addr:%s", err, db.Addr)
		mylog.Logger.Error(errStr)
		return fmt.Errorf("redis new conn fail,err:%v addr:%s", err, db.Addr)
	}
	return
}

// RedisClusterConfigSetOnlyMasters run 'config set ' on all redis cluster running masters
func (db *RedisClient) RedisClusterConfigSetOnlyMasters(confName string, val string) (rets []string, err error) {
	nodes, err := db.GetClusterNodes()
	if err != nil {
		return
	}
	confSetFunc := func(node001 *ClusterNodeData, confName, val string) (ret string, err error) {
		cli01, err := NewRedisClient(node001.Addr, db.Password, 0, consts.TendisTypeRedisInstance)
		if err != nil {
			return
		}
		defer cli01.Close()
		return cli01.ConfigSet(confName, val)
	}
	for _, nodeItem := range nodes {
		node01 := nodeItem
		if IsRunningMaster(node01) {
			ret, err := confSetFunc(node01, confName, val)
			if err != nil {
				return rets, err
			}
			rets = append(rets, ret)
		}
	}
	return
}

// DoCommand Do command(auto switch db)
func (db *RedisClient) DoCommand(cmdArgv []string, dbnum int) (interface{}, error) {
	err := db.SelectDB(dbnum)
	if err != nil {
		return nil, err
	}
	var ret interface{}
	dstCmds := []interface{}{}
	for _, cmd01 := range cmdArgv {
		dstCmds = append(dstCmds, cmd01)
	}
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.Do(context.TODO(), dstCmds...).Result()
	} else {
		ret, err = db.InstanceClient.Do(context.TODO(), dstCmds...).Result()
	}
	if err != nil && err != redis.Nil {
		mylog.Logger.Error(fmt.Sprintf("Redis  DoCommand fail,err:%v,command:%+v,addr:%s", err, cmdArgv, db.Addr))
		return nil, err
	} else if err != nil && err == redis.Nil {
		return nil, err
	}
	return ret, nil
}

// SelectDB db
func (db *RedisClient) SelectDB(dbNum int) (err error) {
	if db.DB == dbNum {
		return nil
	}
	if db.DbType != consts.TendisTypeRedisInstance {
		err = fmt.Errorf("redis:%s dbtype:%s cannot change db", db.Addr, db.DbType)
		mylog.Logger.Error(err.Error())
		return
	}
	if db.InstanceClient == nil {
		err = fmt.Errorf("redis:%s not connect", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	pipe01 := db.InstanceClient.Pipeline()
	_, err = pipe01.Select(context.TODO(), dbNum).Result()
	if err != nil && err != redis.Nil {
		err = fmt.Errorf("redis:%s selectdb fail,err:%v", db.Addr, err)
		mylog.Logger.Error(err.Error())
		return
	}
	_, err = pipe01.Exec(context.TODO())
	if err != nil && err != redis.Nil {
		err = fmt.Errorf("redis:%s selectdb fail,err:%v", db.Addr, err)
		mylog.Logger.Error(err.Error())
		return
	}
	db.DB = dbNum
	return nil
}

// SelectDB1WhenClusterDisabled 当cluster-enabled=no时,执行select 1,否则依然连db 0
func (db *RedisClient) SelectDB1WhenClusterDisabled() (err error) {
	var clusterEnabled bool
	clusterEnabled, err = db.IsClusterEnabled()
	if err != nil {
		return
	}
	if !clusterEnabled {
		return db.SelectDB(1)
	}
	return nil
}

// ReadOnlyOnClusterSlave 如果是cluster slave,则执行readonly命令
func (db *RedisClient) ReadOnlyOnClusterSlave() (err error) {
	// 执行 bgsave 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("'readonly' command redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return err
	}
	var clusterEnabled bool
	var role string
	clusterEnabled, err = db.IsClusterEnabled()
	if err != nil {
		return
	}
	role, err = db.GetRole()
	if err != nil {
		return
	}
	if clusterEnabled && role == consts.RedisSlaveRole {
		err = db.InstanceClient.ReadOnly(context.TODO()).Err()
		if err != nil {
			err = fmt.Errorf("'readonly' fail,err:%v,addr:%s", err, db.Addr)
			mylog.Logger.Error(err.Error())
			return
		}
	}
	return nil
}

// DelForce 删除key
func (db *RedisClient) DelForce(keyname string) (ret int64, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.Del(context.TODO(), keyname).Result()
	} else {
		ret, err = db.InstanceClient.Del(context.TODO(), keyname).Result()
	}
	if err != nil && err != redis.Nil {
		mylog.Logger.Error(fmt.Sprintf("Redis 'del %s' command fail,err:%v,addr:%s", keyname, err, db.Addr))
		return 0, err
	}
	return
}

// KeyType key类型
func (db *RedisClient) KeyType(keyname string) (keyType string, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		keyType, err = db.ClusterClient.Type(context.TODO(), keyname).Result()
	} else {
		keyType, err = db.InstanceClient.Type(context.TODO(), keyname).Result()
	}
	if err != nil && err != redis.Nil {
		mylog.Logger.Error(fmt.Sprintf("Redis 'type %s' command fail,err:%v,addr:%s", keyname, err, db.Addr))
		return
	}
	return
}

// DbSize 'dbsize'
func (db *RedisClient) DbSize() (ret int64, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.DBSize(context.TODO()).Result()
	} else {
		ret, err = db.InstanceClient.DBSize(context.TODO()).Result()
	}
	if err != nil && err != redis.Nil {
		mylog.Logger.Error(fmt.Sprintf("Redis 'dbsize' command fail,err:%v,addr:%s", err, db.Addr))
		return
	}
	return ret, nil
}

// Info 执行info [section]命令并将返回结果保存在map中
func (db *RedisClient) Info(section string) (infoRet map[string]string, err error) {
	infoRet = make(map[string]string)
	var str01 string
	ctx := context.TODO()
	if section == "" && db.DbType == consts.TendisTypeRedisCluster {
		str01, err = db.ClusterClient.Info(ctx).Result()
	} else if section != "" && db.DbType == consts.TendisTypeRedisCluster {
		str01, err = db.ClusterClient.Info(ctx, section).Result()
	} else if section == "" && db.DbType != consts.TendisTypeRedisCluster {
		str01, err = db.InstanceClient.Info(ctx).Result()
	} else if section != "" && db.DbType != consts.TendisTypeRedisCluster {
		str01, err = db.InstanceClient.Info(ctx, section).Result()
	}
	if err != nil {
		err = fmt.Errorf("redis:%s 'info %s' fail,err:%v", db.Addr, section, err)
		mylog.Logger.Error(err.Error())
		return
	}
	infoList := strings.Split(str01, "\n")
	for _, infoItem := range infoList {
		infoItem = strings.TrimSpace(infoItem)
		if strings.HasPrefix(infoItem, "#") {
			continue
		}
		if len(infoItem) == 0 {
			continue
		}
		list01 := strings.SplitN(infoItem, ":", 2)
		if len(list01) < 2 {
			continue
		}
		list01[0] = strings.TrimSpace(list01[0])
		list01[1] = strings.TrimSpace(list01[1])
		infoRet[list01[0]] = list01[1]
	}
	return
}

// GetTendisType 获取redis类型,返回RedisInstance or TendisplusInstance or TendisSSDInsance
func (db *RedisClient) GetTendisType() (dbType string, err error) {
	var infoRet map[string]string
	infoRet, err = db.Info("server")
	if err != nil {
		return
	}
	version := infoRet["redis_version"]
	if strings.Contains(version, "-rocksdb-") {
		dbType = consts.TendisTypeTendisplusInsance
	} else if strings.Contains(version, "-TRedis-") {
		dbType = consts.TendisTypeTendisSSDInsance
	} else {
		dbType = consts.TendisTypeRedisInstance
	}
	return
}

// GetDir config get dir 获取数据路径
func (db *RedisClient) GetDir() (dir string, err error) {
	var ok bool
	confRet, err := db.ConfigGet("dir")
	if err != nil {
		return
	}
	dir, ok = confRet["dir"]
	if !ok {
		err = fmt.Errorf("config get dir result not include dir?,result:%+v,addr:%s", confRet, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	dir = strings.TrimPrefix(dir, `"`)
	dir = strings.TrimSuffix(dir, `"`)
	return
}

// GetDumpDir config get dumpdir 获取dumpdir(保存binlog的路径)
func (db *RedisClient) GetDumpDir() (dir string, err error) {
	var ok bool
	confRet, err := db.ConfigGet("dumpdir")
	if err != nil {
		return
	}
	dir, ok = confRet["dumpdir"]
	if !ok {
		err = fmt.Errorf("config get dumpdir result not include dumpdir?,result:%+v,addr:%s", confRet, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	dir = strings.TrimPrefix(dir, `"`)
	dir = strings.TrimSuffix(dir, `"`)
	return
}

// GetKvstoreCount config get kvstorecount 获取kvstore 数量
func (db *RedisClient) GetKvstoreCount() (kvstorecount int, err error) {
	var ok bool
	var kvstorecountStr string
	confRet, err := db.ConfigGet("kvstorecount")
	if err != nil {
		return 0, err
	}
	kvstorecountStr, ok = confRet["kvstorecount"]
	if !ok {
		err = fmt.Errorf("config get kvstorecount result not include dir?,result:%+v,addr:%s", confRet, db.Addr)
		mylog.Logger.Error(err.Error())
		return 0, err
	}

	kvstorecountStr = strings.TrimPrefix(kvstorecountStr, `"`)
	kvstorecountStr = strings.TrimSuffix(kvstorecountStr, `"`)
	kvstorecount, err = strconv.Atoi(kvstorecountStr)
	if err != nil {
		err = fmt.Errorf("config get kvstorecount result '%s' to int fail,err:%v,addr:%s", kvstorecountStr, err, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// GetRole info replication中获取角色
func (db *RedisClient) GetRole() (role string, err error) {
	var infoRet map[string]string
	infoRet, err = db.Info("replication")
	if err != nil {
		return
	}
	role = infoRet["role"]
	return
}

// GetMasterData info replication中master信息
func (db *RedisClient) GetMasterData() (masterHost, masterPort, linkStatus, selfRole string,
	masterLastIOSec int64, err error) {
	var infoRet map[string]string
	infoRet, err = db.Info("replication")
	if err != nil {
		return
	}
	selfRole = infoRet["role"]
	if selfRole != consts.RedisSlaveRole {
		return
	}
	masterHost = infoRet["master_host"]
	masterPort = infoRet["master_port"]
	linkStatus = infoRet["master_link_status"]
	masterLastIOSec, err = strconv.ParseInt(infoRet["master_last_io_seconds_ago"], 10, 64)
	if err != nil {
		err = fmt.Errorf("redis:%s 'info replication' master_last_io_seconds_ago(%s) to int64 fail,err:%v",
			db.Addr, infoRet["master_last_io_seconds_ago"], err)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// Bgsave 执行bgsave命令
func (db *RedisClient) Bgsave() (ret string, err error) {
	// 执行 bgsave 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("bgsave command redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	str01, err := db.InstanceClient.BgSave(context.TODO()).Result()
	if err != nil {
		err = fmt.Errorf("redis:%s 'bgsave' fail,err:%v", db.Addr, err)
		mylog.Logger.Error(err.Error())
		return str01, err
	}
	return str01, nil
}

// IsBgsaveInProgress ..
func (db *RedisClient) IsBgsaveInProgress() (ret bool, err error) {
	persisInfo, err := db.Info("Persistence")
	if err != nil {
		return false, err
	}
	inProgress := persisInfo["rdb_bgsave_in_progress"]
	if inProgress == "1" {
		return true, nil
	}
	return false, nil
}

// BgRewriteAOF 执行bgrewriteaof命令
func (db *RedisClient) BgRewriteAOF() (ret string, err error) {
	// 执行 bgrewriteaof 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("bgrewriteaof command redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	str01, err := db.InstanceClient.BgRewriteAOF(context.TODO()).Result()
	if err != nil {
		err = fmt.Errorf("redis:%s 'bgrewriteaof' fail,err:%v", db.Addr, err)
		mylog.Logger.Error(err.Error())
		return str01, err
	}
	return str01, nil
}

// IsAofRewriteInProgress ..
func (db *RedisClient) IsAofRewriteInProgress() (ret bool, err error) {
	persisInfo, err := db.Info("Persistence")
	if err != nil {
		return false, err
	}
	inProgress := persisInfo["aof_rewrite_in_progress"]
	if inProgress == "1" {
		return true, nil
	}
	return false, nil
}

// BgRewriteAOFAndWaitForDone 执行bgrewriteaof命令并等待结束
func (db *RedisClient) BgRewriteAOFAndWaitForDone() (err error) {
	_, err = db.BgRewriteAOF()
	if err != nil {
		return err
	}
	count := 0 // 每分钟输出一次日志
	var msg string
	var inProgress bool
	for {
		time.Sleep(5 * time.Second)
		inProgress, err = db.IsAofRewriteInProgress()
		if err != nil {
			return err
		}
		if inProgress == false {
			msg = fmt.Sprintf("redis:%s bgrewriteaof success", db.Addr)
			mylog.Logger.Info(msg)
			return nil
		}
		count++
		if (count % 12) == 0 {
			msg = fmt.Sprintf("redis:%s bgrewriteaof is still running ...", db.Addr)
			mylog.Logger.Info(msg)
		}
	}
}

// BgSaveAndWaitForFinish 执行bgsave命令并等待结束
func (db *RedisClient) BgSaveAndWaitForFinish() (err error) {
	var inProgress bool
	if inProgress, err = db.IsBgsaveInProgress(); err != nil {
		return err
	}

	if !inProgress {
		if _, err = db.Bgsave(); err != nil {
			return err
		}
	}
	count := 0 // 每分钟输出一次日志
	var msg string
	for {
		time.Sleep(5 * time.Second)
		inProgress, err = db.IsBgsaveInProgress()
		if err != nil {
			return err
		}
		if !inProgress {
			msg = fmt.Sprintf("redis:%s bgsave success", db.Addr)
			mylog.Logger.Info(msg)
			return nil
		}
		count++
		if (count % 12) == 0 {
			msg = fmt.Sprintf("redis:%s bgsave is still running ...", db.Addr)
			mylog.Logger.Info(msg)
		}
	}
}

// TendisplusBackup backup
func (db *RedisClient) TendisplusBackup(targetDir string) (ret string, err error) {
	// 执行 backup 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("backup command redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	cmd := []interface{}{"backup", targetDir}
	res, err := db.InstanceClient.Do(context.TODO(), cmd...).Result()
	if err != nil {
		err = fmt.Errorf("%+v fail,err:%v,addr:%s", cmd, err, db.Addr)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	ret = res.(string)
	return ret, nil
}

// IsTendisplusBackupInProgress ..
func (db *RedisClient) IsTendisplusBackupInProgress() (ret bool, err error) {
	bakInfo, err := db.Info("backup")
	if err != nil {
		return false, err
	}
	inProgress := bakInfo["current-backup-running"]
	if inProgress == "yes" {
		return true, nil
	}
	return false, nil
}

// TendisplusBackupAndWaitForDone 执行backup命令并等待结束
func (db *RedisClient) TendisplusBackupAndWaitForDone(targetDir string) (err error) {
	_, err = db.TendisplusBackup(targetDir)
	if err != nil {
		return err
	}
	count := 0 // 每分钟输出一次日志
	var msg string
	var inProgress bool
	for {
		time.Sleep(5 * time.Second)
		inProgress, err = db.IsTendisplusBackupInProgress()
		if err != nil {
			return err
		}
		if inProgress == false {
			msg = fmt.Sprintf("tendisplus:%s backup success", db.Addr)
			mylog.Logger.Info(msg)
			return nil
		}
		count++
		if (count % 12) == 0 {
			msg = fmt.Sprintf("tendisplus:%s backup is still running ...", db.Addr)
			mylog.Logger.Info(msg)
		}
	}
}

// IsTendisSSDBackupInProgress tendisSSD是否在备份中
func (db *RedisClient) IsTendisSSDBackupInProgress() (ret bool, err error) {
	bakInfo, err := db.Info("Backups")
	if err != nil {
		return false, err
	}
	inProgress := bakInfo["current-backup-running"]
	if inProgress == "yes" {
		return true, nil
	}
	return false, nil
}

// WaitForBackupFinish 无论是redis or tendisplus等待其backup结束
func (db *RedisClient) WaitForBackupFinish() (err error) {
	count := 0 // 每分钟输出一次日志
	var msg string
	var aofRewriteRunning bool
	var bgsaveRunning bool
	var plusBakRunning bool
	var ssdBakRunning bool
	var tendisType string
	tendisType, err = db.GetTendisType()
	if err != nil {
		return
	}
	for {
		switch tendisType {
		case consts.TendisTypeRedisInstance:
			aofRewriteRunning, _ = db.IsAofRewriteInProgress()
			bgsaveRunning, err = db.IsAofRewriteInProgress()
			msg = fmt.Sprintf("redis:%s bgrewriteaof or bgsave is still running ...", db.Addr)
		case consts.TendisTypeTendisplusInsance:
			plusBakRunning, err = db.IsTendisplusBackupInProgress()
			msg = fmt.Sprintf("tendisplus:%s backup is still running ...", db.Addr)
		case consts.TendisTypeTendisSSDInsance:
			ssdBakRunning, err = db.IsTendisSSDBackupInProgress()
			msg = fmt.Sprintf("tendisSSD:%s backup is still running ...", db.Addr)
		}
		if err != nil {
			return
		}
		if aofRewriteRunning || bgsaveRunning || plusBakRunning || ssdBakRunning {
			count++
			if (count % 12) == 0 {
				mylog.Logger.Info(msg)
			}
			time.Sleep(5 * time.Second)
			continue
		}
		msg = fmt.Sprintf("redis:%s rdb_bgsave_in_progress=0,aof_rewrite_in_progress=0,current-backup-running=no", db.Addr)
		mylog.Logger.Info(msg)
		break
	}
	return nil
}

// TendisSSDBackup pipeline执行 binlogsize + bakcup $dir命令,并返回结果
func (db *RedisClient) TendisSSDBackup(targetDir string) (
	binlogsizeRet TendisSSDBinlogSize, backupCmdRet string, err error,
) {
	// 执行 backup 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("backup command redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	pipe01 := db.InstanceClient.Pipeline()
	cmd := []interface{}{"binlogsize"}
	binlogRetInter := pipe01.Do(context.TODO(), cmd...)
	cmd = []interface{}{"backup", targetDir}
	backupRetInter := pipe01.Do(context.TODO(), cmd...)

	_, err = pipe01.Exec(context.TODO())
	if err != nil && err != redis.Nil {
		err = fmt.Errorf("redis(%s) pipeline.Exec fail,err:%v,cmds:['binlogsize','backup %s']", db.Addr, err, targetDir)
		mylog.Logger.Error(err.Error())
		return
	}
	binlogsizeRet, err = db.parseBinlogSizeCmdRet(binlogRetInter.Val())
	if err != nil {
		return
	}

	backupCmdRet = backupRetInter.Val().(string)
	return
}

// TendisSSDBackupAndWaitForDone 执行backup命令并等待结束
func (db *RedisClient) TendisSSDBackupAndWaitForDone(targetDir string) (
	binlogsizeRet TendisSSDBinlogSize, backupCmdRet string, err error,
) {
	binlogsizeRet, backupCmdRet, err = db.TendisSSDBackup(targetDir)
	if err != nil {
		return
	}
	count := 0 // 每分钟输出一次日志
	var msg string
	var inProgress bool
	for {
		time.Sleep(5 * time.Second)
		inProgress, err = db.IsTendisSSDBackupInProgress()
		if err != nil {
			return
		}
		if inProgress == false {
			msg = fmt.Sprintf("tendisSSD:%s backup success", db.Addr)
			mylog.Logger.Info(msg)
			return
		}
		count++
		if (count % 12) == 0 {
			msg = fmt.Sprintf("tendisSSD:%s backup is still running ...", db.Addr)
			mylog.Logger.Info(msg)
		}
	}
}

// Scan 命令
func (db *RedisClient) Scan(match string, cursor uint64, count int64) (keys []string, retcursor uint64, err error) {
	// 执行scan命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("Scan redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	keys, retcursor, err = db.InstanceClient.Scan(context.TODO(), cursor, match, count).Result()
	if err != nil && err != redis.Nil {
		err = fmt.Errorf("redis scan fail,err:%v,match:%s,cursor:%d,count:%d,addr:%s", err, match, cursor, count, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	return keys, retcursor, nil
}

// Sscan 'sscan'
func (db *RedisClient) Sscan(keyname string, cursor uint64, match string, count int64) (fields []string,
	retCursor uint64, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		fields, retCursor, err = db.ClusterClient.SScan(context.TODO(), keyname, cursor, match, count).Result()
	} else {
		fields, retCursor, err = db.InstanceClient.SScan(context.TODO(), keyname, cursor, match, count).Result()
	}
	if err != nil && err != redis.Nil {
		mylog.Logger.Error(fmt.Sprintf("Redis 'sscan %s %d match %s count %d' command fail,err:%v,addr:%s",
			keyname, cursor, match, count, err, db.Addr))
		return fields, 0, err
	}
	return fields, retCursor, nil
}

// GetClusterNodes 获取cluster nodes命令结果并解析
func (db *RedisClient) GetClusterNodes() (clusterNodes []*ClusterNodeData, err error) {
	db.nodesMu.Lock()
	defer db.nodesMu.Unlock()
	var nodesStr01 string
	if db.DbType == consts.TendisTypeRedisCluster {
		nodesStr01, err = db.ClusterClient.ClusterNodes(context.TODO()).Result()
	} else {
		nodesStr01, err = db.InstanceClient.ClusterNodes(context.TODO()).Result()
	}
	if err != nil {
		err = fmt.Errorf("cluster nodes fail,err:%v,addr:%s", err, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	clusterNodes, err = DecodeClusterNodes(nodesStr01)
	if err != nil {
		return
	}
	db.addrMapToNodes = make(map[string]*ClusterNodeData)
	db.nodeIDMapToNodes = make(map[string]*ClusterNodeData)
	for _, tmpItem := range clusterNodes {
		infoItem := tmpItem
		db.addrMapToNodes[infoItem.Addr] = infoItem
		db.nodeIDMapToNodes[infoItem.NodeID] = infoItem
	}
	return
}

// GetAddrMapToNodes 返回addr=>clusterNode 映射
func (db *RedisClient) GetAddrMapToNodes() (ret map[string]*ClusterNodeData, err error) {
	_, err = db.GetClusterNodes()
	if err != nil {
		return
	}
	ret = db.addrMapToNodes
	return
}

// GetNodeIDMapToNodes 返回nodeId=>clusterNode 映射
func (db *RedisClient) GetNodeIDMapToNodes() (ret map[string]*ClusterNodeData, err error) {
	_, err = db.GetClusterNodes()
	if err != nil {
		return
	}
	ret = db.nodeIDMapToNodes
	return
}

// ConfigSet tendis执行confxx set
func (db *RedisClient) ConfigSet(confName string, val string) (string, error) {
	var err error
	var ok bool
	// 执行 config set 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("ConfigSet redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	// 先执行config set,如果报错则执行 confxx set
	data, err := db.InstanceClient.ConfigSet(context.TODO(), confName, val).Result()
	if err != nil && strings.Contains(err.Error(), "ERR unknown command") {
		cmd := []interface{}{"confxx", "set", confName, val}
		confRet, err := db.InstanceClient.Do(context.TODO(), cmd...).Result()
		if err != nil {
			err = fmt.Errorf("%+v fail,err:%v,addr:%s", cmd, err, db.Addr)
			mylog.Logger.Error(err.Error())
			return "", err
		}
		data, ok = confRet.(string)
		if ok == false {
			err = fmt.Errorf(`confxx set result not interface{},cmd:%v,cmdRet:%v,nodeAddr:%s`,
				cmd, confRet, db.Addr)
			mylog.Logger.Error(err.Error())
			return "", err
		}
	} else if err != nil {
		err = fmt.Errorf("redis config set %s %s fail,err:%v,addr:%s", confName, val, err, db.Addr)
		mylog.Logger.Error(err.Error())
		return data, err
	}
	return data, nil
}

// ConfigGet tendis执行config get or confxx get
func (db *RedisClient) ConfigGet(confName string) (ret map[string]string, err error) {
	var confInfos []interface{}
	var ok bool
	ret = map[string]string{}

	// 先执行config get,如果报错则执行 confxx get
	if db.DbType == consts.TendisTypeRedisCluster {
		confInfos, err = db.ClusterClient.ConfigGet(context.TODO(), confName).Result()
	} else {
		confInfos, err = db.InstanceClient.ConfigGet(context.TODO(), confName).Result()
	}
	if err != nil && strings.Contains(err.Error(), "ERR unknown command") {
		cmd := []interface{}{"confxx", "get", confName}
		var confRet interface{}
		if db.DbType == consts.TendisTypeRedisCluster {
			confRet, err = db.ClusterClient.Do(context.TODO(), cmd...).Result()
		} else {
			confRet, err = db.InstanceClient.Do(context.TODO(), cmd...).Result()
		}
		if err != nil {
			err = fmt.Errorf("cmd:%+v fail,err:%v,addr:%s", cmd, err, db.Addr)
			mylog.Logger.Error(err.Error())
			return ret, err
		}
		confInfos, ok = confRet.([]interface{})
		if ok == false {
			err = fmt.Errorf("cmd:%v result not []interface{},cmdRet:%v,nodeAddr:%s", cmd, confRet, db.Addr)
			mylog.Logger.Error(err.Error())
			return ret, err
		}
	} else if err != nil {
		err = fmt.Errorf(" cmd:config get %q failed,err:%v", confName, err)
		mylog.Logger.Error(err.Error())
		return ret, err
	}

	var k01, v01 string
	for idx, confItem := range confInfos {
		conf01 := confItem.(string)
		if idx%2 == 0 {
			k01 = conf01
			continue
		}
		v01 = conf01
		ret[k01] = v01
	}
	return ret, nil
}

// ConfigRewrite tendis执行confxx rewrite
func (db *RedisClient) ConfigRewrite() (string, error) {
	var err error
	var data string
	var ok bool
	// 执行 config rewrite 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("ConfigRewrite redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	data, err = db.InstanceClient.ConfigRewrite(context.TODO()).Result()
	if err != nil && strings.Contains(err.Error(), "ERR unknown command") {
		cmd := []interface{}{"confxx", "rewrite"}
		confRet, err := db.InstanceClient.Do(context.TODO(), cmd...).Result()
		if err != nil {
			err = fmt.Errorf("%+v fail,err:%v,addr:%s", cmd, err, db.Addr)
			mylog.Logger.Error(err.Error())
			return "", err
		}
		data, ok = confRet.(string)
		if ok == false {
			err = fmt.Errorf(
				`confxx rewrite result not string,cmd:%v,cmdRet:%v,addr:%s`,
				cmd, confRet, db.Addr)
			mylog.Logger.Error(err.Error())
			return "", err
		}
	} else if err != nil {
		err = fmt.Errorf("redis config rewrite fail,err:%v,addr:%s", err, db.Addr)
		mylog.Logger.Error(err.Error())
		return "", err
	}
	return data, nil
}

// SlaveOf 'slaveof' command
func (db *RedisClient) SlaveOf(masterIP, masterPort string) (ret string, err error) {
	// 执行slaveof 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("SlaveOf redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	ret, err = db.InstanceClient.SlaveOf(context.TODO(), masterIP, masterPort).Result()
	if err != nil {
		err = fmt.Errorf("'slaveof %s %s' failed,err:%v,addr:%s", masterIP, masterPort, err, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// IsClusterEnabled 'cluster-enabled' 是否启动
func (db *RedisClient) IsClusterEnabled() (clusterEnabled bool, err error) {
	confData, err := db.ConfigGet("cluster-enabled")
	if err != nil {
		return
	}
	val, ok := confData["cluster-enabled"]
	if ok && (strings.ToLower(val) == "yes" ||
		strings.ToLower(val) == "on" ||
		strings.ToLower(val) == "1") {
		clusterEnabled = true
	}
	return
}

// ClusterMeet  'cluster meet' command
func (db *RedisClient) ClusterMeet(ip, port string) (ret string, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.ClusterMeet(context.TODO(), ip, port).Result()
	} else {
		ret, err = db.InstanceClient.ClusterMeet(context.TODO(), ip, port).Result()
	}
	if err != nil {
		err = fmt.Errorf("redis(%s) 'cluster meet %s %s' failed,err:%v", db.Addr, ip, port, err)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// ClusterAddSlots 添加slots, 'cluster addslots 'command
func (db *RedisClient) ClusterAddSlots(slots []int) (ret string, err error) {
	// 执行 cluster addslots 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("ClusterAddSlots redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	ret, err = db.InstanceClient.ClusterAddSlots(context.TODO(), slots...).Result()
	if err != nil {
		slotStr := ConvertSlotToStr(slots)
		err = fmt.Errorf("redis(%s) 'cluster addslots %s' failed,err:%v", db.Addr, slotStr, err)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// ClusterReplicate 'cluster replicate'
func (db *RedisClient) ClusterReplicate(masterID string) (ret string, err error) {
	// 执行cluster replicate 命令只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("ClusterReplicate redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	ret, err = db.InstanceClient.ClusterReplicate(context.TODO(), masterID).Result()
	if err != nil {
		err = fmt.Errorf("'cluster replicate %s' failed,err:%v,addr:%s", masterID, err, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// GetMyself 获取myself的节点信息
func (db *RedisClient) GetMyself() (ret *ClusterNodeData, err error) {
	// cluster nodes中找到 myself 节点,只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("GetMyself redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return nil, err
	}
	addrMap, err := db.GetAddrMapToNodes()
	if err != nil {
		return ret, err
	}
	for _, info01 := range addrMap {
		infoItem := info01
		if infoItem.IsMyself == true {
			ret = infoItem
			break
		}
	}
	return ret, nil
}

// TendisplusDataSize tendisplus数据量大小,'info Dataset' rocksdb.total-sst-files-size,单位byte
func (db *RedisClient) TendisplusDataSize() (dataSize uint64, err error) {
	// 命令'info Dataset',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("TendisplusDataSize redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	var infoRet map[string]string
	infoRet, err = db.Info("Dataset")
	if err != nil {
		return
	}
	sizeStr := infoRet["rocksdb.total-sst-files-size"]
	dataSize, err = strconv.ParseUint(sizeStr, 10, 64)
	if err != nil {
		err = fmt.Errorf("strconv.ParseUint fail,err:%v,value:%s", err, sizeStr)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// RedisInstanceDataSize redis数据量大小,'info memory' used_memory,单位byte
func (db *RedisClient) RedisInstanceDataSize() (dataSize uint64, err error) {
	// 命令'info Dataset',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("RedisInstanceDataSize redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	var infoRet map[string]string
	infoRet, err = db.Info("memory")
	if err != nil {
		return
	}
	sizeStr := infoRet["used_memory"]
	dataSize, err = strconv.ParseUint(sizeStr, 10, 64)
	if err != nil {
		err = fmt.Errorf("strconv.ParseUint fail,err:%v,value:%s", err, sizeStr)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// TendisSSDDataSize 获取tendisSSD数据量大小,单位 byte
func (db *RedisClient) TendisSSDDataSize() (rockdbSize uint64, err error) {
	// 命令'info',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("TendisSSDDataSize redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	infoRet, err := db.Info("")
	if err != nil {
		return 0, err
	}

	rockdbSize = 0
	levelHeadRegexp := regexp.MustCompile(`^level-\d+$`)
	levelDataRegexp := regexp.MustCompile(`^bytes=(\d+),num_entries=(\d+),num_deletions=(\d+)`)
	for k01, v01 := range infoRet {
		if levelHeadRegexp.MatchString(k01) {
			list01 := levelDataRegexp.FindStringSubmatch(v01)
			if len(list01) != 4 {
				err = fmt.Errorf("redis:%s info 'RocksDB Level stats' format not correct,%s:%s", db.Addr, k01, v01)
				mylog.Logger.Error(err.Error())
				return
			}
			size01, _ := strconv.ParseUint(list01[1], 10, 64)
			rockdbSize = rockdbSize + size01
		}
	}
	return
}

// TendisSSDBinlogSize tendis ssd binlog size
type TendisSSDBinlogSize struct {
	FirstSeq uint64 `json:"firstSeq"`
	EndSeq   uint64 `json:"endSeq"`
}

// String 字符串
func (t *TendisSSDBinlogSize) String() string {
	return fmt.Sprintf("[%d,%d]", t.FirstSeq, t.EndSeq)
}

// parseBinlogSizeCmdRet 解析tendisSSD binlogsize命令的结果
func (db *RedisClient) parseBinlogSizeCmdRet(cmdRet interface{}) (ret TendisSSDBinlogSize, err error) {
	sizeInfos, ok := cmdRet.([]interface{})
	if ok == false {
		err = fmt.Errorf("parseBinlogSizeCmdRet 'binlogsize' result not []interface{},cmdRet:%v,nodeAddr:%s",
			cmdRet, db.Addr)
		mylog.Logger.Error(err.Error())
		return ret, err
	}
	if len(sizeInfos) != 4 {
		err = fmt.Errorf("'binlogsize' result not correct,length:%d != 4,data:%+v,addr:%s",
			len(sizeInfos), sizeInfos, db.Addr)
		mylog.Logger.Error(err.Error())
		return ret, err
	}
	firstSeqStr := sizeInfos[1].(string)
	endSeqStr := sizeInfos[3].(string)

	ret.FirstSeq, err = strconv.ParseUint(firstSeqStr, 10, 64)
	if err != nil {
		err = fmt.Errorf("'binlogsize' firstSeq:%s to uint64 fail,err:%v,data:%+v,addr:%s",
			firstSeqStr, err, sizeInfos, db.Addr)
		mylog.Logger.Error(err.Error())
		return ret, err
	}
	ret.EndSeq, err = strconv.ParseUint(endSeqStr, 10, 64)
	if err != nil {
		err = fmt.Errorf("'binlogsize' endSeq:%s to uint64 fail,err:%v,data:%+v,addr:%s",
			endSeqStr, err, sizeInfos, db.Addr)
		mylog.Logger.Error(err.Error())
		return ret, err
	}
	return ret, nil
}

// TendisSSDBinlogSize binlogsize
func (db *RedisClient) TendisSSDBinlogSize() (ret TendisSSDBinlogSize, err error) {
	// 命令'info',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("TendisSSDDataSize redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	cmd := []interface{}{"binlogsize"}
	ret = TendisSSDBinlogSize{}
	sizeRet, err := db.InstanceClient.Do(context.TODO(), cmd...).Result()
	if err != nil {
		err = fmt.Errorf("TendisSSDBinlogSize fail,cmd:%v fail,err:%v,addr:%s", cmd, err, db.Addr)
		mylog.Logger.Error(err.Error())
		return ret, err
	}
	return db.parseBinlogSizeCmdRet(sizeRet)
}

// Randomkey command
func (db *RedisClient) Randomkey() (key string, err error) {
	// 命令'RANDOMKEY',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("Randomkey redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	key, err = db.InstanceClient.RandomKey(context.TODO()).Result()
	if err != nil && err != redis.Nil {
		err = fmt.Errorf("redis:%s 'randomkey' failed,err:%v", db.Addr, err)
		mylog.Logger.Error(err.Error())
		return
	}
	return key, nil
}

// Shutdown command
func (db *RedisClient) Shutdown() (err error) {
	// 命令'shutdown',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("Shutdown redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	redisCliBin := filepath.Join(consts.UsrLocal, "redis/bin/redis-cli")
	if util.FileExists(redisCliBin) {
		// 如果redis-cli存在,则优先使用redis-cli 执行shutdown
		// db.InstanceClient.Shutdown() 会返回一些其他错误
		var opt string
		if util.IsCliSupportedNoAuthWarning(redisCliBin) {
			opt = "--no-auth-warning"
		}
		l01 := strings.Split(db.Addr, ":")
		cmd := fmt.Sprintf("%s -h %s -p %s -a %s %s shutdown",
			redisCliBin, l01[0], l01[1], db.Password, opt)
		logcmd := fmt.Sprintf("%s -h %s -p %s -a xxxx %s shutdown",
			redisCliBin, l01[0], l01[1], opt)
		mylog.Logger.Info(logcmd)
		_, err = util.RunBashCmd(cmd, "", nil, 1*time.Minute)
		if err != nil {
			return
		}
		return
	}

	db.InstanceClient.Shutdown(context.TODO()).Result()
	return nil
}

// IsReplicaStatusOk '我'是slave,判断我和master的复制状态是否ok
func (db *RedisClient) IsReplicaStatusOk(masterIP, masterPort string) (ok bool, err error) {
	var infoRet map[string]string
	ok = false
	infoRet, err = db.Info("replication")
	if err != nil {
		return
	}
	replRole := infoRet["role"]
	if replRole != consts.RedisSlaveRole {
		return false, nil
	}
	replMasterHost := infoRet["master_host"]
	replMasterPort := infoRet["master_port"]
	replLinkStatus := infoRet["master_link_status"]
	if replMasterHost != masterIP || replMasterPort != masterPort {
		err = fmt.Errorf("slave(%s) 'info replication' master(%s:%s) != (%s:%s)",
			db.Addr, replMasterHost, replMasterPort, masterIP, masterPort)
		return
	}
	if replLinkStatus != consts.MasterLinkStatusUP {
		err = fmt.Errorf("slave(%s) 'info replication' master(%s:%s) master_link_status:%s",
			db.Addr, replMasterHost, replMasterPort, replLinkStatus)
		return
	}
	return true, nil
}

// IsTendisSSDReplicaStatusOk '我'是tendisssd slave,判断我和master的复制状态是否ok
func (db *RedisClient) IsTendisSSDReplicaStatusOk(masterIP, masterPort string) (ok bool, err error) {
	ok, err = db.IsReplicaStatusOk(masterIP, masterPort)
	if err != nil {
		return
	}
	if !ok {
		return
	}
	ok = false
	// master上执行 info slaves,结果中 slave的状态必须是 IncrSync/REPL_FOLLOW
	var confRet map[string]string
	var masterCli *RedisClient
	var slavesState TendisSSDInfoSlavesData
	masterAddr := masterIP + ":" + masterPort
	confRet, err = db.ConfigGet("masterauth")
	if err != nil {
		return
	}
	masterAuth := confRet["masterauth"]
	masterCli, err = NewRedisClient(masterAddr, masterAuth, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return
	}
	defer masterCli.Close()

	slavesState, err = masterCli.TendisSSDInfoSlaves()
	if err != nil {
		return
	}
	if len(slavesState.SlaveList) == 0 {
		err = fmt.Errorf("slave(%s) master_link_status:up but master(%s) 'info slaves' not found slaves", db.Addr, masterAddr)
		return
	}
	for _, slave01 := range slavesState.SlaveList {
		slaveItem := slave01
		if slaveItem.Addr() == db.Addr {
			if slaveItem.State == consts.TendisSSDIncrSyncState ||
				slaveItem.State == consts.TendisSSDReplFollowtate {
				return true, nil
			}
			mylog.Logger.Info(fmt.Sprintf("master(%s) 'info slaves' ret:%s", masterAddr, slavesState.String()))
			err = fmt.Errorf(
				"slave(%s) master_link_status:up but master(%s) 'info slaves' slave.state:%s != IncrSync|REPL_FOLLOW",
				db.Addr, masterAddr, slaveItem.State)
			return
		}
	}
	mylog.Logger.Info(fmt.Sprintf("master(%s) 'info slaves' ret:%s", masterAddr, slavesState.String()))
	err = fmt.Errorf("slave(%s) master_link_status:up but master(%s) 'info slaves' not found record", db.Addr, masterAddr)
	return
}

// RedisClusterGetMasterNode 获取master节点信息(如果 addr是master则返回它的node信息,否则找到它的masterID,进而找到master的node信息)
func (db *RedisClient) RedisClusterGetMasterNode(addr string) (masterNode *ClusterNodeData, err error) {
	addrToNodes, err := db.GetAddrMapToNodes()
	if err != nil {
		return
	}
	myNode, ok := addrToNodes[addr]
	if !ok {
		err = fmt.Errorf("addr:%s not found in cluster nodes", addr)
		mylog.Logger.Error(err.Error())
		return
	}
	if myNode.GetRole() == consts.RedisMasterRole {
		masterNode = myNode
		return
	}
	masterNodeID := myNode.MasterID
	idToNode, err := db.GetNodeIDMapToNodes()
	if err != nil {
		return
	}
	masterNode, ok = idToNode[masterNodeID]
	if !ok {
		err = fmt.Errorf("masterNodeID:%s not found in cluster nodes", masterNodeID)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// MaxMemory 'confxx get maxmemory'
func (db *RedisClient) MaxMemory() (maxmemory uint64, err error) {
	var confRet map[string]string
	confRet, err = db.ConfigGet("maxmemory")
	if err != nil {
		return
	}
	str01, ok := confRet["maxmemory"]
	if !ok {
		err = fmt.Errorf("redis(%s) get maxmemory fail,'confxx get maxmemory' ret:%+v", db.Addr, confRet)
		mylog.Logger.Error(err.Error())
		return
	}
	maxmemory, _ = strconv.ParseUint(str01, 10, 64)
	return
}

// GetMemUsed 'info memory' used_memory/used_memory_rss
func (db *RedisClient) GetMemUsed() (memoryUsed, memoryUsedRss uint64, err error) {
	var infoRet map[string]string
	var memoryUsedStr, memoryRssStr string
	var ok bool
	infoRet, err = db.Info("memory")
	if err != nil {
		return
	}
	memoryUsedStr, ok = infoRet["used_memory"]
	if !ok {
		err = fmt.Errorf("redis(%s)  used_memory not found,'info memory' ret:%+v", db.Addr, infoRet)
		mylog.Logger.Error(err.Error())
		return
	}
	memoryRssStr, ok = infoRet["used_memory_rss"]
	if !ok {
		err = fmt.Errorf("redis(%s) get used_memory_rss not found,'info memory' ret:%+v", db.Addr, infoRet)
		mylog.Logger.Error(err.Error())
		return
	}
	memoryUsed, _ = strconv.ParseUint(memoryUsedStr, 10, 64)
	memoryUsedRss, _ = strconv.ParseUint(memoryRssStr, 10, 64)
	return
}

// Set set $k $v ex/px $expiration
func (db *RedisClient) Set(k string, val interface{}, expiration time.Duration) (ret string, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.Set(context.TODO(), k, val, expiration).Result()
	} else {
		ret, err = db.InstanceClient.Set(context.TODO(), k, val, expiration).Result()
	}
	if err != nil {
		err = fmt.Errorf("'set %s %v ex %d' fail,err:%v,addr:%s", k, val, int(expiration.Seconds()), err, db.Addr)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

// Mset mset ...
func (db *RedisClient) Mset(vals []interface{}) (ret string, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.MSet(context.TODO(), vals...).Result()
	} else {
		ret, err = db.InstanceClient.MSet(context.TODO(), vals...).Result()
	}
	if err != nil {
		err = fmt.Errorf("mset %+v fail,err:%v,addr:%s", vals, err, db.Addr)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

// Get 'get key'
func (db *RedisClient) Get(k string) (ret string, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.Get(context.TODO(), k).Result()
	} else {
		ret, err = db.InstanceClient.Get(context.TODO(), k).Result()
	}
	if err != nil {
		err = fmt.Errorf("'get %s' fail,err:%v,addr:%s", k, err, db.Addr)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

// Hmset hmset ...
func (db *RedisClient) Hmset(k string, vals []interface{}) (ret bool, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.HMSet(context.TODO(), k, vals...).Result()
	} else {
		ret, err = db.InstanceClient.HMSet(context.TODO(), k, vals...).Result()
	}
	if err != nil {
		err = fmt.Errorf("hmset %s %+v fail,err:%v,addr:%s", k, vals, err, db.Addr)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

// Rpush rpush ...
func (db *RedisClient) Rpush(k string, vals []interface{}) (ret int64, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.RPush(context.TODO(), k, vals...).Result()
	} else {
		ret, err = db.InstanceClient.RPush(context.TODO(), k, vals...).Result()
	}
	if err != nil {
		err = fmt.Errorf("rpush %s %+v fail,err:%v,addr:%s", k, vals, err, db.Addr)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

// Sadd sadd ...
func (db *RedisClient) Sadd(k string, vals []interface{}) (ret int64, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.SAdd(context.TODO(), k, vals...).Result()
	} else {
		ret, err = db.InstanceClient.SAdd(context.TODO(), k, vals...).Result()
	}
	if err != nil {
		err = fmt.Errorf("Sadd %s %+v fail,err:%v,addr:%s", k, vals, err, db.Addr)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

// Zadd zadd ...
func (db *RedisClient) Zadd(k string, members []*redis.Z) (ret int64, err error) {
	if db.DbType == consts.TendisTypeRedisCluster {
		ret, err = db.ClusterClient.ZAdd(context.TODO(), k, members...).Result()
	} else {
		ret, err = db.InstanceClient.ZAdd(context.TODO(), k, members...).Result()
	}
	if err != nil {
		err = fmt.Errorf("Zadd %s %+v fail,err:%v,addr:%s", k, members, err, db.Addr)
		mylog.Logger.Info(err.Error())
		return
	}
	return
}

// AdminSet tendisplus 'adminset' 命令
func (db *RedisClient) AdminSet(key, val string) (ret string, err error) {
	var ok bool
	// 命令'adminset ',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("'adminset' redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	cmd := []interface{}{"adminset", key, val}
	adminsetRet, err := db.InstanceClient.Do(context.TODO(), cmd...).Result()
	if err != nil {
		err = fmt.Errorf("redis:%s 'adminget %s' fail,err:%v\n", db.Addr, key, err)
		mylog.Logger.Error(err.Error())
		return
	}
	ret, ok = adminsetRet.(string)
	if ok == false {
		err = fmt.Errorf("'adminget %s %s' result not string,ret:%+v,nodeAddr:%s", key, val, adminsetRet, db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	return
}

// GetTendisplusHeartbeat 获取tendisplus 心跳数据
/* for example:
> adminget 1.1.1.1:heartbeat
 1) 1) "0"
    2) "2021-06-01 16:47:00"
 2) 1) "1"
    2) "2021-06-01 16:47:00"
 3) 1) "2"
    2) "2021-06-01 16:47:00"
 4) 1) "3"
    2) "2021-06-01 16:47:00"
 5) 1) "4"
    2) "2021-06-01 16:47:00"
 6) 1) "5"
    2) "2021-06-01 16:47:00"
 7) 1) "6"
    2) "2021-06-01 16:47:00"
 8) 1) "7"
    2) "2021-06-01 16:47:00"
 9) 1) "8"
    2) "2021-06-01 16:47:00"
10) 1) "9"
    2) "2021-06-01 16:47:00"
*/
func (db *RedisClient) GetTendisplusHeartbeat(key string) (heartbeat map[int]time.Time, err error) {
	// 命令'adminget ',只能用 普通redis client
	if db.InstanceClient == nil {
		err = fmt.Errorf("'adminget' redis:%s must create a standalone client", db.Addr)
		mylog.Logger.Error(err.Error())
		return
	}
	heartbeat = make(map[int]time.Time)
	cmd := []interface{}{"adminget", key}
	adminGetRet, err := db.InstanceClient.Do(context.TODO(), cmd...).Result()
	if err != nil {
		err = fmt.Errorf("redis:%s 'adminget %s' fail,err:%v\n", db.Addr, key, err)
		mylog.Logger.Error(err.Error())
		return heartbeat, err
	}
	adminGetRets, ok := adminGetRet.([]interface{})
	if ok == false {
		err = fmt.Errorf("GetTendisplusHeartbeat 'adminget %s' result not []interface{},nodeAddr:%s", key, db.Addr)
		mylog.Logger.Error(err.Error())
		return heartbeat, err
	}
	var storeID int
	var value, storeIDStr string
	for _, confItem := range adminGetRets {
		conf01 := confItem.([]interface{})
		if conf01[1] == nil {
			continue
		}
		storeIDStr = conf01[0].(string)
		value = conf01[1].(string)
		storeID, _ = strconv.Atoi(storeIDStr)
		heartbeat[storeID], _ = time.ParseInLocation(consts.UnixtimeLayout, value, time.Local)
	}
	return heartbeat, nil
}

// Close 关闭连接
func (db *RedisClient) Close() {
	if db.InstanceClient == nil && db.ClusterClient == nil {
		return
	}

	if db.DbType == consts.TendisTypeRedisCluster {
		db.ClusterClient.Close()
		db.ClusterClient = nil
		return
	}
	db.InstanceClient.Close()
	db.InstanceClient = nil
	return
}
