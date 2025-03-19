package mongodb_rpc

import (
	"dbm-services/mysql/db-remote-service/pkg/rpc_implement/mongodb_rpc/session"
	"fmt"
	"log/slog"
	"os"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

var (
	logger   *slog.Logger
	pool     *session.Pool // Not instantiated
	poolOnce sync.Once
)

func getPool() (*slog.Logger, *session.Pool) {
	// Create a new pool if it does not exist
	poolOnce.Do(func() {
		logger = slog.New(slog.NewJSONHandler(os.Stdout, nil))
		pool = session.NewPool(logger.With("service", "mongo_rpc"))
		go pool.CheckTimeout(60)
	})
	return logger, pool
}

// QueryParams redis请求参数
type QueryParams struct {
	ClusterId     int      `json:"cluster_id"`     // 集群id
	ClusterType   string   `json:"cluster_type"`   // 集群类型
	ClusterDomain string   `json:"cluster_domain"` // 集群名称
	Addresses     []string `json:"addresses"`      // ip:port列表
	SetName       string   `json:"set_name"`       // 如果是集群，指定为空
	UserName      string   `json:"username"`       // 用户名
	Password      string   `json:"password"`       // 密码  MongodbRepo().getPassword()
	Token         string   `json:"session"`        // session token, 一个随机字符串
	Command       string   `json:"command"`        // 命令. 例如: "db.stats()". 必须是一个完整的命令
	Timeout       int      `json:"timeout"`        // 超时时间，单位秒，预留参数，现在默认1分钟
	Version       string   `json:"version"`        // 版本号，如果 4.4 以上，会使用新的mongoshell
}

// StringWithoutPasswd 打印参数，不打印密码
func (param *QueryParams) StringWithoutPasswd() string {
	return fmt.Sprintf("{domain:%s,Addresses:%+v,token:%s,command:%s,user:%s password:len-%d}",
		param.ClusterDomain, param.Addresses, param.Token, param.Command, param.UserName, len(param.Password))
}

// GetUniqSessionToken 打印参数，不打印密码
func (param *QueryParams) GetUniqSessionToken() string {
	return fmt.Sprintf("%s_%s_%s", param.ClusterDomain, param.UserName, param.Token)
}

// MongoRPCEmbed redis 实现
type MongoRPCEmbed struct {
}

// NewMongoRPCEmbed new mongo rpc embed instance
func NewMongoRPCEmbed() *MongoRPCEmbed {
	return &MongoRPCEmbed{}
}

func parseQueryParams(c *gin.Context) (*QueryParams, error) {
	param := &QueryParams{}
	if err := c.BindJSON(param); err != nil {
		return nil, fmt.Errorf("bad param, bind json failed")
	}

	if len(param.Addresses) == 0 {
		return nil, fmt.Errorf("bad param, empty Addresses")
	}
	if len(param.Addresses[0]) == 0 {
		return nil, fmt.Errorf("bad param, empty Addresses")
	}

	if len(param.Token) == 0 {
		return nil, fmt.Errorf("bad param, empty token")
	}

	if len(param.UserName) == 0 {
		return nil, fmt.Errorf("bad param, empty UserName")
	}

	if len(param.Password) == 0 {
		return nil, fmt.Errorf("bad param, empty Password")
	}

	return param, nil
}

// DoCommand do command for mongo
func (r *MongoRPCEmbed) DoCommand(c *gin.Context) {
	// Get the session pool && logger
	_, myPool := getPool()

	param, err := parseQueryParams(c)
	if err != nil {
		NewRespHandle(c, nil, logger).SendError(err.Error())
		return
	}

	session := myPool.Add(param.Token)

	// Create a new response handler. with the request context and parameters
	resp := NewRespHandle(c, param, logger)

	// 同一个session只能同时运行一个命令，否则会出现输出混乱
	if false == session.RunningLock.TryLock() {
		resp.SendError(fmt.Sprintf("session %s is busy", param.Token))
		return
	}
	// 刷新最后运行时间。 用于超时检查
	session.LastRunTime = time.Now()
	defer session.RunningLock.Unlock()

	if !session.IsStopped() && len(param.Command) == 0 {
		resp.SendError(fmt.Sprintf("bad param, empty command"))
		return
	}

	// Start the session if it is not running
	err = session.Run(NewMongoShellFromParm(param))
	if err != nil {
		resp.SendError(err.Error())
		return
	}

	// Send the command to the session
	_, err = session.SendMsg([]byte(param.Command))
	logger.Info("send msg",
		slog.String("msg", param.Command),
		slog.String("token", param.Token),
		slog.Bool("success", err == nil))

	// Check if the command was sent successfully
	if err != nil {
		session.Stop()
		resp.SendError(err.Error())
		return
	}

	v, err := session.ReceiveMsg(15)
	if err != nil {
		logger.Error("read resp", slog.String("resp", string(v)))
		session.Stop()
		resp.SendError(err.Error())
		return
	} else {
		resp.SendResp(string(v), 0, "")
	}

}
