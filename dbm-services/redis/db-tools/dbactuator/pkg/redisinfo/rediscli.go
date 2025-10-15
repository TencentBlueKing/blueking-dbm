// Package rediscli TODO
package redisinfo

import (
	"context"

	"fmt"
	"strings"
	"sync"

	"github.com/go-redis/redis/v8"
	"github.com/pkg/errors"
)

// CheckCmdValid TODO
func CheckCmdValid(args []string) error {

	dangerCmds := []string{"shutdown", "cleandb", "cleanall", "flushdb", "flushall", "eval", "script"}
	for _, arg := range args[:1] {
		for _, str := range dangerCmds {
			if strings.Contains(strings.ToLower(arg), strings.ToLower(str)) {
				return fmt.Errorf("invalid cmd: %s", arg)
			}
		}
	}
	return nil
}

func ConnectAndPingRedis(host, pass string) (*redis.Client, error) {
	var ctx = context.Background()
	client := redis.NewClient(&redis.Options{
		Addr:     host,
		Password: pass, // no password set
		DB:       0,    // use default DB
	})
	return client, client.Ping(ctx).Err()
}

// ExecRedisCommand 使用github.com/go-redis/redis/v8
func ExecRedisCommand(host, pass string, cmd ...string) (interface{}, error) {
	var ctx = context.Background()
	client := redis.NewClient(&redis.Options{
		Addr:     host,
		Password: pass, // no password set
		DB:       0,    // use default DB
	})
	defer client.Close()
	o := client.Ping(ctx)
	if o.Val() != "PONG" {
		return "", o.Err()
	}

	defer client.Close()

	var args []interface{}
	for _, v := range cmd {
		args = append(args, v)
	}

	if result, err := client.Do(ctx, args...).Result(); err == nil {
		return result, err
	} else {
		return nil, err
	}
}

// RedisHost TODO
type RedisHost struct {
	Host string
	Pass string
}

// RedisCommandIn TODO
type RedisCommandIn struct {
	Host string
	Pass string
	Cmd  []string
}

// RedisCommandOut TODO
type RedisCommandOut struct {
	Host string `json:"host"`
	Err  error  `json:"-"`
	Out  any    `json:"out"`
	Ok   int    `json:"ok"`
}

// ExecRedisCommandConcurrency并行执行多个指令 number 并发度，number最小值为1
func ExecRedisCommandConcurrency(in []RedisCommandIn, number int) ([]RedisCommandOut, error) {
	var wg sync.WaitGroup
	var mutex sync.Mutex

	outs := make([]RedisCommandOut, len(in))
	if len(in) == 0 {
		return nil, errors.Errorf("empty input")
	}
	for i := range in {
		if len(in[i].Cmd) == 0 {
			return nil, errors.Errorf("empty cmd")
		}
	}

	if number <= 0 {
		number = 1
	}

	ch := make(chan struct{}, number) // 并发数量

	for i := range in {
		i := i
		ch <- struct{}{}
		wg.Add(1)
		go func(wg *sync.WaitGroup, i int, row *RedisCommandIn) {
			defer wg.Done()
			out, err := ExecRedisCommand(row.Host, row.Pass, row.Cmd...)
			<-ch
			mutex.Lock()
			outs[i].Host = row.Host
			outs[i].Err = err
			outs[i].Out = out
			mutex.Unlock()
		}(&wg, i, &in[i])
	}
	wg.Wait()
	return outs, nil
}

// GetInfo 执行 info, 如果是2.8版本，会尝试使用confxx get *maxmemory* 获得maxmemory信息
func GetInfo(client *redis.Client, withMaxmemory bool) (*Info, error) {
	var ctx = context.Background()
	result, err := client.Do(ctx, "info").Result()
	if err != nil {
		return nil, err
	}
	info, err := Parse(result.(string))
	if err != nil {
		return nil, err
	}
	return &info, nil
}

func ConnRedis(host *RedisHost) (*redis.Client, error) {
	var ctx = context.Background()
	client := redis.NewClient(&redis.Options{
		Addr:     host.Host,
		Password: host.Pass, // no password set
		DB:       0,         // use default DB
	})
	if pong, err := client.Ping(ctx).Result(); err != nil || pong != "PONG" {
		return nil, err
	}
	return client, nil
}
