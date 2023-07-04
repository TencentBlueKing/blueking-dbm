package atomproxy

import (
	"crypto/md5"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net"
	"sort"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

/*
	校验 所有 proxy 的后端，适用于切换后，扩缩容等步骤检查使用
	{
		"instances":[{"ip":"","port":50000,"admin_port":51000}]
	}
*/

// ProxyInstances TODO
type ProxyInstances struct {
	IP        string `json:"ip" validate:"required"`
	Port      int    `json:"port" validate:"required"`
	AdminPort int    `json:"admin_port"`
}

// ProxyCheckParam TODO
type ProxyCheckParam struct {
	Instances []ProxyInstances
}

// TwemproxyCheckBackends   原子任务
type TwemproxyCheckBackends struct {
	runtime *jobruntime.JobGenericRuntime
	params  ProxyCheckParam
}

// NewTwemproxySceneCheckBackends TODO
// NewTwemproxyOperate new
func NewTwemproxySceneCheckBackends() jobruntime.JobRunner {
	return &TwemproxyCheckBackends{}
}

// Init 初始化
func (job *TwemproxyCheckBackends) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error(
				"TwemproxyCheckBackends Init params validate failed InvalidValidationError,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("TwemproxyCheckBackends Init params validate failed ValidationErrors,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *TwemproxyCheckBackends) Name() string {
	return "twemproxy_check_backends"
}

// Run 执行
func (job *TwemproxyCheckBackends) Run() (err error) {
	md5s := map[string][]string{}
	for idx, p := range job.params.Instances {
		md5Val := job.getTwemproxyMd5(fmt.Sprintf("%s:%d", p.IP, p.Port+1000))
		if _, ok := md5s[md5Val]; !ok {
			md5s[md5Val] = []string{}
		}
		md5s[md5Val] = append(md5s[md5Val], p.IP)
		job.runtime.Logger.Info(fmt.Sprintf("get {%s} nosqlproxy servers md5 %d:%s", p.IP, idx, md5Val))
	}

	if len(md5s) > 1 {
		x, _ := json.Marshal(md5s)
		return fmt.Errorf("some proxy failed for servers:{%s}", x)
	}

	job.runtime.Logger.Info(fmt.Sprintf("all twemproxy %+v got same nosqlproxy servers md5 %+v", job.params, md5s))
	return nil
}

// Retry times
func (job *TwemproxyCheckBackends) Retry() uint {
	return 2
}

// Rollback rollback
func (job *TwemproxyCheckBackends) Rollback() error {
	return nil
}

func (job *TwemproxyCheckBackends) getTwemproxyMd5(addr string) string {
	// 建立一个链接（Dial拨号）
	conn, err := net.DialTimeout("tcp", addr, time.Second*2)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("dial failed, {%s} err:%v\n", addr, err))
		return fmt.Sprintf("Dail{%s}Failed:%+v", addr, err)
	}

	// 写入数据
	_, err = io.WriteString(conn, "get nosqlproxy servers")
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("wirte string failed, err:%v\n", err))
		return fmt.Sprintf("Write{%s}Failed:%+v", addr, err)
	}

	// 读取返回的数据
	rsp, err := ioutil.ReadAll(conn)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("read string failed, err:%v\n", err))
		return fmt.Sprintf("Read{%s}Failed:%+v", addr, err)
	}
	// 1.1.x.a:30000 tgalive 0-17499 1
	segs := []string{}
	for _, seg := range strings.Split(strings.TrimRight(string(rsp), "\n"), "\n") {
		segInfo := strings.Split(seg, " ")
		if len(segInfo) != 4 {
			return fmt.Sprintf("GetServersFailed:%s|[%d:%+v]{%s}", addr, len(segInfo), segInfo, rsp)
		}
		segs = append(segs, fmt.Sprintf("%s|%s", segInfo[0], segInfo[2]))
	}
	sort.Strings(segs)

	data, _ := json.Marshal(segs)
	// 计算MD5
	md5er := md5.New()
	has := md5er.Sum(data)
	job.runtime.Logger.Info(fmt.Sprintf("proxy {%s} has backends servers md5:%s:%s", addr, has, data))
	return fmt.Sprintf("%x", has) // 将[]byte转成16进制
}
