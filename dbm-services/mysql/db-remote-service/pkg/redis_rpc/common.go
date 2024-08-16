package redis_rpc

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/pkg/errors"
)

// MAX TODO
const MAX = 1 * 1024 * 1024

// MaxMemberSize 允许查询的最大成员数量
const MaxMemberSize = 1000

// MaxStringLength 允许查询的最大String长度
const MaxStringLength = 1 * 1024 * 1024

var ctx = context.Background()

// RedisQueryParams redis请求参数
type RedisQueryParams struct {
	Addresses []string `json:"addresses"`
	DbNum     int      `json:"db_num"`
	Password  string   `json:"password"`
	Command   string   `json:"command"`
	// ClientType webconsole or 其它任何值。 当这个值为webconsole时，调用redis-cli执行命令.
	ClientType string `json:"client_type"`
	// Raw 只对ClientType为webconsole时生效. 为redis-cli添加--raw参数 raw模式下，能返回中文. 默认为false
	Raw bool `json:"raw,omitempty"`
}

// StringWithoutPasswd 打印参数，不打印密码
func (param *RedisQueryParams) StringWithoutPasswd() string {
	return fmt.Sprintf("{addresses:%+v,db_num:%d,command:%s,password:xxxx}", param.Addresses, param.DbNum, param.Command)
}

// CmdResult TODO
// ==== 返回
type CmdResult struct {
	Address string      `json:"address"`
	Result  interface{} `json:"result"`
}

// RedisQueryResp TODO
type RedisQueryResp struct {
	Code     int         `json:"code"`
	Data     []CmdResult `json:"data"`
	ErrorMsg string      `json:"error_msg"`
}

// SendResponse TODO
func SendResponse(c *gin.Context, code int, errMsg string, data []CmdResult) {
	c.JSON(http.StatusOK, RedisQueryResp{
		Code:     code,
		ErrorMsg: errMsg,
		Data:     data,
	})
}

// FormatName 返回格式化后的执行命令
func FormatName(msg string) (string, error) {
	stringMsg := strings.TrimSpace(msg)
	if len(stringMsg) == 0 {
		return "", fmt.Errorf("bad input: msg length too short")
	}
	stringMsg = strings.ReplaceAll(stringMsg, `"`, ``)
	stringMsg = strings.ReplaceAll(stringMsg, `''`, ``)

	// 去除连续空格
	pattern := regexp.MustCompile(`\s+`)
	stringMsg = pattern.ReplaceAllString(stringMsg, " ")

	return stringMsg, nil
}

// DoRedisCmdNew 执行redis命令 by go driver
func DoRedisCmdNew(address, redisPass, cmd string, dbNum int) (ret string, err error) {
	var strBuilder strings.Builder
	cli, err := NewRedisClientWithTimeout(address, redisPass, dbNum, time.Second*2)
	if err != nil {
		return
	}
	defer cli.Close()
	cmdlist := strings.Fields(cmd)
	cmdRet, err := cli.DoCommand(cmdlist, dbNum)
	if err != nil {
		return
	}
	switch v := cmdRet.(type) {
	case int64:
		strBuilder.WriteString(strconv.FormatInt(v, 10))
	case string:
		strBuilder.WriteString(cmdRet.(string))
	case []string:
		list01 := cmdRet.([]string)
		for _, item01 := range list01 {
			strBuilder.WriteString(item01 + "\n")
		}
	case []interface{}:
		list02 := cmdRet.([]interface{})
		for _, item01 := range list02 {
			strBuilder.WriteString(fmt.Sprintf("%v", item01) + "\n")
		}
	default:
		slog.Info(fmt.Sprintf("ExecuteCmd unknown result type,cmds:'%s',retType:%s,addr:%s", cmd, v, address))
		byte01, _ := json.Marshal(cmdRet)
		strBuilder.WriteString(string(byte01))
	}
	ret = strBuilder.String()
	return
}

// TcpClient01 向tcp端口发送一条指令 并接受 返回
// 模仿netcat
func TcpClient01(addr01, cmd string) (ret string, err error) {
	client, err := net.Dial("tcp", addr01)
	if err != nil {
		err = fmt.Errorf("net.Dial fail,err:%v", err)
		return "", err
	}
	defer client.Close()
	_, err = client.Write([]byte(cmd))
	if err != nil {
		err = fmt.Errorf("tcp client.Write fail,err:%v,addr:%s,command:%s", err, addr01, cmd)
		return "", err
	}
	buf := make([]byte, 1024)
	for {
		readCnt, err := client.Read(buf)
		if err != nil {
			if err == io.EOF {
				return ret, nil
			}
			err = fmt.Errorf("tcp client.read fail,err:%v,addr:%s,command:%s", err, addr01, cmd)
			return "", err
		}
		ret = ret + string(buf[:readCnt])
	}
}

// GetValueSize 分析cmdLine，返回它的valueSize
// 返回值说明，出现各种 error 以及非 read 指令，返回 -1；对于非受限的 read 指令，返回0；对于受限的 read 指令，返回其value_size
func GetValueSize(address, pass string, cmdLine string, dbNum int) (int, bool, error) {
	rdb := redis.NewClient(&redis.Options{
		Addr:     address,
		Password: pass,
		DB:       dbNum, // use default DB
	})

	// 检测是否连接到redis数据库
	pong, err := rdb.Ping(ctx).Result()
	if err != nil {
		return -1, false, errors.Wrap(err, "connect redis failed")
	}
	if pong != "PONG" {
		return -1, false, fmt.Errorf("connect redis failed")
	}
	return getValue(rdb, cmdLine)
}

// getValue 是否超过了最大允许长度，错误内容。 超过返回Error
func getValue(rdb *redis.Client, cmdLine string) (int, bool, error) {
	stringMsg := strings.TrimSpace(cmdLine)
	inputs := strings.Fields(stringMsg)
	// 先得到命令的名称，其余参数分情况处理
	command := inputs[0]
	commandLc := treatString(strings.ToLower(command))
	keys, err := RedisCommandTable[commandLc].GetKeys(cmdLine)
	if err != nil {
		return -1, false, err
	}
	if len(keys) == 0 {
		if commandLc == "scan" {
			return PrecheckScanCmd(rdb, commandLc, inputs)
		} else {
			return 0, true, nil
		}
	}
	key := keys[0]

	if commandLc == "get" {
		// redis_parse.go 中标注了各种命令所需的最小参数个数
		len, err := rdb.StrLen(ctx, key).Result()
		if err != nil {
			return -1, true, fmt.Errorf("check your redis command, strlen cmd error: " + err.Error())
		}
		return int(len), true, checkStringLength(int(len))
	} else if commandLc == "mget" { // 有多个key
		if len(inputs) < 2 {
			return -1, true, fmt.Errorf("incomplete argvs")
		}
		totalLen := 0
		for i := 1; i < len(inputs); i++ { // 检索所有的 key 的长度，加起来再比较
			len, err := rdb.StrLen(ctx, inputs[i]).Result()
			if err != nil {
				return -1, true, fmt.Errorf("check your redis command, strlen cmd error: " + err.Error())
			}
			totalLen += int(len)
		}
		return totalLen, true, checkStringLength(totalLen)
	} else if commandLc == "hgetall" || commandLc == "hkeys" || commandLc == "hvals" {
		return PrecheckHashKeysCmd(rdb, commandLc, inputs)
	} else if commandLc == "lrange" {
		PrecheckListKeysCmd(rdb, commandLc, inputs)
	} else if commandLc == "smembers" || commandLc == "srandmember" {
		return PrecheckSetKeysCmd(rdb, commandLc, inputs)
	} else if commandLc == "zrangebyscore" || commandLc == "zrevrangebyscore" || commandLc == "zrangebylex" ||
		commandLc == "zrevrangebylex" {
		return PrecheckZsetKeysCmd(rdb, commandLc, inputs)
	} else if commandLc == "hscan" || commandLc == "sscan" || commandLc == "zscan" {
		return PrecheckScanCmd(rdb, commandLc, inputs)
	}
	// 非受限的 read 指令
	return 0, false, nil
}

// treatString 删除' "
func treatString(str string) string {
	str = strings.Trim(str, `"`)
	str = strings.Trim(str, `'`)
	return str
}

// treatLRangeArgv LRange 的偏移量可以是负数，为方便计算，将其调整
func treatLRangeArgv(start int, end int, list_len int) (int, int) {
	if start < 0 {
		if start*(-1) > list_len { // 一律算作从头开始取
			start = 0
		} else {
			start = list_len - start*(-1) // 否则，偏移量是负数代表从尾部计数，为方便计算，将其转化为从头部计数的正数
		}
	}
	if end < 0 {
		if end*(-1) > list_len { // lrange 一定会返回空列表，为方便计算直接将其置为-1
			end = -1
		} else {
			end = list_len - end*(-1)
		}
	}
	if end >= list_len { // 一律算作取到尾部
		end = list_len - 1
	}
	return start, end
}

// treatSRandMemberCount count参数也有多种情况
func treatSRandMemberCount(count int, set_len int) int {
	if count < 0 {
		count = count * (-1)
		return count
	} else {
		if count > set_len {
			return set_len
		} else {
			return count
		}
	}
}

func checkStringLength(len int) error {
	if len > MaxStringLength {
		return fmt.Errorf("value length %d is too big, it must be less than 1M", len)
	} else {
		return nil
	}
}

func checkLength(len int) error {
	if len > MaxMemberSize {
		return fmt.Errorf("there are too many member returned, it must be less than 1000. e.g" +
			"[hzs]scan $cursor [match pattern] count 1000")
	} else {
		return nil
	}
}

// PrecheckHashKeysCmd 预检查hash类型key相关命令
func PrecheckHashKeysCmd(rdb *redis.Client, commandLc string, inputs []string) (int, bool, error) {
	if len(inputs) < 2 {
		return -1, false, fmt.Errorf("incomplete argvs")
	}
	key := inputs[1]
	len, err := rdb.HLen(ctx, key).Result()
	if err != nil {
		return -1, false, fmt.Errorf("check your redis command, hlen cmd error: " + err.Error())
	}
	return int(len), false, checkLength(int(len))
}

// PrecheckListKeysCmd 预检查list类型key相关命令
func PrecheckListKeysCmd(rdb *redis.Client, commandLc string, inputs []string) (int, bool, error) {
	if len(inputs) < 4 {
		return -1, false, fmt.Errorf("incomplete argvs")
	}
	key := inputs[1]
	start, err := strconv.Atoi(inputs[2])
	if err != nil {
		return -1, false, err
	}
	end, err := strconv.Atoi(inputs[3])
	if err != nil {
		return -1, false, err
	}
	listLen, err := rdb.LLen(ctx, key).Result()
	if err != nil {
		return -1, false, fmt.Errorf("check your redis command, llen cmd error: " + err.Error())
	}
	start, end = treatLRangeArgv(start, end, int(listLen))
	len := end - start + 1
	if len < 0 {
		return -1, false, nil
	}
	return int(len), false, checkLength(int(len))
}

// PrecheckSetKeysCmd 预检查set类型key相关命令
func PrecheckSetKeysCmd(rdb *redis.Client, commandLc string, inputs []string) (int, bool, error) {
	if len(inputs) < 2 {
		return -1, false, fmt.Errorf("incomplete argvs")
	}
	if commandLc == "smembers" {
		key := inputs[1]
		set_len, err := rdb.SCard(ctx, key).Result()
		if err != nil {
			return -1, false, fmt.Errorf("check your redis command, scard cmd error: " + err.Error())
		}
		return int(set_len), false, checkLength(int(set_len))
	} else if commandLc == "srandmember" {
		if len(inputs) == 2 { // 随机返回一个成员
			return 1, false, nil
		} else if len(inputs) == 3 { // 有 count 参数
			count, err := strconv.Atoi(inputs[2])
			if err != nil {
				return -1, false, fmt.Errorf("check your count argv: " + err.Error())
			}
			key := inputs[1]
			set_len, err := rdb.SCard(ctx, key).Result()
			if err != nil {
				return -1, false, fmt.Errorf("check your redis command, scard cmd error: " + err.Error())
			}
			count = treatSRandMemberCount(count, int(set_len))
			return count, false, checkLength(count)
		}
	}
	return 0, false, nil
}

// PrecheckZsetKeysCmd 预检查zset命令
func PrecheckZsetKeysCmd(rdb *redis.Client, commandLc string, inputs []string) (int, bool, error) {
	// ZRANGEBYSCORE key min max [WITHSCORES] [LIMIT offset count]
	// ZRANGEBYLEX key min max [LIMIT offset count]
	haveLimit := false
	var count int

	for i, argv := range inputs { // 循环检测是否有 LIMIT 关键字
		argvLow := strings.ToLower(argv)
		if argvLow != "limit" {
			continue
		}
		if len(inputs) < i+3 { // [LIMIT offset count]
			return -1, false, fmt.Errorf("incomplete argvs")
		}
		if cnt, err := strconv.Atoi(inputs[i+2]); err != nil {
			return -1, false, fmt.Errorf("check your count argv: " + err.Error())
		} else {
			haveLimit = true
			count = cnt
		}
		break
	}

	if haveLimit {
		return count, false, checkLength(count)
	}

	// 没有提供[Limit offset count]参数
	if len(inputs) < 4 {
		return -1, false, fmt.Errorf("incomplete argvs")
	}
	key := inputs[1]
	min := inputs[2]
	max := inputs[3]
	if commandLc == "zrevrangebyscore" || commandLc == "zrevrangebylex" {
		min, max = max, min
	}
	if commandLc == "zrangebyscore" || commandLc == "zrevrangebyscore" {
		len, err := rdb.ZCount(ctx, key, min, max).Result()
		if err != nil {
			return -1, false, fmt.Errorf("check your redis command, zcount cmd error: " + err.Error())
		}
		return int(len), false, checkLength(int(len))
	} else {
		len, err := rdb.ZLexCount(ctx, key, min, max).Result()
		if err != nil {
			return -1, false, fmt.Errorf("check your redis command, zlexcount cmd error: " + err.Error())
		}
		return int(len), false, checkLength(int(len))
	}
}

// PrecheckScanCmd 预检查scan命令
func PrecheckScanCmd(rdb *redis.Client, commandLc string, inputs []string) (int, bool, error) {
	haveCount := false
	var count int
	for i, argv := range inputs {
		argvLow := strings.ToLower(argv)
		if argvLow == "count" {
			if len(inputs) < i+2 { // [COUNT count]
				return -1, false, fmt.Errorf("incomplete argvs")
			}
			cnt, err := strconv.Atoi(inputs[i+1])
			if err != nil {
				return -1, false, fmt.Errorf("check your count argv: " + err.Error())
			} else {
				haveCount = true
				count = cnt
			}
		}
	}
	if haveCount {
		return count, false, checkLength(count)
	} else {
		return -1, false, fmt.Errorf("require count arg")
	}
}
