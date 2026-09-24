package atommongodb

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

const (
	mongoInstanceTypeMongod = "mongod"
	mongoInstanceTypeMongos = "mongos"
	rsStateRemoved          = 10
	rsStateStrRemoved       = "REMOVED"
	// Older MongoDB after rs.remove(): isMaster.info (not myState=10).
	rsInvalidConfigMsg = "does not have a valid replica set config"

	// After rs.remove() the recovered node may briefly report SECONDARY on stale
	// local config until it learns the newer replica-set config.
	mongodRemovedCheckAttempts = 12
	mongodRemovedCheckInterval = 5 * time.Second
)

// DeferredDeInstallConfParams 延迟下架严格卸载参数
type DeferredDeInstallConfParams struct {
	IP              string   `json:"ip" validate:"required"`
	Port            int      `json:"port" validate:"required"`
	SetId           string   `json:"setId"`
	NodeInfo        []string `json:"nodeInfo" validate:"required"`
	ReplicaSetPeers []string `json:"replicaSetPeers"`
	InstanceType    string   `json:"instanceType" validate:"required"` // mongod mongos
	RenameDir       bool     `json:"renameDir"`
	AdminUsername   string   `json:"adminUsername"`
	AdminPassword   string   `json:"adminPassword"`
}

// DeferredDeInstall 故障替换后的延迟严格卸载：进程已停可直接清理；
// mongod 运行中必须已脱离副本集（REMOVED / 旧版 invalid replica set config）；
// mongos 运行中必须无外部连接。禁止 force 跳过检查。
type DeferredDeInstall struct {
	BaseJob
	runtime          *jobruntime.JobGenericRuntime
	BinDir           string
	DataDir          string
	BackupDir        string
	PortDir          string
	LogPortDir       string
	DbPathRenameDir  string
	LogPathRenameDir string
	Mongo            string
	ServiceStatus    bool
	ConfParams       *DeferredDeInstallConfParams
}

// NewDeferredDeInstall 实例化
func NewDeferredDeInstall() jobruntime.JobRunner {
	return &DeferredDeInstall{}
}

// Name 原子任务名
func (d *DeferredDeInstall) Name() string {
	return "mongo_deferred_deinstall"
}

// Run 运行
func (d *DeferredDeInstall) Run() error {
	if err := d.checkMongoService(); err != nil {
		return err
	}

	if d.ServiceStatus {
		if err := d.precheckRunning(); err != nil {
			return err
		}
		if err := d.shutdownProcess(); err != nil {
			return err
		}
		d.runtime.Logger.Info("shutdown service successfully")
	} else {
		d.runtime.Logger.Info("mongo process already stopped, skip state/connection precheck")
	}

	if err := d.dirRename(); err != nil {
		return err
	}
	return nil
}

// Retry 重试次数
func (d *DeferredDeInstall) Retry() uint {
	return 2
}

// Rollback 回滚
func (d *DeferredDeInstall) Rollback() error {
	return nil
}

// Init 初始化
func (d *DeferredDeInstall) Init(runtime *jobruntime.JobGenericRuntime) error {
	d.runtime = runtime
	d.runtime.Logger.Info("start to init deferred deinstall")
	d.BinDir = consts.GetMongoBinDir()
	d.DataDir = consts.GetMongoDataDir()
	d.BackupDir = consts.GetMongoBackupDir()

	if err := json.Unmarshal([]byte(d.runtime.PayloadDecoded), &d.ConfParams); err != nil {
		d.runtime.Logger.Error("get parameters of deferred deInstall fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of deferred deInstall fail by json.Unmarshal, error:%s", err)
	}

	d.Mongo = filepath.Join(d.BinDir, "mongodb", "bin", "mongo")
	strPort := strconv.Itoa(d.ConfParams.Port)
	d.PortDir = filepath.Join(d.DataDir, "mongodata", strPort)
	strTime := time.Now().Format("20060102150405")
	renameDirName := fmt.Sprintf("removed_%d_%s", d.ConfParams.Port, strTime)
	d.DbPathRenameDir = filepath.Join(d.DataDir, "mongodata", renameDirName)
	d.LogPathRenameDir = filepath.Join(d.BackupDir, "mongolog", renameDirName)
	d.LogPortDir = filepath.Join(d.BackupDir, "mongolog", strPort)

	validate := validator.New()
	if err := validate.Struct(d.ConfParams); err != nil {
		d.runtime.Logger.Error("validate parameters of deferred deInstall fail, error:%s", err)
		return fmt.Errorf("validate parameters of deferred deInstall fail, error:%s", err)
	}
	instType := strings.ToLower(strings.TrimSpace(d.ConfParams.InstanceType))
	if instType != mongoInstanceTypeMongod && instType != mongoInstanceTypeMongos {
		return fmt.Errorf("unsupported instanceType:%s", d.ConfParams.InstanceType)
	}
	d.ConfParams.InstanceType = instType
	return nil
}

func (d *DeferredDeInstall) checkMongoService() error {
	d.runtime.Logger.Info("start to check process status")
	flag, _, err := common.CheckMongoService(d.ConfParams.Port)
	if err != nil {
		d.runtime.Logger.Error("get mongo service status fail, error:%s", err)
		return fmt.Errorf("get mongo service status fail, error:%s", err)
	}
	d.ServiceStatus = flag
	return nil
}

func (d *DeferredDeInstall) precheckRunning() error {
	switch d.ConfParams.InstanceType {
	case mongoInstanceTypeMongod:
		return d.checkMongodRemoved()
	case mongoInstanceTypeMongos:
		return checkExternalMongoConnections(
			d.runtime.Logger.Info,
			d.runtime.Logger.Error,
			d.ConfParams.Port,
			d.ConfParams.IP,
			d.ConfParams.NodeInfo,
		)
	default:
		return fmt.Errorf("unsupported instanceType:%s", d.ConfParams.InstanceType)
	}
}

// mongodRemovedCheckResult is the JSON shape returned by the REMOVED precheck eval.
type mongodRemovedCheckResult struct {
	OK           int    `json:"ok"`
	State        int    `json:"state"`
	StateStr     string `json:"stateStr"`
	Msg          string `json:"msg"`
	IsMaster     *bool  `json:"ismaster"`
	Secondary    *bool  `json:"secondary"`
	IsReplicaSet *bool  `json:"isreplicaset"`
	RsStatusErr  string `json:"rsStatusErr"`
}

// isMongodRemovedAccepted reports whether local mongod is safely out of the replica set.
// Accepts: myState=10 / stateStr REMOVED / hello.msg containing "removed",
// or older MongoDB after rs.remove(): isMaster/hello with info/msg
// "Does not have a valid replica set config" and ismaster=false, secondary=false.
func isMongodRemovedAccepted(r mongodRemovedCheckResult) bool {
	msgLower := strings.ToLower(r.Msg)
	if strings.Contains(msgLower, "removed") {
		return true
	}
	if r.State == rsStateRemoved || strings.EqualFold(r.StateStr, rsStateStrRemoved) {
		return true
	}
	if strings.Contains(msgLower, rsInvalidConfigMsg) {
		isMasterFalse := r.IsMaster != nil && !*r.IsMaster
		secondaryFalse := r.Secondary != nil && !*r.Secondary
		if isMasterFalse && secondaryFalse {
			return true
		}
	}
	return false
}

func isMongodRemovedRetryable(r mongodRemovedCheckResult) bool {
	if r.State == 1 || strings.EqualFold(r.StateStr, "PRIMARY") {
		return false
	}
	if r.IsMaster != nil && *r.IsMaster {
		return false
	}
	if r.State == 2 || strings.EqualFold(r.StateStr, "SECONDARY") {
		return true
	}
	if r.Secondary != nil && *r.Secondary {
		return true
	}
	switch r.State {
	case 0, 3, 5, 6: // startup, recovering, startup2, unknown
		return true
	}
	return false
}

func formatMongodRemovedRefuse(r mongodRemovedCheckResult) error {
	return fmt.Errorf(
		"mongod is not REMOVED, refuse deferred deinstall: state=%d stateStr=%s msg=%q ismaster=%v secondary=%v rsStatusErr=%q",
		r.State, r.StateStr, r.Msg, r.IsMaster, r.Secondary, r.RsStatusErr,
	)
}

func waitUntilMongodRemoved(
	probe func() (mongodRemovedCheckResult, error),
	attempts int,
	interval time.Duration,
	sleep func(time.Duration),
	logf func(string, ...interface{}),
) (mongodRemovedCheckResult, error) {
	if attempts < 1 {
		attempts = 1
	}
	if sleep == nil {
		sleep = time.Sleep
	}
	if logf == nil {
		logf = func(string, ...interface{}) {}
	}
	var last mongodRemovedCheckResult
	var lastErr error
	for i := 1; i <= attempts; i++ {
		result, err := probe()
		if err != nil {
			lastErr = err
			logf("REMOVED check attempt %d/%d failed, will retry: %v", i, attempts, err)
			if i < attempts {
				sleep(interval)
			}
			continue
		}
		last = result
		lastErr = nil
		if isMongodRemovedAccepted(result) {
			logf(
				"mongod is REMOVED/out-of-config on attempt %d/%d state=%d stateStr=%s msg=%q",
				i, attempts, result.State, result.StateStr, result.Msg,
			)
			return result, nil
		}
		if !isMongodRemovedRetryable(result) {
			return result, formatMongodRemovedRefuse(result)
		}
		logf(
			"mongod still transitional on attempt %d/%d state=%d stateStr=%s msg=%q, wait for REMOVED",
			i, attempts, result.State, result.StateStr, result.Msg,
		)
		if i < attempts {
			sleep(interval)
		}
	}
	if lastErr != nil {
		return last, fmt.Errorf("check mongod REMOVED fail after %d attempts: %w", attempts, lastErr)
	}
	return last, formatMongodRemovedRefuse(last)
}

// checkMongodRemoved 本机 mongod 必须已脱离副本集（REMOVED 或旧版 invalid config）。
func (d *DeferredDeInstall) checkMongodRemoved() error {
	d.runtime.Logger.Info("start to check mongod REMOVED state")
	if strings.TrimSpace(d.ConfParams.AdminUsername) == "" || strings.TrimSpace(d.ConfParams.AdminPassword) == "" {
		return fmt.Errorf("adminUsername/adminPassword required to verify mongod REMOVED state")
	}

	_, err := waitUntilMongodRemoved(
		d.probeMongodRemoved,
		mongodRemovedCheckAttempts,
		mongodRemovedCheckInterval,
		time.Sleep,
		d.runtime.Logger.Info,
	)
	if err == nil {
		return nil
	}
	if len(d.ConfParams.ReplicaSetPeers) > 0 {
		d.runtime.Logger.Warn(
			"local mongod not REMOVED after retries (%v), fall back to authoritative rs.conf",
			err,
		)
		return d.checkMongodAbsentFromAuthoritativeConfig()
	}
	return err
}

func (d *DeferredDeInstall) probeMongodRemoved() (mongodRemovedCheckResult, error) {
	eval := `
(function(){
  var out = {ok:0, state:0, stateStr:"", msg:"", ismaster:null, secondary:null, isreplicaset:null};
  try {
    var h = null;
    try { h = db.hello(); } catch (e0) {}
    if (!h) {
      try { h = db.isMaster(); } catch (e1) {}
    }
    if (h) {
      out.msg = (h.msg || h.infoMessage || h.info || "") + "";
      if (typeof h.ismaster !== "undefined") { out.ismaster = !!h.ismaster; }
      else if (typeof h.isWritablePrimary !== "undefined") { out.ismaster = !!h.isWritablePrimary; }
      if (typeof h.secondary !== "undefined") { out.secondary = !!h.secondary; }
      if (typeof h.isreplicaset !== "undefined") { out.isreplicaset = !!h.isreplicaset; }
      else if (typeof h.isReplicaSet !== "undefined") { out.isreplicaset = !!h.isReplicaSet; }
      if (h.me) { out.me = h.me; }
    }
  } catch (e) {}
  try {
    var s = rs.status();
    if (s && typeof s.myState !== "undefined") {
      out.state = s.myState;
      out.stateStr = (s.members || []).filter(function(m){return m.state===s.myState;}).map(function(m){return m.stateStr;})[0] || "";
    }
  } catch (e2) {
    out.rsStatusErr = (e2 && e2.message) ? e2.message : (""+e2);
  }
  out.ok = 1;
  print(JSON.stringify(out));
})();`

	stdout, err := d.runMongoEval(eval)
	if err != nil {
		return mongodRemovedCheckResult{}, fmt.Errorf("check mongod REMOVED fail: %w", err)
	}
	var result mongodRemovedCheckResult
	if err := json.Unmarshal([]byte(stdout), &result); err != nil {
		d.runtime.Logger.Error("parse REMOVED check output fail stdout=%q err=%v", stdout, err)
		return mongodRemovedCheckResult{}, fmt.Errorf("parse REMOVED check output fail: %w", err)
	}
	return result, nil
}

// checkMongodAbsentFromAuthoritativeConfig asks the live replica-set primary.
// The recovered source's local config can be stale and may report SECONDARY even
// though the source has already been removed by the replacement flow.
func (d *DeferredDeInstall) checkMongodAbsentFromAuthoritativeConfig() error {
	source := fmt.Sprintf("%s:%d", d.ConfParams.IP, d.ConfParams.Port)
	checkedPrimaries := make(map[string]struct{})
	var errs []string

	for _, peer := range d.ConfParams.ReplicaSetPeers {
		host, portStr, err := net.SplitHostPort(peer)
		if err != nil {
			errs = append(errs, fmt.Sprintf("invalid peer %q: %v", peer, err))
			continue
		}
		port, err := strconv.Atoi(portStr)
		if err != nil {
			errs = append(errs, fmt.Sprintf("invalid peer port %q: %v", peer, err))
			continue
		}
		primary, err := common.GetPrimaryInfo(
			d.Mongo, d.ConfParams.AdminUsername, d.ConfParams.AdminPassword, host, port,
		)
		if err != nil || primary == "" {
			errs = append(errs, fmt.Sprintf("resolve primary via %s fail: %v", peer, err))
			continue
		}
		if _, ok := checkedPrimaries[primary]; ok {
			continue
		}
		checkedPrimaries[primary] = struct{}{}

		primaryHost, primaryPortStr, err := net.SplitHostPort(primary)
		if err != nil {
			errs = append(errs, fmt.Sprintf("invalid primary %q: %v", primary, err))
			continue
		}
		primaryPort, err := strconv.Atoi(primaryPortStr)
		if err != nil {
			errs = append(errs, fmt.Sprintf("invalid primary port %q: %v", primary, err))
			continue
		}
		stdout, err := d.runMongoEvalAt(primaryHost, primaryPort, buildReplicaSetConfigCheckEval(source))
		if err != nil {
			errs = append(errs, fmt.Sprintf("check rs.conf via primary %s fail: %v", primary, err))
			continue
		}
		var result replicaSetConfigCheckResult
		if err := json.Unmarshal([]byte(stdout), &result); err != nil {
			errs = append(errs, fmt.Sprintf("parse rs.conf result via primary %s output=%q: %v", primary, stdout, err))
			continue
		}
		if result.Found {
			return fmt.Errorf(
				"mongod still exists in authoritative rs.conf, refuse deferred deinstall: source=%s primary=%s version=%d",
				source, primary, result.Version,
			)
		}
		d.runtime.Logger.Info(
			"mongod absent from authoritative rs.conf source=%s primary=%s version=%d",
			source, primary, result.Version,
		)
		return nil
	}
	return fmt.Errorf(
		"unable to verify source absence from authoritative rs.conf source=%s errors=%s",
		source, strings.Join(errs, "; "),
	)
}

func (d *DeferredDeInstall) runMongoEval(eval string) (string, error) {
	return d.runMongoEvalAt(d.ConfParams.IP, d.ConfParams.Port, eval)
}

func (d *DeferredDeInstall) runMongoEvalAt(host string, port int, eval string) (string, error) {
	var stdoutBuf bytes.Buffer
	var stderrBuf bytes.Buffer
	cmdBuilder := mycmd.New(
		d.Mongo,
		"-u", d.ConfParams.AdminUsername,
		"-p", mycmd.Password(d.ConfParams.AdminPassword),
		"--host", host,
		"--port", strconv.Itoa(port),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", eval,
	)
	masked := cmdBuilder.GetCmdLine("", true)
	ret, err := cmdBuilder.Run3(60*time.Second, &stdoutBuf, &stderrBuf)
	stdout := strings.TrimSpace(stdoutBuf.String())
	stderr := strings.TrimSpace(stderrBuf.String())
	if err != nil {
		d.runtime.Logger.Error(
			"run mongo eval fail, cmd:%q, exitCode:%d, stdout:%q, stderr:%q, err:%v",
			masked, ret.ExitCode, stdout, stderr, err,
		)
		return "", fmt.Errorf("run mongo eval fail: %w", err)
	}
	if ret.ExitCode != 0 {
		return "", fmt.Errorf("run mongo eval non-zero exit:%d stderr:%s", ret.ExitCode, stderr)
	}
	return stdout, nil
}

func (d *DeferredDeInstall) shutdownProcess() error {
	d.runtime.Logger.Info("start to shutdown service (deferred deinstall, no force skip)")
	if err := common.ShutdownMongoProcess(
		d.runtime.Logger,
		d.ConfParams.Port,
		30*time.Second,
		true,
	); err != nil {
		d.runtime.Logger.Error("shutdown mongo service fail, error:%s", err)
		return fmt.Errorf("shutdown mongo service fail, error:%s", err)
	}
	return nil
}

func (d *DeferredDeInstall) dirRename() error {
	if !d.ConfParams.RenameDir {
		d.runtime.Logger.Info("rename directory is disabled")
		return nil
	}
	if util.FileExists(d.PortDir) {
		d.runtime.Logger.Info("start to rename db directory %s to %s", d.PortDir, d.DbPathRenameDir)
		if _, err := mycmd.New("mv", d.PortDir, d.DbPathRenameDir).Run(60 * time.Second); err != nil {
			d.runtime.Logger.Error("rename db directory fail, error:%s", err)
			return fmt.Errorf("rename db directory fail, error:%s", err)
		}
	} else {
		d.runtime.Logger.Info("db directory %s not exists, skip rename", d.PortDir)
	}
	if util.FileExists(d.LogPortDir) {
		d.runtime.Logger.Info("start to rename log directory %s to %s", d.LogPortDir, d.LogPathRenameDir)
		if _, err := mycmd.New("mv", d.LogPortDir, d.LogPathRenameDir).Run(60 * time.Second); err != nil {
			d.runtime.Logger.Error("rename log directory fail, error:%s", err)
			return fmt.Errorf("rename log directory fail, error:%s", err)
		}
	} else {
		d.runtime.Logger.Info("log directory %s not exists, skip rename", d.LogPortDir)
	}
	return nil
}
