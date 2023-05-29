package redistest

import (
	"fmt"
	"strconv"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"

	"github.com/go-redis/redis/v8"
)

// CommandTest 命令测试
type CommandTest struct {
	IP       string               `json:"ip"`
	Port     int                  `json:"port"`
	Password string               `json:"password"`
	DbType   string               `json:"db_type"`
	Database int                  `json:"database"`
	Err      error                `json:"-"`
	client   *myredis.RedisClient `json:"-"`
}

// NewCommandTest new
func NewCommandTest(ip string, port int, password, dbType string, database int) (ret *CommandTest, err error) {
	ret = &CommandTest{
		IP:       ip,
		Port:     port,
		Password: password,
		DbType:   dbType,
		Database: database,
	}
	addr := ip + ":" + strconv.Itoa(port)
	ret.client, err = myredis.NewRedisClient(addr, password, database, dbType)
	return
}

// StringTest string命令测试
func (test *CommandTest) StringTest() {
	var vals []interface{}
	var k01, v01 string
	for i := 0; i < 100; i++ {
		vals = make([]interface{}, 0, 2)
		k01 = "test_string_" + strconv.Itoa(i)
		v01 = "v" + strconv.Itoa(i)
		vals = append(vals, k01, v01)
		_, test.Err = test.client.Mset(vals)
		if test.Err != nil {
			return
		}
	}
}

// KeyTypeCheck key 过期时间
// 说明：集群写入 400 : *string* ,*hash*,*list*,*set*, 各100个key,提取&删除 *hash* 和 *set* 共200
// 所以 *hash*  *set* ttl的值为 none; *string* 的ttl 为string ；*list*, 的ttl 为list
func (test *CommandTest) KeyTypeCheck() (err error) {
	var k01, ttl string
	for i := 0; i < 100; i++ {
		k01 = "test_string_" + strconv.Itoa(i)
		ttl, test.Err = test.client.KeyType(k01)
		if test.Err != nil {
			return test.Err
		}
		if ttl != "string" {
			test.Err = fmt.Errorf("%s ttl:%s,不为string ,key被意外删除", k01, ttl)
			return test.Err
		}

		k01 = "test_hash_" + strconv.Itoa(i)
		ttl, test.Err = test.client.KeyType(k01)
		if test.Err != nil {
			return test.Err
		}
		if ttl != "none" {
			test.Err = fmt.Errorf("%s ttl:%s,不为none ,key没有删除成功", k01, ttl)
			return test.Err
		}

		k01 = "test_set_" + strconv.Itoa(i)
		ttl, test.Err = test.client.KeyType(k01)
		if test.Err != nil {
			return test.Err
		}

		if ttl != "none" {
			test.Err = fmt.Errorf("%s ttl:%s,不为none ,key没有删除成功", k01, ttl)
			return test.Err
		}

		k01 = "test_list_" + strconv.Itoa(i)
		ttl, test.Err = test.client.KeyType(k01)
		if test.Err != nil {
			return test.Err
		}
		if ttl != "list" {
			test.Err = fmt.Errorf("%s ttl:%s,不为list ,key被意外删除", k01, ttl)
			return test.Err
		}

	}
	return nil
}

// HashTest hash命令测试
func (test *CommandTest) HashTest() {
	var vals []interface{}
	var kname string
	for i := 0; i < 100; i++ {
		kname = "test_hash_" + strconv.Itoa(i)
		vals = make([]interface{}, 0, 4)
		vals = append(vals, "k1", "v1", "k2", "v2")
		_, test.Err = test.client.Hmset(kname, vals)
		if test.Err != nil {
			return
		}
	}
}

// ListTest list命令测试
func (test *CommandTest) ListTest() {
	var vals []interface{}
	var kname string
	for i := 0; i < 100; i++ {
		kname = "test_list_" + strconv.Itoa(i)
		vals = make([]interface{}, 0, 2)
		vals = append(vals, "v1", "v2")
		_, test.Err = test.client.Rpush(kname, vals)
		if test.Err != nil {
			return
		}
	}
}

// SetTest set命令测试
func (test *CommandTest) SetTest() {
	var vals []interface{}
	var kname string
	for i := 0; i < 100; i++ {
		kname = "test_set_" + strconv.Itoa(i)
		vals = make([]interface{}, 0, 4)
		vals = append(vals, "v1", "v1", "v2", "v2")
		_, test.Err = test.client.Sadd(kname, vals)
		if test.Err != nil {
			return
		}
	}
}

// ZsetTest Zset命令测试
func (test *CommandTest) ZsetTest() {
	var kname string
	var members []*redis.Z
	for i := 0; i < 100; i++ {
		kname = "test_zset_" + strconv.Itoa(i)
		members = []*redis.Z{
			{
				Score:  10,
				Member: "m01",
			}, {
				Score:  20,
				Member: "m02",
			},
		}
		_, test.Err = test.client.Zadd(kname, members)
		if test.Err != nil {
			return
		}
	}
}

// DelKeysCheck check key命令测试
// 说明：集群写入 400 : *string* ,*hash*,*list*,*set*, 各100个key,提取&删除 *hash* 和 *set* 共200
func (test *CommandTest) DelKeysCheck() (err error) {
	var stringKeys []string
	var hashKeys []string
	var listKeys []string
	var setKeys []string
	stringKeys, _, test.Err = test.client.Scan("*string*", 0, 400)
	msg := fmt.Sprintf("redis scan result stringKeys: %v", stringKeys)
	fmt.Println(msg)
	hashKeys, _, test.Err = test.client.Scan("*hash*", 0, 400)
	msg = fmt.Sprintf("redis scan result  hashKeys: %v", hashKeys)
	fmt.Println(msg)
	listKeys, _, test.Err = test.client.Scan("*list*", 0, 400)
	msg = fmt.Sprintf("redis scan result listKeys: %v", listKeys)
	fmt.Println(msg)
	setKeys, _, test.Err = test.client.Scan("*set*", 0, 400)
	msg = fmt.Sprintf("redis scan result setKeys:%v", setKeys)
	fmt.Println(msg)
	if test.Err != nil {
		return test.Err
	}
	if stringKeys == nil || listKeys == nil || len(stringKeys) == 0 || len(listKeys) == 0 {
		test.Err = fmt.Errorf("删除了不该删的数据,请检查写入数据是否有更改或者是否改动提取key部分代码:说明:集群共写入400个key(这里只校验一个节点数据) : " +
			" *string* ,*hash*,*list*,*set*, 各100个key,提取&删除 *hash* 和 *set* 共200")
	}
	if len(hashKeys) != 0 || len(setKeys) != 0 {
		test.Err = fmt.Errorf("该删除的key没有删成功,请检查写入数据是否有更改或者是否改动提取key部分代码:说明:集群共写入400个key(这里只校验一个节点数据) :" +
			" *string* ,*hash*,*list*,*set*, 各100个key,提取&删除 *hash* 和 *set* 共200")
	}
	if test.Err != nil {
		return test.Err
	}
	fmt.Println("提取&删除key正则符合预期:删除*hash* 和 *set*; 保留*string* 和*list*")
	return nil
}

// FileDelKeysCheck check file delete key命令测试
// 说明：文件中包含 100个 *string* 匹配的key,实例中还剩下部分*list* 匹配的key
func (test *CommandTest) FileDelKeysCheck() (err error) {
	var stringKeys []string
	var listKeys []string
	stringKeys, _, test.Err = test.client.Scan("*string*", 0, 400)
	msg := fmt.Sprintf("FileDelKeysCheck redis scan result stringKeys: %v", stringKeys)
	fmt.Println(msg)

	listKeys, _, test.Err = test.client.Scan("*list*", 0, 400)
	msg = fmt.Sprintf("FileDelKeysCheck redis scan result listKeys: %v", listKeys)
	fmt.Println(msg)

	if test.Err != nil {
		return test.Err
	}
	if listKeys == nil || len(listKeys) == 0 {
		test.Err = fmt.Errorf("删除了不该删的数据,请检查写入数据是否有更改或者是否改动提取key部分代码:文件中包含 100个 *string* 匹配的key,还剩下部分*list* 匹配的key")
	}
	if len(stringKeys) != 0 || len(stringKeys) != 0 {
		test.Err = fmt.Errorf("该删除的key没有删成功,请检查写入数据是否有更改或者是否改动提取key部分代码:文件中包含 100个 *string* 匹配的key,还剩下部分*list* 匹配的key")
	}
	if test.Err != nil {
		return test.Err
	}
	fmt.Println("文件删除结果验证符合预期：删除*string*; 保留*list*")
	return nil
}

// FileDelKeyTypeCheck check file delete key命令测试
// 说明：文件中包含 100个 *string* 匹配的key(会被删除),实例中还剩下部分*list* 匹配的key
func (test *CommandTest) FileDelKeyTypeCheck() (err error) {
	var k01, ttl string
	for i := 0; i < 100; i++ {
		k01 = "test_string_" + strconv.Itoa(i)
		ttl, test.Err = test.client.KeyType(k01)
		if test.Err != nil {
			return test.Err
		}
		if ttl != "none" {
			test.Err = fmt.Errorf("%s ttl:%s,不为string ,key被意外删除", k01, ttl)
			return test.Err
		}

		k01 = "test_list_" + strconv.Itoa(i)
		ttl, test.Err = test.client.KeyType(k01)
		if test.Err != nil {
			return test.Err
		}
		if ttl != "list" {
			test.Err = fmt.Errorf("%s ttl:%s,不为list ,key被意外删除", k01, ttl)
			return test.Err
		}

	}
	return nil
}
