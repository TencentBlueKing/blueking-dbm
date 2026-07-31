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

// PrimaryStepDownSettleWait is the fixed wait after a primary becomes SECONDARY before shutdown.
const PrimaryStepDownSettleWait = 30 * time.Second

// StopOptions controls DoStopWithOptions behavior.
// Graceful=true: 在停实例前，如果当前节点是primary则先执行rs.stepDown并等待变为SECONDARY，再发送SIGINT。
// Graceful=false: 跳过stepDown，直接SIGINT关停。
// SkipStepDown=true: graceful 停服时跳过 stepDown（由前置 step_down_if_primary 完成时使用）。
// SkipRsAvailabilityCheck=true: graceful 停服时跳过 RS 可用性检查（由前置 check_rs_availability 完成时使用）。
// Timeout>0: 整个 stop 流程（含 stepDown、SIGINT、端口释放等待）的最长总时长。
type StopOptions struct {
	Graceful                bool
	Timeout                 time.Duration
	SkipStepDown            bool
	SkipRsAvailabilityCheck bool
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
	return inst.DoStopWithOptions(StopOptions{Graceful: true})
}

// DoStopWithOptions 停止mongod/mongos，并按选项决定是否先做stepDown
func (inst *InstanceOp) DoStopWithOptions(opts StopOptions) error {
	var deadline time.Time
	hasDeadline := opts.Timeout > 0
	if hasDeadline {
		deadline = time.Now().Add(opts.Timeout)
	}
	checkDeadline := func() error {
		if hasDeadline && time.Now().After(deadline) {
			return fmt.Errorf("graceful stop timeout for %s after %s", inst.Addr(), opts.Timeout)
		}
		return nil
	}
	remaining := func() time.Duration {
		if !hasDeadline {
			return 0
		}
		return time.Until(deadline)
	}

	listenPID, err := getPidByPort(inst.Port)
	if err != nil {
		return errors.Wrap(err, "getPidByPort "+strconv.Itoa(inst.Port))
	}
	if listenPID == 0 {
		inst.logger.Info("port %d has no listener pid", inst.Port)
		return nil
	}
	processNameStr, err := getProcessNameByPID(listenPID)
	if err != nil {
		return err
	}
	inst.logger.Info("process name: %s, pid: %d", processNameStr, listenPID)
	if !strings.Contains(processNameStr, "mongod") && !strings.Contains(processNameStr, "mongos") {
		return fmt.Errorf("port %d is occupied by non-mongo process %q (pid=%d), stop aborted", inst.Port, processNameStr, listenPID)
	}
	if opts.Graceful {
		if !opts.SkipRsAvailabilityCheck {
			if err = inst.DoCheckRsAvailabilityBeforeRestart(); err != nil {
				return errors.Wrap(err, "rs availability check before graceful stop")
			}
		} else {
			inst.logger.Info("skip rs availability check before graceful stop on %s (already done)", inst.Addr())
		}
		if !opts.SkipStepDown {
			stepDownTimeout := 120 * time.Second
			if hasDeadline {
				if rem := remaining(); rem <= 0 {
					return checkDeadline()
				} else if rem < stepDownTimeout {
					stepDownTimeout = rem
				}
			}
			if err = inst.stepDownIfPrimaryWithTimeout(processNameStr, stepDownTimeout); err != nil {
				return errors.Wrap(err, "stepDownIfPrimary before stop")
			}
		} else {
			inst.logger.Info("skip stepDown before graceful stop on %s (already done)", inst.Addr())
		}
	} else {
		inst.logger.Info("graceful stop disabled, skip stepDown before kill -2 on %s", inst.Addr())
	}
	maxRetry := 10
	for i := 0; i < maxRetry; i++ {
		if err := checkDeadline(); err != nil {
			return err
		}
		pid, err := getPidByPort(inst.Port)
		inst.logger.Info("getPidByPort %d %v", inst.Port, err)

		if err != nil {
			return errors.Wrap(err, "getPidByPort "+strconv.Itoa(inst.Port))
		} else if pid == 0 {
			waitRetry := maxRetry
			waitInterval := 10 * time.Second
			if hasDeadline {
				waitRetry = int(remaining()/waitInterval) + 1
				if waitRetry < 1 {
					return checkDeadline()
				}
			}
			return inst.waitPortReleaseWithDeadline(waitRetry, waitInterval, deadline, hasDeadline)
		} else if pid > 0 {
			processNameStr, err := getProcessNameByPID(pid)
			if err != nil {
				return err
			}
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
		sleepDuration := 5 * time.Second
		if hasDeadline {
			if rem := remaining(); rem <= 0 {
				return checkDeadline()
			} else if rem < sleepDuration {
				sleepDuration = rem
			}
		}
		time.Sleep(sleepDuration)
	}

	// Extra wait: process may need longer than maxRetry*5s to release the listener pid.
	extraRetry := 24
	extraInterval := 5 * time.Second
	if hasDeadline {
		extraRetry = int(remaining()/extraInterval) + 1
		if extraRetry < 1 {
			return checkDeadline()
		}
	}
	if err := inst.waitPortReleaseWithDeadline(extraRetry, extraInterval, deadline, hasDeadline); err == nil {
		inst.logger.Info("port %d released after extended wait following stop retries", inst.Port)
		return nil
	}
	if hasDeadline {
		return checkDeadline()
	}
	return fmt.Errorf("port %d still in use after %d retries, stop failed", inst.Port, maxRetry)
}

func (inst *InstanceOp) stepDownIfPrimary(processName string) error {
	return inst.stepDownIfPrimaryWithTimeout(processName, 120*time.Second)
}

// DoStepDownIfPrimary stepDown when current member is PRIMARY, wait until SECONDARY, then settle wait.
func (inst *InstanceOp) DoStepDownIfPrimary() error {
	listenPID, err := getPidByPort(inst.Port)
	if err != nil {
		return errors.Wrap(err, "getPidByPort for stepDown "+strconv.Itoa(inst.Port))
	}
	if listenPID == 0 {
		inst.logger.Info("port %d has no listener pid, skip stepDown on %s", inst.Port, inst.Addr())
		return nil
	}
	processNameStr, err := getProcessNameByPID(listenPID)
	if err != nil {
		return err
	}
	return inst.stepDownIfPrimaryWithTimeout(processNameStr, 120*time.Second)
}

func (inst *InstanceOp) stepDownIfPrimaryWithTimeout(processName string, stepDownTimeout time.Duration) error {
	if !strings.Contains(processName, "mongod") {
		inst.logger.Info("process %s is not mongod, skip stepDown before stop", processName)
		return nil
	}

	isMasterResult, err := inst.IsMasterDirect()
	if err != nil {
		return errors.Wrap(err, "IsMaster before stop")
	}
	if isMasterResult.SetName == "" || isMasterResult.Primary == "" {
		inst.logger.Info("instance %s is not replicaset primary candidate, skip stepDown", inst.Addr())
		return nil
	}
	if !isMasterResult.IsMaster {
		inst.logger.Info("instance %s is not primary (primary=%s), skip stepDown", inst.Addr(), isMasterResult.Primary)
		return nil
	}

	inst.logger.Info("instance %s is primary, start stepDown before kill -2", inst.Addr())
	switched, err := inst.execRsStepDownAndVerify(stepDownTimeout)
	if err != nil {
		return errors.Wrap(err, "execute rs.stepDown")
	}
	if !switched {
		return fmt.Errorf("instance %s did not become secondary after rs.stepDown", inst.Addr())
	}
	inst.logger.Info("instance %s stepDown succeeded before stop", inst.Addr())
	return nil
}

func (inst *InstanceOp) execRsStepDownAndVerify(timeout time.Duration) (bool, error) {
	client, err := inst.ConnectDirect()
	if err != nil {
		return false, errors.Wrap(err, "ConnectDirect for rs.stepDown")
	}
	defer client.Disconnect(context.Background())

	runErr := client.Database("admin").RunCommand(
		context.Background(),
		bson.D{{Key: "replSetStepDown", Value: 60}},
	).Err()
	if runErr != nil {
		// Connection errors right after replSetStepDown are expected in many versions.
		inst.logger.Warn("rs.stepDown command returned error (may be expected): %v", runErr)
	}

	deadline := time.Now().Add(timeout)
	pollDeadline := deadline.Add(-PrimaryStepDownSettleWait)
	if pollDeadline.Before(time.Now()) {
		pollDeadline = time.Now()
	}
	for {
		isMasterResult, err := inst.IsMasterDirect()
		if err == nil {
			if isMasterResult.Secondary {
				settle := PrimaryStepDownSettleWait
				if rem := time.Until(deadline); rem <= 0 {
					return false, fmt.Errorf("wait member become secondary timeout after rs.stepDown (%s)", timeout)
				} else if rem < settle {
					inst.logger.Warn(
						"member %s became SECONDARY, shorten settle wait from %s to %s",
						inst.Addr(), PrimaryStepDownSettleWait, rem,
					)
					settle = rem
				}
				inst.logger.Info(
					"member %s became SECONDARY, waiting %s before shutdown",
					inst.Addr(), settle,
				)
				time.Sleep(settle)
				return true, nil
			}
			inst.logger.Info(
				"waiting member %s to become SECONDARY after rs.stepDown: isMaster=%v secondary=%v primary=%s",
				inst.Addr(), isMasterResult.IsMaster, isMasterResult.Secondary, isMasterResult.Primary,
			)
		} else {
			inst.logger.Warn("wait new primary after stepDown got error: %v", err)
		}

		if time.Now().After(pollDeadline) {
			return false, fmt.Errorf("wait member become secondary timeout after rs.stepDown (%s)", timeout)
		}
		time.Sleep(1 * time.Second)
	}
}

// IsMasterDirect checks local member state by direct connection to inst.IP:inst.Port.
func (inst *Instance) IsMasterDirect() (*mymongo.IsMasterResult, error) {
	client, err := inst.ConnectDirect()
	if err != nil {
		return nil, errors.Wrap(err, "ConnectDirect")
	}
	defer client.Disconnect(context.TODO())
	return mymongo.IsMaster(client, 60)
}

func getProcessNameByPID(pid int) (string, error) {
	processName, err := os.ReadFile(fmt.Sprintf("/proc/%d/comm", pid))
	if err != nil {
		return "", errors.Wrap(err, "read process name from /proc/"+strconv.Itoa(pid)+"/comm")
	}
	return strings.TrimSpace(string(processName)), nil
}

// waitPortRelease waits until no listener pid is resolved for the port (pid+port standard).
func (inst *InstanceOp) waitPortRelease(maxRetry int, waitTime time.Duration) error {
	return inst.waitPortReleaseWithDeadline(maxRetry, waitTime, time.Time{}, false)
}

func (inst *InstanceOp) waitPortReleaseWithDeadline(
	maxRetry int, waitTime time.Duration, deadline time.Time, hasDeadline bool,
) error {
	for i := 0; i < maxRetry; i++ {
		if hasDeadline && time.Now().After(deadline) {
			return fmt.Errorf("port %d still has listener pid after stop timeout", inst.Port)
		}
		listenPID, err := getPidByPort(inst.Port)
		if err != nil {
			return errors.Wrap(err, "getPidByPort after stop")
		}
		if listenPID == 0 {
			inst.logger.Info("port %d has no listener pid", inst.Port)
			return nil
		}
		inst.logger.Info("port %d still has listener pid %d, attempt %d/%d, waiting...", inst.Port, listenPID, i+1, maxRetry)
		sleepDuration := waitTime
		if hasDeadline {
			if rem := time.Until(deadline); rem <= 0 {
				return fmt.Errorf("port %d still has listener pid after stop timeout", inst.Port)
			} else if rem < sleepDuration {
				sleepDuration = rem
			}
		}
		time.Sleep(sleepDuration)
	}
	return fmt.Errorf("port %d still has listener pid after process stopped, waited %d retries", inst.Port, maxRetry)
}

func getMongoBinRootDir() string {
	if binDir := strings.TrimSpace(os.Getenv("MONGO_BIN_DIR")); binDir != "" {
		return binDir
	}
	return "/usr/local"
}

// DoStart 启动 mongod/mongos
// 直接使用对应进程 --config，避免依赖 start_mongo.sh 中的固定路径。
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
	mongoBin := filepath.Join(getMongoBinRootDir(), "mongodb", "bin", inst.startProcessNameByDBType())
	shellCmd := fmt.Sprintf(
		"if command -v numactl >/dev/null 2>&1; then numactl --interleave=all %s --config %s; else %s --config %s; fi",
		mongoBin, confPath, mongoBin, confPath,
	)
	_, err := mycmd.New("bash", "-c", shellCmd).Run3(time.Second*60, nil, nil)
	return err
}

// IsMongosByDBType reports whether this instance should be treated as mongos.
// Payload InstanceType takes precedence; missing values fall back to the dbtype file.
func (inst *InstanceOp) IsMongosByDBType() bool {
	if strings.TrimSpace(inst.InstanceType) != "" {
		return strings.EqualFold(strings.TrimSpace(inst.InstanceType), "mongos")
	}
	return inst.startProcessNameByDBType() == "mongos"
}

func (inst *InstanceOp) startProcessNameByDBType() string {
	dbTypePath := filepath.Join(consts.GetMongoDataDir(strconv.Itoa(inst.Port)), "mongodata", strconv.Itoa(inst.Port), "dbtype")
	if content, err := os.ReadFile(dbTypePath); err == nil && strings.TrimSpace(string(content)) == "mongos" {
		return "mongos"
	}
	return "mongod"
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

// IsRunning 检查服务是否在运行（标准：端口可解析出 pid > 0）。
// return pid:int isRunning:bool, err: error
func (inst *InstanceOp) IsRunning() (pid int, portIsUsing bool, err error) {
	pid, err = getPidByPort(inst.Port)
	if err != nil {
		return 0, false, errors.Wrap(err, "getPidByPort")
	}
	if pid == 0 {
		return 0, false, nil
	}
	return pid, true, nil
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

// DoWaitUntilReady polls service status until healthy or timeout.
func (inst *InstanceOp) DoWaitUntilReady(logger *logger.Logger, timeout time.Duration) error {
	if timeout <= 0 {
		timeout = 300 * time.Second
	}
	deadline := time.Now().Add(timeout)
	interval := 5 * time.Second
	var lastErr error
	for {
		if err := inst.DoServiceStatusCheck(logger); err == nil {
			logger.Info("instance %s became ready", inst.Addr())
			return nil
		} else {
			lastErr = err
			logger.Info("instance %s not ready yet: %v", inst.Addr(), err)
		}
		if time.Now().After(deadline) {
			if lastErr != nil {
				return fmt.Errorf("wait until ready timeout for %s after %s: %w", inst.Addr(), timeout, lastErr)
			}
			return fmt.Errorf("wait until ready timeout for %s after %s", inst.Addr(), timeout)
		}
		sleepDuration := interval
		if rem := time.Until(deadline); rem < sleepDuration {
			sleepDuration = rem
		}
		if sleepDuration <= 0 {
			break
		}
		time.Sleep(sleepDuration)
	}
	if lastErr != nil {
		return fmt.Errorf("wait until ready timeout for %s after %s: %w", inst.Addr(), timeout, lastErr)
	}
	return fmt.Errorf("wait until ready timeout for %s after %s", inst.Addr(), timeout)
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

// getPidByPort 通过端口获取监听进程的 pid（/proc/net/tcp IPv4 与 /proc/*/fd，不依赖 lsof；失败时 ss/netstat fallback）。
// 普通用户只能扫到自己有权限的 /proc 条目，可能返回 0 即使端口被其他用户占用。
func getPidByPort(port int) (int, error) {
	return linuxproc.TCPListenPID(port)
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
