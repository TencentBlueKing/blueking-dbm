package client

import (
	"context"
	"dbm-services/common/dbha/ha-module/log"
	"time"

	"github.com/go-redis/redis/v8"
)

// RedisClientType TODO
type RedisClientType int

const (
	// RedisInstance TODO
	RedisInstance = 0
	// RedisCluster TODO
	RedisCluster = 1
)

// RedisClient TODO
type RedisClient struct {
	rdb  *redis.Client
	crdb *redis.ClusterClient
	mode RedisClientType
}

// InitCluster TODO
func (r *RedisClient) InitCluster(addr string, passwd string, timeout int) {
	timeoutVal := time.Duration(timeout) * time.Second
	r.crdb = redis.NewClusterClient(&redis.ClusterOptions{
		Addrs:        []string{addr},
		Password:     passwd,
		DialTimeout:  timeoutVal,
		ReadTimeout:  timeoutVal,
		WriteTimeout: timeoutVal,
	})
	r.mode = RedisCluster
	return
}

// Init TODO
func (r *RedisClient) Init(addr string, passwd string, timeout int, dbnum int) {
	timeoutVal := time.Duration(timeout) * time.Second
	r.rdb = redis.NewClient(&redis.Options{
		Addr:         addr,
		Password:     passwd,
		DB:           dbnum,
		DialTimeout:  timeoutVal,
		ReadTimeout:  timeoutVal,
		WriteTimeout: timeoutVal,
	})
	r.mode = RedisInstance
	return
}

// Ping TODO
func (r *RedisClient) Ping() (interface{}, error) {
	ret, err := r.rdb.Ping(context.TODO()).Result()
	if err != nil {
		log.Logger.Errorf("redisClient ping err[%s]", err.Error())
		return nil, err
	} else {
		return ret, nil
	}
}

// DoCommand TODO
func (r *RedisClient) DoCommand(cmdArgv []string) (interface{}, error) {
	cmds := make([]interface{}, 0)
	for _, cmd := range cmdArgv {
		cmds = append(cmds, cmd)
	}

	var (
		ret interface{}
		err error
	)
	if r.mode == RedisInstance {
		ret, err = r.rdb.Do(context.TODO(), cmds...).Result()
	} else {
		ret, err = r.crdb.Do(context.TODO(), cmds...).Result()
	}
	if err != nil {
		log.Logger.Errorf("redisClient DoCommand err[%s]", err.Error())
		return nil, err
	} else {
		return ret, nil
	}
}

// Info TODO
func (r *RedisClient) Info() (interface{}, error) {
	var (
		ret interface{}
		err error
	)

	if r.mode == RedisInstance {
		ret, err = r.rdb.Info(context.TODO()).Result()
	} else {
		ret, err = r.crdb.Info(context.TODO()).Result()
	}
	if err != nil {
		return nil, err
	} else {
		return ret, nil
	}
}

// SlaveOf TODO
func (r *RedisClient) SlaveOf(host, port string) (interface{}, error) {
	var (
		ret interface{}
		err error
	)

	if r.mode == RedisInstance {
		ret, err = r.rdb.SlaveOf(context.TODO(), host, port).Result()
	} else {
		ret, err = r.crdb.SlaveOf(context.TODO(), host, port).Result()
	}
	if err != nil {
		return nil, err
	} else {
		return ret, nil
	}
}

// Type TODO
func (r *RedisClient) Type(key string) (interface{}, error) {
	var (
		ret interface{}
		err error
	)

	if r.mode == RedisInstance {
		ret, err = r.rdb.Type(context.TODO(), key).Result()
	} else {
		ret, err = r.crdb.Type(context.TODO(), key).Result()
	}
	if err != nil {
		return nil, err
	} else {
		return ret, nil
	}
}

// ClusterFailover TODO
func (r *RedisClient) ClusterFailover() (interface{}, error) {
	var (
		ret interface{}
		err error
	)

	if r.mode == RedisInstance {
		ret, err = r.rdb.ClusterFailover(context.TODO()).Result()
	} else {
		ret, err = r.crdb.ClusterFailover(context.TODO()).Result()
	}
	if err != nil {
		return nil, err
	} else {
		return ret, nil
	}
}

// Close TODO
func (r *RedisClient) Close() {
	if r.mode == RedisInstance {
		r.rdb.Close()
	} else {
		r.crdb.Close()
	}
}
