package redis_rpc

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/go-redis/redis/v8"
)

// RedisClient redis连接信息
type RedisClient struct {
	Addr           string        `json:"addr"`
	Password       string        `json:"password"`
	DB             int           `json:"db"`
	MaxRetryTime   int           `json:"maxRetryTimes"`
	InstanceClient *redis.Client `json:"-"`
}

// NewRedisClientWithTimeout 建redis客户端,可指定超时时间
func NewRedisClientWithTimeout(addr, passwd string, db int, timeout time.Duration) (
	conn *RedisClient, err error) {
	conn = &RedisClient{
		Addr:         addr,
		Password:     passwd,
		DB:           db,
		MaxRetryTime: int(timeout.Seconds()),
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
			return err
		}
		_, err = pipe01.Exec(context.TODO())
		if err != nil {
			err = fmt.Errorf("newConnct pipeline.exec db fail,err:%v", err)
			slog.Error(err.Error())
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
		PoolSize:        10,
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
		PoolSize:        10,
		OnConnect:       redisConnHook,
	}
	if db.Password != "" {
		redisOpt.Password = db.Password
		clusterOpt.Password = db.Password
	}
	db.InstanceClient = redis.NewClient(redisOpt)
	_, err = db.InstanceClient.Ping(context.TODO()).Result()
	if err != nil {
		errStr := fmt.Sprintf("redis new conn fail,sleep 10s then retry.err:%v,addr:%s", err, db.Addr)
		slog.Error(errStr)
		return fmt.Errorf("redis new conn fail,err:%v addr:%s", err, db.Addr)
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
	ret, err = db.InstanceClient.Do(context.TODO(), dstCmds...).Result()
	if err != nil && err != redis.Nil {
		slog.Error("Redis  DoCommand fail,err:%v,command:%+v,addr:%s", err, cmdArgv, db.Addr)
		return nil, err
	} else if err != nil && err == redis.Nil {
		return "", nil
	}
	return ret, nil
}

// SelectDB db
func (db *RedisClient) SelectDB(dbNum int) (err error) {
	if db.DB == dbNum {
		return nil
	}
	pipe01 := db.InstanceClient.Pipeline()
	_, err = pipe01.Select(context.TODO(), dbNum).Result()
	if err != nil && err != redis.Nil {
		err = fmt.Errorf("redis:%s selectdb fail,err:%v", db.Addr, err)
		slog.Error(err.Error())
		return
	}
	_, err = pipe01.Exec(context.TODO())
	if err != nil && err != redis.Nil {
		err = fmt.Errorf("redis:%s selectdb fail,err:%v", db.Addr, err)
		slog.Error(err.Error())
		return
	}
	db.DB = dbNum
	return nil
}

// Close redis
func (db *RedisClient) Close() {
	db.InstanceClient.Close()
}
