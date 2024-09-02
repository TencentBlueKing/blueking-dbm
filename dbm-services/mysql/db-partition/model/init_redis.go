package model

import (
	"fmt"
	"log/slog"
	"time"

	"github.com/go-redis/redis"
	"github.com/spf13/viper"
)

var rdb *redis.Client

// InitClient 初始化连接
func InitClient() (err error) {
	// 初始化redis客户端
	rdb = redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%d", viper.GetString("redis.host"), viper.GetInt("redis.port")),
		Password: viper.GetString("redis.password"),
		DB:       0,
	})
	slog.Info("redis info", "host", viper.GetString("redis.host"),
		"port", viper.GetInt("redis.port"))
	// 检查连通性
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
