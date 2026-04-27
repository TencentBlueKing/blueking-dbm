package common

import (
	"bytes"
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/dbmon/pkg/linuxproc"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
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

// NewInstance TODO
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
	listenPID, err := getPidByPort(inst.Port)
	if err != nil {
		return errors.Wrap(err, "getPidByPort "+strconv.Itoa(inst.Port))
	}
	if listenPID == 0 {
		inst.logger.Info("port %d has no TCP listener", inst.Port)
		return nil
	}
	maxRetry := 10
	for i := 0; i < maxRetry; i++ {
		pid, err := getPidByPort(inst.Port)
		inst.logger.Info("getPidByPort %d %v", inst.Port, err)

		if err != nil {
			return errors.Wrap(err, "getPidByPort "+strconv.Itoa(inst.Port))
		} else if pid == 0 {
			return inst.waitPortRelease(maxRetry, 10*time.Second)
		} else if pid > 0 {
			processName, err := os.ReadFile(fmt.Sprintf("/proc/%d/comm", pid))
			if err != nil {
				return errors.Wrap(err, "read process name from /proc/"+strconv.Itoa(pid)+"/comm")
			}
			processNameStr := strings.TrimSpace(string(processName))
			inst.logger.Info("process name: %s, pid: %d", processNameStr, pid)
			if strings.Contains(processNameStr, "mongod") || strings.Contains(processNameStr, "mongos") {
				inst.logger.Info("kill pid %d (process name: %s) by signal 2", pid, processNameStr)
				err = syscall.Kill(pid, 2)
				if err != nil {
					return errors.Wrap(err, "kill pid "+strconv.Itoa(pid))
				}
				inst.logger.Info("kill pid %d (process name: %s) successfully", pid, processNameStr)
			} else {
				return fmt.Errorf("port %d is occupied by non-mongo process %q (pid=%d), stop aborted", inst.Port, processNameStr, pid)
			}
		}
		time.Sleep(5 * time.Second)
	}

	// Extra wait: process may need longer than maxRetry*5s to release the port from /proc/net/tcp.
	if err := inst.waitPortRelease(24, 5*time.Second); err == nil {
		inst.logger.Info("port %d released after extended wait following stop retries", inst.Port)
		return nil
	}
	return fmt.Errorf("port %d still in use after %d retries, stop failed", inst.Port, maxRetry)
}

// waitPortRelease waits until no TCP LISTEN on the port (/proc/net/tcp + tcp6), not merely any /proc/net/tcp row.
func (inst *InstanceOp) waitPortRelease(maxRetry int, waitTime time.Duration) error {
	for i := 0; i < maxRetry; i++ {
		listenPID, err := getPidByPort(inst.Port)
		if err != nil {
			return errors.Wrap(err, "getPidByPort after stop")
		}
		if listenPID == 0 {
			inst.logger.Info("port %d has no TCP listener", inst.Port)
			return nil
		}
		inst.logger.Info("port %d still has TCP LISTEN (pid %d), attempt %d/%d, waiting...", inst.Port, listenPID, i+1, maxRetry)
		time.Sleep(waitTime)
	}
	return fmt.Errorf("port %d still has TCP LISTEN after process stopped, waited %d retries", inst.Port, maxRetry)
}

func getMongoBinRootDir() string {
	if binDir := strings.TrimSpace(os.Getenv("MONGO_BIN_DIR")); binDir != "" {
		return binDir
	}
	return "/usr/local"
}

// DoStart 启动 mongod/mongos
// 直接使用 mongod --config，避免依赖 start_mongo.sh 中的固定路径。
func (inst *InstanceOp) DoStart(mode string) error {
	dataDir := consts.GetMongoDataDir(strconv.Itoa(inst.Port))
	if dataDir == "" {
		return errors.New("can not find data dir for port " + strconv.Itoa(inst.Port))
	}
	confName := "noauth.conf"
	switch mode {
	case "auth":
		confName = "mongo.conf"
	case "noauth":
	default:
		return errors.New("unknown mode " + mode)
	}
	confPath := filepath.Join(dataDir, "mongodata", strconv.Itoa(inst.Port), confName)
	mongodBin := filepath.Join(getMongoBinRootDir(), "mongodb", "bin", "mongod")
	shellCmd := fmt.Sprintf(
		"if command -v numactl >/dev/null 2>&1; then numactl --interleave=all %s --config %s; else %s --config %s; fi",
		mongodBin, confPath, mongodBin, confPath,
	)
	_, err := mycmd.New("bash", "-c", shellCmd).Run3(time.Second*60, nil, nil)
	return err
}

// DoStartAsStandAlone 启动为单节点
func (inst *InstanceOp) DoStartAsStandAlone() error {
	standaloneConfigFilePath, err := inst.buildStandaloneConfigFile(strconv.Itoa(inst.Port))
	if err != nil {
		return err
	}
	return startMongoWithConfigFile(inst.Port, standaloneConfigFilePath)
}

// GetDBPathFromConfig 从实例配置中提取存储路径
func (inst *InstanceOp) GetDBPathFromConfig() (string, error) {
	dataDir := consts.GetMongoDataDir(strconv.Itoa(inst.Port))
	if dataDir == "" {
		return "", errors.New("can not find data dir for port " + strconv.Itoa(inst.Port))
	}
	confFile := filepath.Join(dataDir, "mongodata", strconv.Itoa(inst.Port), "mongo.conf")
	conf, err := LoadMongoDBConfFromFile(confFile)
	if err != nil {
		return "", errors.Wrap(err, "load mongo.conf from "+confFile)
	}
	if conf.Storage.DbPath == "" {
		return "", errors.New("dbPath is empty in " + confFile)
	}
	return conf.Storage.DbPath, nil
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

// IsMaster TODO
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

// ExecJs TODO
func (inst *InstanceOp) ExecJs(js string, timeout int64) error {
	var sb strings.Builder
	sb.WriteString("db = connect('" + inst.IP + ":" + strconv.Itoa(inst.Port) + "/admin');\n")
	sb.WriteString("db.auth('" + inst.AdminUsername + "', '" + inst.AdminPassword + "');\n")
	sb.WriteString(js)
	sb.WriteString("\n")
	jsCode := sb.String()
	o, err := mycmd.New(filepath.Join(getMongoBinRootDir(), "mongodb", "bin", "mongo"), "--nodb", "--eval", jsCode).
		Run3(time.Second*time.Duration(timeout), bytes.NewBuffer(nil), bytes.NewBuffer(nil))

	if err != nil {
		return errors.Wrap(err, "ExecJs")
	}

	log.Printf("ExecJs %s return %d %s %s", js, o.ExitCode, o.GetStdout(), o.GetStderr())
	return errors.Wrap(err, fmt.Sprintf("ExecJs %s return %d %s %s", js, o.ExitCode, o.GetStdout(), o.GetStderr()))
}

// GrantRolesToUser TODO
func (inst *InstanceOp) GrantRolesToUser(user string, roles []string) error {
	for i, role := range roles {
		roles[i] = fmt.Sprintf(`'%s'`, role)
	}
	rolesVal := strings.Join(roles, ",")
	err := inst.ExecJs(fmt.Sprintf(`db.grantRolesToUser('%s', [%s]);`, user, rolesVal), 60)
	return errors.Wrap(err, "GrantRolesToUser")
}

// DoFlushRouterConfig TODO
func (inst *InstanceOp) DoFlushRouterConfig() error {
	return inst.ExecJs("db.adminCommand({flushRouterConfig: 1});", 300)
}

// DoServiceStatusCheck 检查服务状态是否正常.
// 如果是mongos，则检查是否有admin, config, local三个库.
// 如果是mongod，则检查是否为PRIMARY或者SECONDARY.
func (inst *InstanceOp) DoServiceStatusCheck(logger *logger.Logger) error {
	client, err := inst.ConnectDirect()
	if err != nil {
		return errors.Wrap(err, "ConnectDirect")
	}
	defer client.Disconnect(context.TODO())
	// determine instance type
	isMasterResult, err := mymongo.IsMaster(client, 120)
	if err != nil {
		return errors.Wrap(err, "IsMaster")
	}
	isMongos := isMasterResult.Msg == "isdbgrid"
	logger.Info("%s isMongos: %t", inst.Addr(), isMongos)
	logger.Info("%s isMasterResult: %+v", inst.Addr(), isMasterResult)

	if isMongos {
		dbList, err := client.ListDatabaseNames(context.TODO(), bson.M{})
		if err != nil {
			return errors.Wrap(err, "ListDatabaseNames")
		}
		if !slices.Contains(dbList, "admin") || !slices.Contains(dbList, "config") {
			return errors.New("not found admin, config, local database")
		}
		logger.Info("%s found admin, config database, seems ok", inst.Addr())
		return nil
	} else {
		return replicaSetServiceCheckRoleOK(isMasterResult)
	}
}

// replicaSetServiceCheckRoleOK returns nil when the connected member reports PRIMARY or SECONDARY (replica set data-bearing).
func replicaSetServiceCheckRoleOK(isMasterResult *mymongo.IsMasterResult) error {
	if isMasterResult.Primary == "" {
		return errors.New("no primary found")
	}
	if isMasterResult.Secondary || isMasterResult.IsMaster {
		return nil
	}
	return errors.New("is not primary or secondary")
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

// getPidByPort 通过端口获取监听进程的 pid（/proc/net/tcp、tcp6 与 /proc/*/fd，不依赖 lsof）。
// 普通用户只能扫到自己有权限的 /proc 条目，可能返回 0 即使端口被其他用户占用。
func getPidByPort(port int) (int, error) {
	return linuxproc.TCPListenPID(port)
}

// portHasTCPListenIPv4 通过 /proc/net/tcp 与 tcp6 判断端口是否仍有 TCP LISTEN（任意本机地址，含 127.0.0.1）。
// 使用 TCPPortHasLISTEN，不依赖 inode 列是否解析成功（ListenSocketInodes 曾因 inode<=0 漏掉 LISTEN）。
func portHasTCPListenIPv4(port int) (bool, error) {
	return linuxproc.TCPPortHasLISTEN(port)
}

func startMongoWithConfigFile(port int, confFile string) error {
	// 启动服务
	cmd := exec.Command(filepath.Join(getMongoBinRootDir(), "mongodb", "bin", "mongod"), "--config", confFile)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Start()
	if err != nil {
		return err
	}
	return nil
}
