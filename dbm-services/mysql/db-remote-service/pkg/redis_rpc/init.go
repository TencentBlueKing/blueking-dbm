package redis_rpc

import (
	"fmt"
	"strings"
	"sync"
)

const (
	adminFlag    = "admin"
	writeFlag    = "write"
	readOnlyFlag = "read-only"
)

var once sync.Once

// RedisCommandTable redis命令表
var RedisCommandTable map[string]*RedisCmdMeta

// RedisCmdMeta redis命令项属性
type RedisCmdMeta struct {
	Name     string `json:"name"`
	Arity    int    `json:"arity"`  // 参数个数,用 -N 表示 >= N
	Sflags   string `json:"sflags"` // admin/write/read-only
	FirstKey int    `json:"firstKey"`
	LastKey  int    `json:"lastKey"`
	KeyStep  int    `json:"keyStep"`
}

// GetKeys 获取命令中的keys
func (m *RedisCmdMeta) GetKeys(srcCmd string) (keys []string, err error) {
	if strings.Contains(m.Sflags, adminFlag) {
		// admin类型的命令,没有keys
		return
	}
	if m.FirstKey == 0 {
		return
	}
	cmdArgs := strings.Fields(srcCmd)
	absArity := m.Arity
	if m.Arity < 0 {
		absArity = -m.Arity
	}
	if len(cmdArgs) < absArity {
		err = fmt.Errorf("'%s' cmdArgs len:%d not enough,need greater than or equal %d", cmdArgs[0], len(cmdArgs), absArity)
		return
	}
	last := m.LastKey
	if last < 0 {
		last = last + len(cmdArgs)
	}
	for i := m.FirstKey; i <= last; i = i + m.KeyStep {
		keys = append(keys, cmdArgs[i])
	}
	return
}

var twemproxyCommand = []string{
	// TODO 先不做限制。后面再看要不要指定命令限制
	"get nosqlproxy servers",
}

var redisError = []string{
	"Could not connect to Redis at",
	"NOAUTH Authentication required",
	"AUTH failed: ERR invalid password",
	"ERR wrong number of arguments",
}

func init() {
	once.Do(func() {
		RedisCommandTable = make(map[string]*RedisCmdMeta)
		RedisCommandTable["module"] = &RedisCmdMeta{Name: "module", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["get"] = &RedisCmdMeta{Name: "get", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["getserver"] = &RedisCmdMeta{Name: "getserver", Arity: 2, Sflags: readOnlyFlag,
			FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["getex"] = &RedisCmdMeta{Name: "getex", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["getdel"] = &RedisCmdMeta{Name: "getdel", Arity: 2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["set"] = &RedisCmdMeta{Name: "set", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["setnx"] = &RedisCmdMeta{Name: "setnx", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["setex"] = &RedisCmdMeta{Name: "setex", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["psetex"] = &RedisCmdMeta{Name: "psetex", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["append"] = &RedisCmdMeta{Name: "append", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["strlen"] = &RedisCmdMeta{Name: "strlen", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["del"] = &RedisCmdMeta{Name: "del", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["unlink"] = &RedisCmdMeta{Name: "unlink", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["exists"] = &RedisCmdMeta{Name: "exists", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["setbit"] = &RedisCmdMeta{Name: "setbit", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["getbit"] = &RedisCmdMeta{Name: "getbit", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["bitfield"] = &RedisCmdMeta{Name: "bitfield", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["bitfield_ro"] = &RedisCmdMeta{Name: "bitfield_ro", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["setrange"] = &RedisCmdMeta{Name: "setrange", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["getrange"] = &RedisCmdMeta{Name: "getrange", Arity: 4, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["substr"] = &RedisCmdMeta{Name: "substr", Arity: 4, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["incr"] = &RedisCmdMeta{Name: "incr", Arity: 2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["decr"] = &RedisCmdMeta{Name: "decr", Arity: 2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["mget"] = &RedisCmdMeta{Name: "mget", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["rpush"] = &RedisCmdMeta{Name: "rpush", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lpush"] = &RedisCmdMeta{Name: "lpush", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["rpushx"] = &RedisCmdMeta{Name: "rpushx", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lpushx"] = &RedisCmdMeta{Name: "lpushx", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["linsert"] = &RedisCmdMeta{Name: "linsert", Arity: 5, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["rpop"] = &RedisCmdMeta{Name: "rpop", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lpop"] = &RedisCmdMeta{Name: "lpop", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["brpop"] = &RedisCmdMeta{Name: "brpop", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: -2,
			KeyStep: 1}
		RedisCommandTable["brpoplpush"] = &RedisCmdMeta{Name: "brpoplpush", Arity: 4, Sflags: writeFlag, FirstKey: 1,
			LastKey: 2, KeyStep: 1}
		RedisCommandTable["blmove"] = &RedisCmdMeta{Name: "blmove", Arity: 6, Sflags: writeFlag, FirstKey: 1, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["blpop"] = &RedisCmdMeta{Name: "blpop", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: -2,
			KeyStep: 1}
		RedisCommandTable["llen"] = &RedisCmdMeta{Name: "llen", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lindex"] = &RedisCmdMeta{Name: "lindex", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lset"] = &RedisCmdMeta{Name: "lset", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lrange"] = &RedisCmdMeta{Name: "lrange", Arity: 4, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["ltrim"] = &RedisCmdMeta{Name: "ltrim", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lpos"] = &RedisCmdMeta{Name: "lpos", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["lrem"] = &RedisCmdMeta{Name: "lrem", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["rpoplpush"] = &RedisCmdMeta{Name: "rpoplpush", Arity: 3, Sflags: writeFlag, FirstKey: 1,
			LastKey: 2, KeyStep: 1}
		RedisCommandTable["lmove"] = &RedisCmdMeta{Name: "lmove", Arity: 5, Sflags: writeFlag, FirstKey: 1, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["sadd"] = &RedisCmdMeta{Name: "sadd", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["srem"] = &RedisCmdMeta{Name: "srem", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["smove"] = &RedisCmdMeta{Name: "smove", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["sismember"] = &RedisCmdMeta{Name: "sismember", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["smismember"] = &RedisCmdMeta{Name: "smismember", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["scard"] = &RedisCmdMeta{Name: "scard", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["spop"] = &RedisCmdMeta{Name: "spop", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["srandmember"] = &RedisCmdMeta{Name: "srandmember", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["sinter"] = &RedisCmdMeta{Name: "sinter", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["sinterstore"] = &RedisCmdMeta{Name: "sinterstore", Arity: -3, Sflags: writeFlag, FirstKey: 1,
			LastKey: -1, KeyStep: 1}
		RedisCommandTable["sunion"] = &RedisCmdMeta{Name: "sunion", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["sunionstore"] = &RedisCmdMeta{Name: "sunionstore", Arity: -3, Sflags: writeFlag, FirstKey: 1,
			LastKey: -1, KeyStep: 1}
		RedisCommandTable["sdiff"] = &RedisCmdMeta{Name: "sdiff", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["sdiffstore"] = &RedisCmdMeta{Name: "sdiffstore", Arity: -3, Sflags: writeFlag, FirstKey: 1,
			LastKey: -1, KeyStep: 1}
		RedisCommandTable["smembers"] = &RedisCmdMeta{Name: "smembers", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["sscan"] = &RedisCmdMeta{Name: "sscan", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zadd"] = &RedisCmdMeta{Name: "zadd", Arity: -4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zincrby"] = &RedisCmdMeta{Name: "zincrby", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zrem"] = &RedisCmdMeta{Name: "zrem", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zremrangebyscore"] = &RedisCmdMeta{Name: "zremrangebyscore", Arity: 4, Sflags: writeFlag,
			FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["zremrangebyrank"] = &RedisCmdMeta{Name: "zremrangebyrank", Arity: 4, Sflags: writeFlag,
			FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["zremrangebylex"] = &RedisCmdMeta{Name: "zremrangebylex", Arity: 4, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zunionstore"] = &RedisCmdMeta{Name: "zunionstore", Arity: -4, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zinterstore"] = &RedisCmdMeta{Name: "zinterstore", Arity: -4, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zdiffstore"] = &RedisCmdMeta{Name: "zdiffstore", Arity: -4, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zunion"] = &RedisCmdMeta{Name: "zunion", Arity: -3, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["zinter"] = &RedisCmdMeta{Name: "zinter", Arity: -3, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["zdiff"] = &RedisCmdMeta{Name: "zdiff", Arity: -3, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["zrange"] = &RedisCmdMeta{Name: "zrange", Arity: -4, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zrangestore"] = &RedisCmdMeta{Name: "zrangestore", Arity: -5, Sflags: writeFlag, FirstKey: 1,
			LastKey: 2, KeyStep: 1}
		RedisCommandTable["zrangebyscore"] = &RedisCmdMeta{Name: "zrangebyscore", Arity: -4, Sflags: readOnlyFlag,
			FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["zrevrangebyscore"] = &RedisCmdMeta{Name: "zrevrangebyscore", Arity: -4, Sflags: readOnlyFlag,
			FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["zrangebylex"] = &RedisCmdMeta{Name: "zrangebylex", Arity: -4, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zrevrangebylex"] = &RedisCmdMeta{Name: "zrevrangebylex", Arity: -4, Sflags: readOnlyFlag,
			FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["zcount"] = &RedisCmdMeta{Name: "zcount", Arity: 4, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zlexcount"] = &RedisCmdMeta{Name: "zlexcount", Arity: 4, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zrevrange"] = &RedisCmdMeta{Name: "zrevrange", Arity: -4, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zcard"] = &RedisCmdMeta{Name: "zcard", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zscore"] = &RedisCmdMeta{Name: "zscore", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zmscore"] = &RedisCmdMeta{Name: "zmscore", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zrank"] = &RedisCmdMeta{Name: "zrank", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zrevrank"] = &RedisCmdMeta{Name: "zrevrank", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["zscan"] = &RedisCmdMeta{Name: "zscan", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zpopmin"] = &RedisCmdMeta{Name: "zpopmin", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["zpopmax"] = &RedisCmdMeta{Name: "zpopmax", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["bzpopmin"] = &RedisCmdMeta{Name: "bzpopmin", Arity: -3, Sflags: writeFlag, FirstKey: 1,
			LastKey: -2, KeyStep: 1}
		RedisCommandTable["bzpopmax"] = &RedisCmdMeta{Name: "bzpopmax", Arity: -3, Sflags: writeFlag, FirstKey: 1,
			LastKey: -2, KeyStep: 1}
		RedisCommandTable["zrandmember"] = &RedisCmdMeta{Name: "zrandmember", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["hset"] = &RedisCmdMeta{Name: "hset", Arity: -4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hsetnx"] = &RedisCmdMeta{Name: "hsetnx", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hget"] = &RedisCmdMeta{Name: "hget", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hmset"] = &RedisCmdMeta{Name: "hmset", Arity: -4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hmget"] = &RedisCmdMeta{Name: "hmget", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hincrby"] = &RedisCmdMeta{Name: "hincrby", Arity: 4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hincrbyfloat"] = &RedisCmdMeta{Name: "hincrbyfloat", Arity: 4, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["hdel"] = &RedisCmdMeta{Name: "hdel", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hlen"] = &RedisCmdMeta{Name: "hlen", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hstrlen"] = &RedisCmdMeta{Name: "hstrlen", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hkeys"] = &RedisCmdMeta{Name: "hkeys", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hvals"] = &RedisCmdMeta{Name: "hvals", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hgetall"] = &RedisCmdMeta{Name: "hgetall", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hexists"] = &RedisCmdMeta{Name: "hexists", Arity: 3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["hrandfield"] = &RedisCmdMeta{Name: "hrandfield", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["hscan"] = &RedisCmdMeta{Name: "hscan", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["incrby"] = &RedisCmdMeta{Name: "incrby", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["decrby"] = &RedisCmdMeta{Name: "decrby", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["incrbyfloat"] = &RedisCmdMeta{Name: "incrbyfloat", Arity: 3, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["getset"] = &RedisCmdMeta{Name: "getset", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["mset"] = &RedisCmdMeta{Name: "mset", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 2}
		RedisCommandTable["msetnx"] = &RedisCmdMeta{Name: "msetnx", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 2}
		RedisCommandTable["randomkey"] = &RedisCmdMeta{Name: "randomkey", Arity: 1, Sflags: readOnlyFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["select"] = &RedisCmdMeta{Name: "select", Arity: 2, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["swapdb"] = &RedisCmdMeta{Name: "swapdb", Arity: 3, Sflags: writeFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["move"] = &RedisCmdMeta{Name: "move", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["copy"] = &RedisCmdMeta{Name: "copy", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["rename"] = &RedisCmdMeta{Name: "rename", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["renamenx"] = &RedisCmdMeta{Name: "renamenx", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["expire"] = &RedisCmdMeta{Name: "expire", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["expireat"] = &RedisCmdMeta{Name: "expireat", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["pexpire"] = &RedisCmdMeta{Name: "pexpire", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["pexpireat"] = &RedisCmdMeta{Name: "pexpireat", Arity: 3, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["keys"] = &RedisCmdMeta{Name: "keys", Arity: 2, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["scan"] = &RedisCmdMeta{Name: "scan", Arity: -2, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["dbsize"] = &RedisCmdMeta{Name: "dbsize", Arity: 1, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["auth"] = &RedisCmdMeta{Name: "auth", Arity: -2, Sflags: readOnlyFlag + "|" + adminFlag,
			FirstKey: 0, LastKey: 0, KeyStep: 0}
		RedisCommandTable["ping"] = &RedisCmdMeta{Name: "ping", Arity: -1, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["echo"] = &RedisCmdMeta{Name: "echo", Arity: 2, Sflags: readOnlyFlag + "|" + adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["save"] = &RedisCmdMeta{Name: "save", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["bgsave"] = &RedisCmdMeta{Name: "bgsave", Arity: -1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["bgrewriteaof"] = &RedisCmdMeta{Name: "bgrewriteaof", Arity: 1, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["shutdown"] = &RedisCmdMeta{Name: "shutdown", Arity: -1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["lastsave"] = &RedisCmdMeta{Name: "lastsave", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["type"] = &RedisCmdMeta{Name: "type", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["multi"] = &RedisCmdMeta{Name: "multi", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["exec"] = &RedisCmdMeta{Name: "exec", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["discard"] = &RedisCmdMeta{Name: "discard", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["sync"] = &RedisCmdMeta{Name: "sync", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["psync"] = &RedisCmdMeta{Name: "psync", Arity: -3, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["replconf"] = &RedisCmdMeta{Name: "replconf", Arity: -1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["flushdb"] = &RedisCmdMeta{Name: "flushdb", Arity: -1, Sflags: writeFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["cleandb"] = &RedisCmdMeta{Name: "cleandb", Arity: -1, Sflags: writeFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["flushall"] = &RedisCmdMeta{Name: "flushall", Arity: -1, Sflags: writeFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["cleanall"] = &RedisCmdMeta{Name: "cleanall", Arity: -1, Sflags: writeFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["sort"] = &RedisCmdMeta{Name: "sort", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["info"] = &RedisCmdMeta{Name: "info", Arity: -1, Sflags: readOnlyFlag + "|" + adminFlag,
			FirstKey: 0, LastKey: 0, KeyStep: 0}
		RedisCommandTable["monitor"] = &RedisCmdMeta{Name: "monitor", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["ttl"] = &RedisCmdMeta{Name: "ttl", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["touch"] = &RedisCmdMeta{Name: "touch", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["pttl"] = &RedisCmdMeta{Name: "pttl", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["expiretime"] = &RedisCmdMeta{Name: "expiretime", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["pexpiretime"] = &RedisCmdMeta{Name: "pexpiretime", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["persist"] = &RedisCmdMeta{Name: "persist", Arity: 2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["slaveof"] = &RedisCmdMeta{Name: "slaveof", Arity: 3, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["replicaof"] = &RedisCmdMeta{Name: "replicaof", Arity: 3, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["role"] = &RedisCmdMeta{Name: "role", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["debug"] = &RedisCmdMeta{Name: "debug", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["config"] = &RedisCmdMeta{Name: "config", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["confxx"] = &RedisCmdMeta{Name: "confxx", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["subscribe"] = &RedisCmdMeta{Name: "subscribe", Arity: -2, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["unsubscribe"] = &RedisCmdMeta{Name: "unsubscribe", Arity: -1, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["psubscribe"] = &RedisCmdMeta{Name: "psubscribe", Arity: -2, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["punsubscribe"] = &RedisCmdMeta{Name: "punsubscribe", Arity: -1, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["publish"] = &RedisCmdMeta{Name: "publish", Arity: 3, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["pubsub"] = &RedisCmdMeta{Name: "pubsub", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["watch"] = &RedisCmdMeta{Name: "watch", Arity: -2, Sflags: adminFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["unwatch"] = &RedisCmdMeta{Name: "unwatch", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["cluster"] = &RedisCmdMeta{Name: "cluster", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["restore"] = &RedisCmdMeta{Name: "restore", Arity: -4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["restore-asking"] = &RedisCmdMeta{Name: "restore-asking", Arity: -4, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["migrate"] = &RedisCmdMeta{Name: "migrate", Arity: -6, Sflags: writeFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["asking"] = &RedisCmdMeta{Name: "asking", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["readonly"] = &RedisCmdMeta{Name: "readonly", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["readwrite"] = &RedisCmdMeta{Name: "readwrite", Arity: 1, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["dump"] = &RedisCmdMeta{Name: "dump", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["object"] = &RedisCmdMeta{Name: "object", Arity: -2, Sflags: readOnlyFlag, FirstKey: 2, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["memory"] = &RedisCmdMeta{Name: "memory", Arity: -2, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["client"] = &RedisCmdMeta{Name: "client", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["hello"] = &RedisCmdMeta{Name: "hello", Arity: -1, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["eval"] = &RedisCmdMeta{Name: "eval", Arity: -3, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["eval_ro"] = &RedisCmdMeta{Name: "eval_ro", Arity: -3, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["evalsha"] = &RedisCmdMeta{Name: "evalsha", Arity: -3, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["evalsha_ro"] = &RedisCmdMeta{Name: "evalsha_ro", Arity: -3, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["slowlog"] = &RedisCmdMeta{Name: "slowlog", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["script"] = &RedisCmdMeta{Name: "script", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["time"] = &RedisCmdMeta{Name: "time", Arity: 1, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["bitop"] = &RedisCmdMeta{Name: "bitop", Arity: -4, Sflags: writeFlag, FirstKey: 2, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["bitcount"] = &RedisCmdMeta{Name: "bitcount", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["bitpos"] = &RedisCmdMeta{Name: "bitpos", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["wait"] = &RedisCmdMeta{Name: "wait", Arity: 3, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["command"] = &RedisCmdMeta{Name: "command", Arity: -1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["geoadd"] = &RedisCmdMeta{Name: "geoadd", Arity: -5, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["georadius"] = &RedisCmdMeta{Name: "georadius", Arity: -6, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["georadius_ro"] = &RedisCmdMeta{Name: "georadius_ro", Arity: -6, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["georadiusbymember"] = &RedisCmdMeta{Name: "georadiusbymember", Arity: -5, Sflags: writeFlag,
			FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["georadiusbymember_ro"] = &RedisCmdMeta{Name: "georadiusbymember_ro", Arity: -5,
			Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1, KeyStep: 1}
		RedisCommandTable["geohash"] = &RedisCmdMeta{Name: "geohash", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["geopos"] = &RedisCmdMeta{Name: "geopos", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["geodist"] = &RedisCmdMeta{Name: "geodist", Arity: -4, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["geosearch"] = &RedisCmdMeta{Name: "geosearch", Arity: -7, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["geosearchstore"] = &RedisCmdMeta{Name: "geosearchstore", Arity: -8, Sflags: writeFlag, FirstKey: 1,
			LastKey: 2, KeyStep: 1}
		RedisCommandTable["pfselftest"] = &RedisCmdMeta{Name: "pfselftest", Arity: 1, Sflags: adminFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["pfadd"] = &RedisCmdMeta{Name: "pfadd", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["pfcount"] = &RedisCmdMeta{Name: "pfcount", Arity: -2, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: -1, KeyStep: 1}
		RedisCommandTable["pfmerge"] = &RedisCmdMeta{Name: "pfmerge", Arity: -2, Sflags: writeFlag, FirstKey: 1, LastKey: -1,
			KeyStep: 1}
		RedisCommandTable["pfdebug"] = &RedisCmdMeta{Name: "pfdebug", Arity: -3, Sflags: adminFlag, FirstKey: 2, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["xadd"] = &RedisCmdMeta{Name: "xadd", Arity: -5, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["xrange"] = &RedisCmdMeta{Name: "xrange", Arity: -4, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["xrevrange"] = &RedisCmdMeta{Name: "xrevrange", Arity: -4, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["xlen"] = &RedisCmdMeta{Name: "xlen", Arity: 2, Sflags: readOnlyFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["xread"] = &RedisCmdMeta{Name: "xread", Arity: -4, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["xreadgroup"] = &RedisCmdMeta{Name: "xreadgroup", Arity: -7, Sflags: writeFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["xgroup"] = &RedisCmdMeta{Name: "xgroup", Arity: -2, Sflags: writeFlag, FirstKey: 2, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["xsetid"] = &RedisCmdMeta{Name: "xsetid", Arity: 3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["xack"] = &RedisCmdMeta{Name: "xack", Arity: -4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["xpending"] = &RedisCmdMeta{Name: "xpending", Arity: -3, Sflags: readOnlyFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["xclaim"] = &RedisCmdMeta{Name: "xclaim", Arity: -6, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["xautoclaim"] = &RedisCmdMeta{Name: "xautoclaim", Arity: -6, Sflags: writeFlag, FirstKey: 1,
			LastKey: 1, KeyStep: 1}
		RedisCommandTable["xinfo"] = &RedisCmdMeta{Name: "xinfo", Arity: -2, Sflags: readOnlyFlag, FirstKey: 2, LastKey: 2,
			KeyStep: 1}
		RedisCommandTable["xdel"] = &RedisCmdMeta{Name: "xdel", Arity: -3, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["xtrim"] = &RedisCmdMeta{Name: "xtrim", Arity: -4, Sflags: writeFlag, FirstKey: 1, LastKey: 1,
			KeyStep: 1}
		RedisCommandTable["latency"] = &RedisCmdMeta{Name: "latency", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["lolwut"] = &RedisCmdMeta{Name: "lolwut", Arity: -1, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["acl"] = &RedisCmdMeta{Name: "acl", Arity: -2, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["stralgo"] = &RedisCmdMeta{Name: "stralgo", Arity: -2, Sflags: readOnlyFlag, FirstKey: 0,
			LastKey: 0, KeyStep: 0}
		RedisCommandTable["reset"] = &RedisCmdMeta{Name: "reset", Arity: 1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["failover"] = &RedisCmdMeta{Name: "failover", Arity: -1, Sflags: adminFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
		RedisCommandTable["select"] = &RedisCmdMeta{Name: "select", Arity: 1, Sflags: readOnlyFlag, FirstKey: 0, LastKey: 0,
			KeyStep: 0}
	})
}
