package model

import (
	"fmt"
	"time"

	"github.com/go-redis/redis"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

var rdb *redis.Client

// InitClient 初始化连接
func InitClient() (err error) {
	rdb = redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%d", viper.GetString("redis.host"), viper.GetInt("redis.port")),
		Password: viper.GetString("redis.password"),
		DB:       0,
	})

	_, err = rdb.Ping().Result()
	if err != nil {
		slog.Error("redis db", "ping err", err)
		return err
	}
	return nil
}

// Lock 加锁
func Lock(key string) (bool, error) {
	slog.Info("msg", "key", key)
	return rdb.SetNX(key, `{"lock":1}`, 30*time.Hour).Result()
}

/*
UnLock 解锁
func UnLock(key string) int64 {
	nums, err := rdb.Del(key).Result()
	if err != nil {
		log.Println(err.Error())
		return 0
	}
	return nums
}
*/
