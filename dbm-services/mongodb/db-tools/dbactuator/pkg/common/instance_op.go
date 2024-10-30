package common

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/dbmon/pkg/linuxproc"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

// Instance Describe a mongodb instance
type Instance struct {
	IP            string `json:"ip"`
	Port          int    `json:"port"`
	AdminUsername string `json:"adminUsername"`
	AdminPassword string `json:"adminPassword"`
	InstanceType  string `json:"instanceType"` // mongos or shard or configsvr
}

func NewInstance(ip string, port int, user, pass, instanceType string) *Instance {
	return &Instance{
		IP:            ip,
		Port:          port,
		AdminUsername: user,
		AdminPassword: pass,
		InstanceType:  instanceType,
	}
}

// Connect 连接数据库
func (inst *Instance) Connect() (*mongo.Client, error) {
	return mymongo.NewMongoHost(
		inst.IP, strconv.Itoa(inst.Port), "admin",
		inst.AdminUsername, inst.AdminPassword, "", "").ConnectWithDirect(false)
}

// ConnectDirect 连接数据库Direct
func (inst *Instance) ConnectDirect() (*mongo.Client, error) {
	return mymongo.NewMongoHost(
		inst.IP, strconv.Itoa(inst.Port), "admin",
		inst.AdminUsername, inst.AdminPassword, "", "").ConnectWithDirect(true)
}

// WaitForConnectable 等待数据库连接成功
func (inst *Instance) WaitForConnectable(count int, waitTime time.Duration) (err error) {
	// wait for config server start
	for i := 0; i < count; i++ {
		if i > 0 {
			time.Sleep(waitTime * time.Second)
		}
		cli, err := inst.ConnectDirect()
		if err == nil {
			cli.Disconnect(context.Background())
			return nil
			break
		}
	}
	return nil
}

// Addr 返回地址
func (inst *Instance) Addr() string {
	return fmt.Sprintf("%s:%d", inst.IP, inst.Port)
}

// InstanceOp 对单个mongod/mongos进程作一些起停操作
type InstanceOp struct {
	*Instance
	logger *logger.Logger
}

// NewInstanceOp 新建一个InstanceOp
func NewInstanceOp(ip string, port int, user, pass string, logger *logger.Logger) *InstanceOp {
	return &InstanceOp{
		Instance: &Instance{
			IP:            ip,
			Port:          port,
			AdminUsername: user,
			AdminPassword: pass,
		},
		logger: logger,
	}
}

// DoStop 停止mongod/mongos
func (inst *InstanceOp) DoStop() error {
	// 连接数据库
	using, err := checkPortInUse(inst.Port)

	if err != nil {
		return errors.Wrap(err, "checkPortInUse "+strconv.Itoa(inst.Port))
	}
	if !using {
		inst.logger.Info("port %d is not in use", inst.Port)
		return nil
	}
	maxRetry := 10
	for i := 0; i < maxRetry; i++ {
		pid, err := getPidByPort(inst.Port)
		inst.logger.Info("getPidByPort %d %v", inst.Port, err)

		if err != nil {
			return errors.Wrap(err, "getPidByPort "+strconv.Itoa(inst.Port))
		} else if pid == 0 {
			return nil
		} else if pid > 0 {
			inst.logger.Info("kill pid " + strconv.Itoa(pid))
			err = syscall.Kill(pid, 2)
			if err != nil {
				return errors.Wrap(err, "kill pid "+strconv.Itoa(pid))
			}
		}
		time.Sleep(5 * time.Second)

	}
	return nil
}

const startMongoScript = "/usr/local/mongodb/bin/start_mongo.sh"

// DoStart 启动 mongod/mongos
// 默认是使用start_mongo.sh $port 来启动
// 如果configFile不为空，则使用configFile来启动
func (inst *InstanceOp) DoStart(mode string) error {
	switch mode {
	case "auth":
		_, _, _, err := mycmd.New(startMongoScript, fmt.Sprintf("%d", inst.Port)).Run(time.Second * 60)
		return err
	case "noauth":
		_, _, _, err := mycmd.New(startMongoScript, fmt.Sprintf("%d", inst.Port), "noauth").Run(time.Second * 60)
		return err
	default:
		return errors.New("unknown mode " + mode)
	}

	return nil
}

// DoStartAsStandAlone 启动为单节点
func (inst *InstanceOp) DoStartAsStandAlone() error {
	standaloneConfigFilePath, err := inst.buildStandaloneConfigFile(strconv.Itoa(inst.Port))
	if err != nil {
		return err
	}
	return startMongoWithConfigFile(inst.Port, standaloneConfigFilePath)
}

// buildStandaloneConfigFile 构建单节点的配置文件. standalone.conf
func (inst *InstanceOp) buildStandaloneConfigFile(port string) (string, error) {
	dataDir := consts.GetMongoDataDir(port)
	if dataDir == "" {
		return "", errors.New("can not find data dir for port " + port)
	}
	confFile := filepath.Join(dataDir, "mongodata", port, "mongo.conf")
	conf, err := LoadMongoDBConfFromFile(confFile)
	if err != nil {
		return "", errors.Wrap(err, "load mongo.conf from "+confFile)
	}
	standaloneConfigFilePath := filepath.Join(dataDir, "mongodata", port, "standalone.conf")
	conf.Sharding = nil
	conf.Replication = nil
	// conf.Security = nil
	err = conf.Write(standaloneConfigFilePath)
	if err != nil {
		return "", errors.Wrap(err, "write mongo.conf to "+standaloneConfigFilePath)
	}
	if err = os.MkdirAll(conf.Storage.DbPath, 0755); err != nil {
		return "", errors.Wrap(err, "mkdir "+conf.Storage.DbPath)
	}
	return standaloneConfigFilePath, nil
}

// DoCheckEmptyData  检查数据是否为空, 返回空数据返回nil, 否则返回错误
func (inst *InstanceOp) DoCheckEmptyData() (isEmpty bool, err error) {
	host := mymongo.NewMongoHost(
		inst.IP, fmt.Sprintf("%d", inst.Port), "admin",
		inst.AdminUsername, inst.AdminPassword, "", "")

	client, err := host.Connect()
	if err != nil {
		return false, errors.Wrap(err, "Connect")
	}
	defer client.Disconnect(context.TODO())
	dbList, err := client.ListDatabaseNames(context.TODO(), bson.M{})
	if err != nil {
		return false, errors.Wrap(err, "ListDatabaseNames")
	}
	var notEmptyDb []string
	for _, db := range dbList {
		if mymongo.IsSysDb(db) {
			continue
		}
		if db == "test" {
			continue
		} else {
			notEmptyDb = append(notEmptyDb, db)
		}
	}
	if len(notEmptyDb) > 0 {
		return false, errors.Errorf("not empty data, dblist:%v", notEmptyDb)
	}

	isEmpty = true
	return
}

// RsRemoveMember 从副本集中移除成员
func (inst *InstanceOp) RsRemoveMember(toRemoveMember string) error {
	// stepDown if is primary
	isMasterResult, err := inst.IsMaster()
	if err != nil {
		return errors.Wrap(err, "IsMaster")
	}
	if isMasterResult.Primary == toRemoveMember {

	}

	return nil
}

func (inst *Instance) IsMaster() (*mymongo.IsMasterResult, error) {
	client, err := inst.Connect()
	if err != nil {
		return nil, errors.Wrap(err, "Connect")
	}
	defer client.Disconnect(context.TODO())
	return mymongo.IsMaster(client, 60)
}

// IsRunning 检查服务是否在运行
// return pid:int isRunning:bool, err: error
func (inst *InstanceOp) IsRunning() (pid int, portIsUsing bool, err error) {
	portIsUsing, err = checkPortInUse(inst.Port)
	if err != nil {
		return 0, false, errors.Wrap(err, "checkPortInUse")
	}

	if !portIsUsing {
		return 0, false, nil
	}

	pid, err = getPidByPort(inst.Port)
	if err != nil {
		err = errors.Wrap(err, "getPidByPort")
		return 0, portIsUsing, err
	}
	return
}

func (inst *InstanceOp) ExecJs(js string, timeout int64) error {
	var sb strings.Builder
	sb.WriteString("db = connect('" + inst.IP + ":" + strconv.Itoa(inst.Port) + "/admin');\n")
	sb.WriteString("db.auth('" + inst.AdminUsername + "', '" + inst.AdminPassword + "');\n")
	sb.WriteString(js)
	sb.WriteString("\n")
	jsCode := sb.String()
	code, stdOut, stdErr, err :=
		mycmd.New("/usr/local/mongodb/bin/mongo", "--nodb", "--eval", jsCode).
			Run(time.Second * time.Duration(timeout))
	log.Printf("ExecJs %s return %d %s %s", jsCode, code, stdOut, stdErr)
	return errors.Wrap(err, fmt.Sprintf("ExecJs %s return %d %s %s", jsCode, code, stdOut, stdErr))
}

func (inst *InstanceOp) GrantRolesToUser(user string, roles []string) error {
	for i, role := range roles {
		roles[i] = fmt.Sprintf(`'%s'`, role)
	}
	rolesVal := strings.Join(roles, ",")
	err := inst.ExecJs(fmt.Sprintf(`db.grantRolesToUser('%s', [%s]);`, user, rolesVal), 60)
	return errors.Wrap(err, "GrantRolesToUser")
}

func checkPortInUse(port int) (bool, error) {
	tcpRows, err := linuxproc.ProcNetTcp(nil)
	if err != nil {
		return false, err
	}
	idx := slices.IndexFunc(tcpRows, func(row linuxproc.NetTcp) bool {
		return row.LocalPort == port
	})

	return idx >= 0, nil
}

// getPidByPort 通过端口获取pid. 普通用户只能查到自己的进程的pid
func getPidByPort(port int) (int, error) {
	cmd := exec.Command("lsof", "-i", ":"+fmt.Sprintf("%d", port), "-t", "-sTCP:LISTEN")
	output, err := cmd.Output()

	if err != nil {
		if err.Error() == "exit status 1" {
			return 0, nil
		}
		return 0, err
	}
	re := regexp.MustCompile(`\d+`)
	pid := re.FindString(string(output))
	return strconv.Atoi(pid)
}

func startMongoWithConfigFile(port int, confFile string) error {
	// 启动服务
	cmd := exec.Command("/usr/local/mongodb/bin/mongod", "--config", confFile)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Start()
	if err != nil {
		return err
	}
	return nil
}
