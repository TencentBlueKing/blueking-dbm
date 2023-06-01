// Package myredis redis操作
package myredis

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/tclog"

	"github.com/go-redis/redis/v8"
	"go.uber.org/zap"
)

// RedisWorker redis连接信息
type RedisWorker struct {
	Addr     string        `json:"addr"`
	Password string        `json:"password"`
	DB       int           `json:"db"`
	Client   *redis.Client `json:"-"`
	logger   *zap.Logger   `json:"-"`
}

// ParamsString 将连接信息返回为字符串
func (db *RedisWorker) ParamsString() string {
	ret, _ := json.Marshal(db)
	return string(ret)
}

// NewRedisClient 新建redis连接
func NewRedisClient(addr, passwd string, db int, logger *zap.Logger) (conn *RedisWorker, err error) {
	retry := 0 // 如果失败。重试12次，10秒一次
	if logger == nil {
		logger = tclog.NewFileLogger("log/main.log")
	}
	conn = &RedisWorker{
		Addr:     addr,
		Password: passwd,
		DB:       db,
		logger:   logger,
	}
RECONNCT:
	if conn.Password == "" {
		conn.Client = redis.NewClient(&redis.Options{
			Addr:        conn.Addr,
			DB:          conn.DB,
			DialTimeout: 10 * time.Second,
			MaxConnAge:  24 * time.Hour,
		})
	} else {
		conn.Client = redis.NewClient(&redis.Options{
			Addr:        conn.Addr,
			Password:    conn.Password,
			DB:          conn.DB,
			DialTimeout: 10 * time.Second,
			MaxConnAge:  24 * time.Hour,
		})
	}
	_, err = conn.Client.Ping(context.TODO()).Result()
	if err != nil {
		conn.logger.Error("redis new client fail,sleep 10s then retry.err:%v,addr:%s",
			zap.Error(err), zap.String("params", conn.ParamsString()))
		if retry < 12 {
			retry++
			time.Sleep(10 * time.Second)
			goto RECONNCT
		} else {
			return nil, fmt.Errorf("redis new client fail,err:%v addr:%s", err, conn.Addr)
		}
	}
	return
}

// LPush ..
func (db *RedisWorker) LPush(key01, data string) error {
	_, err := db.Client.LPush(context.TODO(), key01, data).Result()
	if err != nil {
		db.logger.Error("redis lpush fail", zap.Error(err),
			zap.String("key", key01), zap.String("data", data),
			zap.String("params", db.ParamsString()))
		err = fmt.Errorf("redis lpush fail,err:%v,keyname:%s", err, key01)
		return err
	}
	return err
}

// SetNx ..
func (db *RedisWorker) SetNx(key01 string, data interface{}, expire time.Duration) (bool, error) {
	ret, err := db.Client.SetNX(context.TODO(), key01, data, expire).Result()
	if err != nil {
		db.logger.Error("redis setNx fail", zap.Error(err),
			zap.String("key", key01), zap.Any("data", data),
			zap.String("params", db.ParamsString()))
		err = fmt.Errorf("redis setNx fail,err:%v,keyname:%s", err, key01)
		return false, err
	}
	return ret, nil
}

// SetEx ..
func (db *RedisWorker) SetEx(key01 string, data interface{}, expire time.Duration) (string, error) {
	ret, err := db.Client.SetEX(context.TODO(), key01, data, expire).Result()
	if err != nil {
		db.logger.Error("redis setEx fail", zap.Error(err),
			zap.String("key", key01), zap.Any("data", data),
			zap.String("params", db.ParamsString()))
		err = fmt.Errorf("redis setEX fail,err:%v,keyname:%s", err, key01)
		return "", err
	}
	return ret, nil
}

// Get ..
func (db *RedisWorker) Get(key01 string) (val01 string, err error) {
	val01, err = db.Client.Get(context.TODO(), key01).Result()
	if err != nil && err != redis.Nil {
		db.logger.Error("redis get fail", zap.Error(err),
			zap.String("key", key01), zap.String("params", db.ParamsString()))
		err = fmt.Errorf("redis get fail,err:%v,keyName:%s", err, key01)
		return
	}
	return
}

// Expire ..
func (db *RedisWorker) Expire(key01 string, expire time.Duration) (bool, error) {
	_, err := db.Client.Expire(context.TODO(), key01, expire).Result()
	if err != nil && err != redis.Nil {
		db.logger.Error("redis expire fail", zap.Error(err),
			zap.String("key", key01), zap.String("params", db.ParamsString()))
		err = fmt.Errorf("redis expire fail,err:%v,keyname:%s", err, key01)
		return false, err
	}
	if err != nil && err == redis.Nil {
		return false, nil
	}
	return true, nil
}

// SISMember ..
func (db *RedisWorker) SISMember(key01, member01 string) (bool, error) {
	ret, err := db.Client.SIsMember(context.TODO(), key01, member01).Result()
	if err != nil && err != redis.Nil {
		db.logger.Error("redis SIsMember fail", zap.Error(err),
			zap.String("key", key01), zap.String("member01", member01),
			zap.String("params", db.ParamsString()))
		err = fmt.Errorf("redis SIsMember fail,err:%v,keyname:%s,member:%s", err, key01, member01)
		return false, err
	}
	return ret, nil
}

// TendisSSDBakcup tendisSSD执行备份命令
func (db *RedisWorker) TendisSSDBakcup(dstDir string) error {
	cmd := []interface{}{"backup", dstDir}
	_, err := db.Client.Do(context.TODO(), cmd...).Result()
	if err != nil {
		db.logger.Error("tendisssd instance backup fail", zap.Error(err),
			zap.Any("backupCmd", cmd), zap.String("Addr:", db.Addr))
		return fmt.Errorf("tendisssd:%s backup fail,err:%v,cmd:%s %s", db.Addr, err, "backup", dstDir)
	}
	db.logger.Info(fmt.Sprintf("tendisssd:%s start backup dstdir:%s", db.Addr, dstDir))
	return nil
}

// InfoBackups tendisSSD 执行Info Backups得到的结果解析
type InfoBackups struct {
	BackupCount          int    `json:"backup-count"`
	LastBackupTime       int    `json:"last-backup-time"`
	CurrentBackupRunning string `json:"current-backup-running"`
}

// TendisSSDInfoBackups tenidsSSD执行info Backups得到的结果
func (db *RedisWorker) TendisSSDInfoBackups() (*InfoBackups, error) {
	str01, err := db.Client.Info(context.TODO(), "Backups").Result()
	if err != nil {
		db.logger.Error("tendisssd info backups fail", zap.Error(err),
			zap.Any("Cmd", "info Backups"), zap.String("Addr:", db.Addr))
		return nil, fmt.Errorf("tendisssd:%s info backups fail,err:%v,cmd:%s", db.Addr, err, "info Backups")
	}
	infoList := strings.Split(str01, "\n")
	ret := &InfoBackups{}
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
		if list01[0] == "backup-count" {
			ret.BackupCount, _ = strconv.Atoi(list01[0])
		} else if list01[0] == "last-backup-time" {
			ret.LastBackupTime, _ = strconv.Atoi(list01[0])
		} else if list01[0] == "current-backup-running" {
			ret.CurrentBackupRunning = list01[1]
		}
	}
	return ret, nil
}

// TendisSSDIsBackupRunning tendisSSD是否在备份中
func (db *RedisWorker) TendisSSDIsBackupRunning() (bool, error) {
	info01, err := db.TendisSSDInfoBackups()
	if err != nil {
		return false, err
	}
	if info01.CurrentBackupRunning == "yes" {
		return true, nil
	} else {
		return false, nil
	}
}

// ConfigSet tendis执行config set
func (db *RedisWorker) ConfigSet(confName string, val interface{}) (string, error) {
	var err error
	var ok bool
	valStr := fmt.Sprintf("%v", val)
	// 先执行config set,如果报错则执行 confxx set
	data, err := db.Client.ConfigSet(context.TODO(), confName, valStr).Result()
	if err != nil && strings.Contains(err.Error(), "ERR unknown command") {
		cmd := []interface{}{"confxx", "set", confName, val}
		confRet, err := db.Client.Do(context.TODO(), cmd...).Result()
		if err != nil {
			err = fmt.Errorf("%+v fail,err:%v,addr:%s", cmd, err, db.Addr)
			db.logger.Error(err.Error())
			return "", err
		}
		data, ok = confRet.(string)
		if !ok {
			err = fmt.Errorf(`confxx set result not interface{},cmd:%v,cmdRet:%v,nodeAddr:%s`,
				cmd, confRet, db.Addr)
			db.logger.Error(err.Error())
			return "", err
		}
	} else if err != nil {
		err = fmt.Errorf("redis config set %s %s fail,err:%v,addr:%s", confName, val, err, db.Addr)
		db.logger.Error(err.Error())
		return data, err
	}
	return data, nil
}

// ConfigGet tendis执行config get
func (db *RedisWorker) ConfigGet(confName string) (ret map[string]string, err error) {
	var confInfos []interface{}
	var ok bool
	ret = map[string]string{}

	// 先执行config get,如果报错则执行 confxx get
	confInfos, err = db.Client.ConfigGet(context.TODO(), confName).Result()
	if err != nil && strings.Contains(err.Error(), "ERR unknown command") {
		cmd := []interface{}{"confxx", "get", confName}
		var confRet interface{}
		confRet, err = db.Client.Do(context.TODO(), cmd...).Result()
		if err != nil {
			err = fmt.Errorf("cmd:%+v fail,err:%v,addr:%s", cmd, err, db.Addr)
			db.logger.Error(err.Error())
			return ret, err
		}
		confInfos, ok = confRet.([]interface{})
		if ok == false {
			err = fmt.Errorf("cmd:%v result not []interface{},cmdRet:%v,nodeAddr:%s", cmd, confRet, db.Addr)
			db.logger.Error(err.Error())
			return ret, err
		}
	} else if err != nil {
		err = fmt.Errorf(" cmd:config get %q failed,err:%v", confName, err)
		db.logger.Error(err.Error())
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

// TendisSSDBinlogSize tendis ssd binlog size
type TendisSSDBinlogSize struct {
	FirstSeq uint64 `json:"firstSeq"`
	EndSeq   uint64 `json:"endSeq"`
}

// TendisSSDBinlogSize command: binlogsize
func (db *RedisWorker) TendisSSDBinlogSize() (ret TendisSSDBinlogSize, err error) {
	cmd := []interface{}{"binlogsize"}
	ret = TendisSSDBinlogSize{}
	sizeRet, err := db.Client.Do(context.TODO(), cmd...).Result()
	if err != nil {
		db.logger.Error("TendisSSDBinlogSize fail", zap.Error(err), zap.Any("cmd", cmd))
		return ret, fmt.Errorf("cmd:%v fail,err:%v,addr:%s", cmd, err, db.Addr)
	}
	sizeInfos, ok := sizeRet.([]interface{})
	if ok == false {
		err = fmt.Errorf("TendisSSDBinlogSize cmd:%v result not []interface{},cmdRet:%v,nodeAddr:%s", cmd, sizeRet, db.Addr)
		db.logger.Error(err.Error())
		return ret, err
	}
	if len(sizeInfos) != 4 {
		err = fmt.Errorf("'binlogsize' result not correct,length:%d != 4,data:%+v,addr:%s",
			len(sizeInfos), sizeInfos, db.Addr)
		db.logger.Error(err.Error())
		return ret, err
	}
	firstSeqStr := sizeInfos[1].(string)
	endSeqStr := sizeInfos[3].(string)

	ret.FirstSeq, err = strconv.ParseUint(firstSeqStr, 10, 64)
	if err != nil {
		err = fmt.Errorf("'binlogsize' firstSeq:%s to uint64 fail,err:%v,data:%+v,addr:%s",
			firstSeqStr, err, sizeInfos, db.Addr)
		db.logger.Error(err.Error())
		return ret, err
	}
	ret.EndSeq, err = strconv.ParseUint(endSeqStr, 10, 64)
	if err != nil {
		err = fmt.Errorf("'binlogsize' endSeq:%s to uint64 fail,err:%v,data:%+v,addr:%s",
			endSeqStr, err, sizeInfos, db.Addr)
		db.logger.Error(err.Error())
		return ret, err
	}
	return ret, nil
}

// Info 执行info $section命令并将返回结果保存在map中
func (db *RedisWorker) Info(section string) (infoRet map[string]string, err error) {
	infoRet = make(map[string]string)
	str01, err := db.Client.Info(context.TODO(), section).Result()
	if err != nil {
		err = fmt.Errorf("redis:%s 'info %s' fail,err:%v", db.Addr, section, err)
		db.logger.Error(err.Error())
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

// GetMasterAddrAndPasswd 获取master addr和passsword信息
// 如果'self'是slave,则info replication中获取其master信息;
// 如果'self'是master,则直接返回其addr 和 password信息
func (db *RedisWorker) GetMasterAddrAndPasswd() (masterAddr, masterAuth string, err error) {
	var infoRet map[string]string
	var confRet map[string]string
	infoRet, err = db.Info("replication")
	if err != nil {
		return
	}
	if infoRet["role"] == constvar.RedisSlaveRole {
		masterAddr = infoRet["master_host"] + ":" + infoRet["master_port"]
		confRet, err = db.ConfigGet("masterauth")
		if err != nil {
			return
		}
		masterAuth = confRet["masterauth"]
	} else {
		masterAddr = db.Addr
		masterAuth = db.Password
	}
	return
}

// Close :关闭client
func (db *RedisWorker) Close() {
	if db.Client == nil {
		return
	}
	db.Client.Close()
	db.Client = nil
}
