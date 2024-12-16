package client

import (
	"context"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/log"

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

		// disable retry.
		MaxRedirects: -1,
		MaxRetries:   -1,
	})
	r.mode = RedisCluster
	return
}

// Init TODO
func (r *RedisClient) Init(addr string, passwd string, timeout int, dbnum int) {
	timeoutVal := time.Duration(timeout) * time.Second
	r.rdb = redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: passwd,
		DB:       dbnum,

		// Dial timeout for establishing new connections. Default is 5 seconds.
		// DialTimeout:  timeoutVal,
		ReadTimeout:  timeoutVal,
		WriteTimeout: timeoutVal,
		//  Default is 3 retries; -1 (not 0) disables retries.
		MaxRetries: -1,
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

// Info 执行info [section]命令并将返回结果保存在map中
func (r *RedisClient) InfoV2(section string) (infoRet map[string]string, err error) {
	infoRet = make(map[string]string)
	var str01 string
	ctx := context.TODO()
	if section == "" && r.mode != RedisInstance {
		str01, err = r.crdb.Info(ctx).Result()
	} else if section != "" && r.mode != RedisInstance {
		str01, err = r.crdb.Info(ctx, section).Result()
	} else if section == "" && r.mode == RedisInstance {
		str01, err = r.rdb.Info(ctx).Result()
	} else if section != "" && r.mode == RedisInstance {
		str01, err = r.rdb.Info(ctx, section).Result()
	}
	if err != nil {
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

// Get Redis `GET key` command. It returns redis.Nil error when key does not exist.
func (r *RedisClient) Get(key string) (ret string, err error) {
	if r.mode != RedisInstance {
		ret, err = r.crdb.Get(context.TODO(), key).Result()
	} else {
		ret, err = r.rdb.Get(context.TODO(), key).Result()
	}
	if err != nil && err != redis.Nil {
		return
	}
	return ret, nil
}

// SlaveOf TODO
func (r *RedisClient) SlaveOf(host, port string) (ret string, err error) {
	if r.mode == RedisInstance {
		ret, err = r.rdb.SlaveOf(context.TODO(), host, port).Result()
	} else {
		ret, err = r.crdb.SlaveOf(context.TODO(), host, port).Result()
	}
	if err != nil {
		return "nil", err
	}
	return ret, nil
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
