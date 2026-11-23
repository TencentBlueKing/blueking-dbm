package atommongodb

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

// MongoDReplaceConfParams 参数  // 替换mongod
type MongoDReplaceConfParams struct {
	IP             string `json:"ip" validate:"required"` // 执行节点
	Port           int    `json:"port" validate:"required"`
	SourceIP       string `json:"sourceIP"`   // 源节点，新加节点时可以为null
	SourcePort     int    `json:"sourcePort"` // 源端口，新加节点时可以为null
	SourceDown     bool   `json:"sourceDown"` // 源端已down机 true：已down false：未down
	AdminUsername  string `json:"adminUsername" validate:"required"`
	AdminPassword  string `json:"adminPassword" validate:"required"`
	TargetIP       string `json:"targetIP"`       // 目标节点，移除节点时可以为null
	TargetPort     int    `json:"targetPort"`     // 目标端口，移除节点时可以为null
	TargetPriority string `json:"targetPriority"` // 可选，默认为null，如果为null，则使用source端的Priority，取值：0-正无穷
	TargetHidden   string `json:"targetHidden"`   // 可选，默认为null，如果为null，则使用source端的Hidden，取值：null，0，1，0：显现 1：隐藏
}

// MongoDReplace 添加分片到集群
type MongoDReplace struct {
	BaseJob
	runtime         *jobruntime.JobGenericRuntime
	BinDir          string
	Mongo           string
	OsUser          string
	DataDir         string
	DbpathDir       string
	PrimaryIP       string
	PrimaryPort     int
	AddTargetScript string
	ConfParams      *MongoDReplaceConfParams
	TargetIPStatus  int
	TargetPriority  int
	TargetHidden    bool
	StatusCh        chan int
}

type replicaSetConfigCheckResult struct {
	Found   bool `json:"found"`
	Version int  `json:"version"`
}

type rsRemainingMember struct {
	Host     string `json:"host"`
	Votes    int    `json:"votes"`
	Health   int    `json:"health"`
	State    int    `json:"state"`
	StateStr string `json:"stateStr"`
}

type rsRemoveQuorumCheckResult struct {
	Remaining []rsRemainingMember `json:"remaining"`
}

// rsRemoveResult is the JSON printed by buildReplicaSetRemoveEval.
// Both mongosh (throws) and legacy mongo shell (returns cmd result) are
// normalized into this shape so callers can decide retry by numeric code
// without depending on stderr text that Run3 never puts into err.Error().
type rsRemoveResult struct {
	Ok       int    `json:"ok"`
	Code     int    `json:"code"`
	CodeName string `json:"codeName"`
	Errmsg   string `json:"errmsg"`
}

// rsRemoveError is a typed rs.remove failure carried by removeWithRetry.
type rsRemoveError struct {
	Code     int
	CodeName string
	Errmsg   string
}

func (e *rsRemoveError) Error() string {
	if e == nil {
		return "rs.remove fail"
	}
	if e.CodeName != "" {
		return fmt.Sprintf("rs.remove fail: code=%d codeName=%s errmsg=%s", e.Code, e.CodeName, e.Errmsg)
	}
	return fmt.Sprintf("rs.remove fail: code=%d errmsg=%s", e.Code, e.Errmsg)
}

const (
	// MongoDB ErrorCodes::ConfigurationInProgress — replSetReconfig while a
	// previous config change is still being applied.
	errCodeConfigurationInProgress = 109
	// MongoDB ErrorCodes::CurrentConfigNotCommittedYet — common right after
	// rs.add when the newlyAdded flag has not been cleared by the automatic
	// follow-up reconfig (MongoDB 4.4+).
	errCodeCurrentConfigNotCommittedYet = 308
)

func buildReplicaSetConfigCheckEval(source string) string {
	sourceJSON, _ := json.Marshal(source)
	return fmt.Sprintf(`
(function(){
  var source = %s;
  var conf = rs.conf();
  var found = false;
  var members = conf.members || [];
  for (var i = 0; i < members.length; i++) {
    if (members[i].host === source) { found = true; break; }
  }
  print(JSON.stringify({found: found, version: conf.version || 0}));
})();`, string(sourceJSON))
}

func buildReplicaSetRemoveQuorumEval(source string) string {
	sourceJSON, _ := json.Marshal(source)
	return fmt.Sprintf(`
(function(){
  var source = %s;
  var conf = rs.conf();
  var status = rs.status();
  var statusMap = {};
  var sm = status.members || [];
  for (var i = 0; i < sm.length; i++) {
    statusMap[sm[i].name] = sm[i];
  }
  var remaining = [];
  var members = conf.members || [];
  for (var j = 0; j < members.length; j++) {
    var m = members[j];
    if (m.host === source) { continue; }
    var st = statusMap[m.host];
    remaining.push({
      host: m.host,
      votes: (typeof m.votes === "undefined" || m.votes === null) ? 1 : Number(m.votes),
      health: st && typeof st.health !== "undefined" ? Number(st.health) : 0,
      state: st && typeof st.state !== "undefined" ? Number(st.state) : 8,
      stateStr: st && st.stateStr ? st.stateStr : "DOWN"
    });
  }
  print(JSON.stringify({remaining: remaining}));
})();`, string(sourceJSON))
}

// buildReplicaSetRemoveEval runs rs.remove and always prints a JSON result.
// mongosh throws on failure; legacy mongo shell returns the command document
// with ok/code/errmsg and exit 0. Catching + printing covers both paths so
// Go can retry on numeric codes instead of matching stderr strings that never
// appear in Run3's error value.
func buildReplicaSetRemoveEval(source string) string {
	sourceJSON, _ := json.Marshal(source)
	return fmt.Sprintf(`
(function(){
  var source = %s;
  try {
    var r = rs.remove(source);
    if (r === undefined || r === null) {
      print(JSON.stringify({ok:1, code:0, codeName:"", errmsg:""}));
      return;
    }
    print(JSON.stringify({
      ok: (typeof r.ok === "undefined" || r.ok === null) ? 1 : Number(r.ok),
      code: r.code || 0,
      codeName: r.codeName || "",
      errmsg: r.errmsg || ""
    }));
  } catch (e) {
    print(JSON.stringify({
      ok: 0,
      code: e.code || 0,
      codeName: e.codeName || "",
      errmsg: e.message || String(e)
    }));
  }
})();`, string(sourceJSON))
}

const (
	quorumCheckAttempts = 3
	quorumCheckInterval = 2 * time.Second
	// rsRemoveAttempts retries rs.remove when the replica set is still
	// applying a previous reconfig (code 109) or the current config is not
	// yet committed (code 308). Both commonly occur right after rs.add, when
	// the newly added member just reached SECONDARY but config propagation /
	// newlyAdded clearance has not fully settled.
	rsRemoveAttempts = 5
	rsRemoveInterval = 5 * time.Second
)

func isStrictMajorityRefuse(err error) bool {
	return err != nil && strings.Contains(err.Error(), "no strict majority")
}

func isReconfigBusyCode(code int) bool {
	return code == errCodeConfigurationInProgress || code == errCodeCurrentConfigNotCommittedYet
}

// isReconfigBusy reports whether err is a transient replSetReconfig rejection
// (ConfigurationInProgress / CurrentConfigNotCommittedYet). Matching is by
// typed *rsRemoveError code, not by stderr substrings — Run3 only returns
// "exit status N" and never embeds mongosh stderr into err.Error().
func isReconfigBusy(err error) bool {
	var re *rsRemoveError
	if errors.As(err, &re) {
		return isReconfigBusyCode(re.Code)
	}
	return false
}

func parseRsRemoveResult(stdout string) (rsRemoveResult, error) {
	var result rsRemoveResult
	if err := json.Unmarshal([]byte(stdout), &result); err != nil {
		return result, fmt.Errorf("parse rs.remove output %q fail: %w", stdout, err)
	}
	return result, nil
}

func rsRemoveResultError(result rsRemoveResult) error {
	if result.Ok == 1 {
		return nil
	}
	errmsg := result.Errmsg
	if errmsg == "" {
		errmsg = result.CodeName
	}
	if errmsg == "" {
		errmsg = "rs.remove failed"
	}
	return &rsRemoveError{Code: result.Code, CodeName: result.CodeName, Errmsg: errmsg}
}

// removeWithRetry retries rs.remove only while the replica set is still
// applying a previous reconfig. Any other error (auth, notPrimary, quorum,
// dial, ...) is returned immediately without retry.
func removeWithRetry(
	exec func() error,
	attempts int,
	interval time.Duration,
	sleep func(time.Duration),
	warn func(string, ...interface{}),
) error {
	if attempts < 1 {
		attempts = 1
	}
	if sleep == nil {
		sleep = time.Sleep
	}
	var lastErr error
	for i := 1; i <= attempts; i++ {
		err := exec()
		if err == nil {
			return nil
		}
		lastErr = err
		if !isReconfigBusy(err) {
			return err
		}
		if warn != nil {
			warn(
				"rs.remove rejected, reconfig not settled, retry attempt=%d/%d err=%s",
				i, attempts, err.Error(),
			)
		}
		if i < attempts {
			sleep(interval)
		}
	}
	return lastErr
}

func isSingleVotingSurvivor(remaining []rsRemainingMember) bool {
	voting := 0
	healthy := 0
	for _, m := range remaining {
		if m.Votes <= 0 {
			continue
		}
		voting++
		if m.Health == 1 {
			healthy++
		}
	}
	return voting == 1 && healthy == 1
}

// checkQuorumWithRetry re-samples rs.status() when a single health snapshot
// says the set would lose strict majority. Eval/parse errors are not retried.
func checkQuorumWithRetry(
	probe func() ([]rsRemainingMember, error),
	attempts int,
	interval time.Duration,
	sleep func(time.Duration),
) ([]rsRemainingMember, error) {
	if attempts < 1 {
		attempts = 1
	}
	if sleep == nil {
		sleep = time.Sleep
	}
	var last []rsRemainingMember
	var lastErr error
	for i := 1; i <= attempts; i++ {
		remaining, err := probe()
		last = remaining
		lastErr = err
		if err == nil || !isStrictMajorityRefuse(err) {
			return remaining, err
		}
		if i < attempts {
			sleep(interval)
		}
	}
	return last, lastErr
}

// validateRsQuorumAfterRemove refuses rs.remove unless remaining healthy
// voting members would still be a strict majority (healthy*2 > voting).
// Equivalently: failed*2 >= voting is refused, including the even case
// "2 remaining, 1 failed" which cannot keep a PRIMARY.
// Non-voting members (votes=0) are ignored. Members in rs.conf() but missing
// from rs.status() are treated as failed.
func validateRsQuorumAfterRemove(remaining []rsRemainingMember) error {
	voting := 0
	failed := 0
	var failedHosts []string
	for _, m := range remaining {
		if m.Votes <= 0 {
			continue
		}
		voting++
		if m.Health != 1 {
			failed++
			failedHosts = append(failedHosts, fmt.Sprintf("%s(health=%d state=%s)", m.Host, m.Health, m.StateStr))
		}
	}
	if voting == 0 {
		return fmt.Errorf("no remaining voting members after remove, refuse rs.remove")
	}
	healthy := voting - failed
	if healthy*2 <= voting {
		return fmt.Errorf(
			"after remove, remaining voting members=%d healthy=%d failed=%d (%s); no strict majority, refuse rs.remove",
			voting, healthy, failed, strings.Join(failedHosts, ","),
		)
	}
	return nil
}

func rsStateToString(state string) string {
	switch state {
	case "1":
		return "PRIMARY"
	case "2":
		return "SECONDARY"
	case "3":
		return "RECOVERING"
	case "5":
		return "STARTUP2"
	case "6":
		return "UNKNOWN"
	case "7":
		return "ARBITER"
	case "8":
		return "DOWN"
	case "9":
		return "ROLLBACK"
	case "10":
		return "REMOVED"
	default:
		return "STATE_" + state
	}
}

func (r *MongoDReplace) runMongoEvalOutput(eval string) (string, error) {
	var stdoutBuf bytes.Buffer
	var stderrBuf bytes.Buffer
	cmdBuilder := mycmd.New(
		r.Mongo,
		"-u", r.ConfParams.AdminUsername,
		"-p", mycmd.Password(r.ConfParams.AdminPassword),
		"--host", r.PrimaryIP,
		"--port", strconv.Itoa(r.PrimaryPort),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", eval,
	)
	maskedCmdline := cmdBuilder.GetCmdLine("", true)
	ret, err := cmdBuilder.Run3(60*time.Second, &stdoutBuf, &stderrBuf)
	stdout := strings.TrimSpace(stdoutBuf.String())
	stderr := strings.TrimSpace(stderrBuf.String())
	if err != nil {
		r.runtime.Logger.Error(
			"run mongo eval fail, cmd:%q, exitCode:%d, stdout:%q, stderr:%q, err:%v",
			maskedCmdline, ret.ExitCode, stdout, stderr, err,
		)
		return "", fmt.Errorf("run mongo eval fail: %w", err)
	}
	if ret.ExitCode != 0 {
		r.runtime.Logger.Error(
			"run mongo eval non-zero exit, cmd:%q, exitCode:%d, stdout:%q, stderr:%q",
			maskedCmdline, ret.ExitCode, stdout, stderr,
		)
		return "", fmt.Errorf("run mongo eval non-zero exit: %d", ret.ExitCode)
	}
	return stdout, nil
}

func (r *MongoDReplace) runMongoEval(eval string) error {
	_, err := r.runMongoEvalOutput(eval)
	return err
}

// execRsRemove runs the JSON-normalized rs.remove eval and returns a typed
// *rsRemoveError when ok!=1 so removeWithRetry can match on error codes.
func (r *MongoDReplace) execRsRemove(eval string) error {
	stdout, err := r.runMongoEvalOutput(eval)
	if err != nil {
		return err
	}
	result, err := parseRsRemoveResult(stdout)
	if err != nil {
		return err
	}
	return rsRemoveResultError(result)
}

// sourceInReplicaSetConfig checks the authoritative config through the current primary.
// rs.status() is deliberately not used: a down member may be absent from status while
// still retaining voting rights in rs.conf().
func (r *MongoDReplace) sourceInReplicaSetConfig() (bool, int, error) {
	source := fmt.Sprintf("%s:%d", r.ConfParams.SourceIP, r.ConfParams.SourcePort)
	stdout, err := r.runMongoEvalOutput(buildReplicaSetConfigCheckEval(source))
	if err != nil {
		return false, 0, err
	}
	var result replicaSetConfigCheckResult
	if err := json.Unmarshal([]byte(stdout), &result); err != nil {
		return false, 0, fmt.Errorf("parse rs.conf check output %q fail: %w", stdout, err)
	}
	return result.Found, result.Version, nil
}

func (r *MongoDReplace) loadRemainingAfterRemove(source string) ([]rsRemainingMember, error) {
	stdout, err := r.runMongoEvalOutput(buildReplicaSetRemoveQuorumEval(source))
	if err != nil {
		return nil, fmt.Errorf("check remaining rs quorum before remove fail: %w", err)
	}
	var result rsRemoveQuorumCheckResult
	if err := json.Unmarshal([]byte(stdout), &result); err != nil {
		return nil, fmt.Errorf("parse remaining rs quorum check output %q fail: %w", stdout, err)
	}
	if err := validateRsQuorumAfterRemove(result.Remaining); err != nil {
		return result.Remaining, err
	}
	return result.Remaining, nil
}

func (r *MongoDReplace) checkQuorumAfterRemove() error {
	source := fmt.Sprintf("%s:%d", r.ConfParams.SourceIP, r.ConfParams.SourcePort)
	attempt := 0
	remaining, err := checkQuorumWithRetry(func() ([]rsRemainingMember, error) {
		attempt++
		members, probeErr := r.loadRemainingAfterRemove(source)
		if isStrictMajorityRefuse(probeErr) {
			r.runtime.Logger.Warn(
				"rs quorum snapshot not majority attempt=%d source=%s err=%s",
				attempt, source, probeErr.Error(),
			)
		}
		return members, probeErr
	}, quorumCheckAttempts, quorumCheckInterval, time.Sleep)
	if err != nil {
		r.runtime.Logger.Error("%s", err.Error())
		return err
	}
	if isSingleVotingSurvivor(remaining) {
		r.runtime.Logger.Warn(
			"after remove replica set keeps only one voting member, no further failover capacity source=%s",
			source,
		)
	}
	r.runtime.Logger.Info("remaining voting members keep strict majority before remove source=%s", source)
	return nil
}

// NewMongoDReplace 实例化结构体
func NewMongoDReplace() jobruntime.JobRunner {
	return &MongoDReplace{}
}

// Name 获取原子任务的名字
func (r *MongoDReplace) Name() string {
	return "mongod_replace"
}

// Run 运行原子任务
func (r *MongoDReplace) Run() error {
	// 打印替换前副本集成员状态，便于排查 primary/secondary/hidden 实际分布。
	r.logMembersBeforeReplace()

	// 主节点进行切换
	if err := r.primaryStepDown(); err != nil {
		return err
	}

	// 生成添加新节点脚本
	if err := r.makeAddTargetScript(); err != nil {
		return err
	}

	// 执行添加新节点脚本
	if err := r.execAddTargetScript(); err != nil {
		return err
	}

	// 查看新节点状态
	go r.checkTargetStatus()

	// 执行删除老节点脚本
	if err := r.checkTargetStatusAndRemoveSource(); err != nil {
		return err
	}
	// 打印替换后副本集成员状态，便于对比替换结果。
	r.logMembersAfterReplace()

	return nil
}

func (r *MongoDReplace) logMembersBeforeReplace() {
	_, _, _, _, _, memberInfo, err := common.GetNodeInfo(
		r.Mongo, r.PrimaryIP, r.PrimaryPort,
		r.ConfParams.AdminUsername, r.ConfParams.AdminPassword,
		r.PrimaryIP, r.PrimaryPort,
	)
	if err != nil {
		r.runtime.Logger.Warn(
			"print rs members status before replace failed via primary=%s:%d, err:%v",
			r.PrimaryIP, r.PrimaryPort, err,
		)
		return
	}
	r.runtime.Logger.Info(
		"rs members status before replace via primary=%s:%d (source=%s:%d target=%s:%d):",
		r.PrimaryIP, r.PrimaryPort, r.ConfParams.SourceIP, r.ConfParams.SourcePort, r.ConfParams.TargetIP, r.ConfParams.TargetPort,
	)
	for _, m := range memberInfo {
		state := m["state"]
		r.runtime.Logger.Info(
			"member=%s state=%s(%s) hidden=%s",
			m["name"], state, rsStateToString(state), m["hidden"],
		)
	}
}

func (r *MongoDReplace) logMembersAfterReplace() {
	_, _, _, _, _, memberInfo, err := common.GetNodeInfo(
		r.Mongo, r.PrimaryIP, r.PrimaryPort,
		r.ConfParams.AdminUsername, r.ConfParams.AdminPassword,
		r.PrimaryIP, r.PrimaryPort,
	)
	if err != nil {
		r.runtime.Logger.Warn(
			"print rs members status after replace failed via primary=%s:%d, err:%v",
			r.PrimaryIP, r.PrimaryPort, err,
		)
		return
	}
	r.runtime.Logger.Info(
		"rs members status after replace via primary=%s:%d (source=%s:%d target=%s:%d):",
		r.PrimaryIP, r.PrimaryPort, r.ConfParams.SourceIP, r.ConfParams.SourcePort, r.ConfParams.TargetIP, r.ConfParams.TargetPort,
	)
	for _, m := range memberInfo {
		state := m["state"]
		r.runtime.Logger.Info(
			"member=%s state=%s(%s) hidden=%s",
			m["name"], state, rsStateToString(state), m["hidden"],
		)
	}
}

// Retry 重试
func (r *MongoDReplace) Retry() uint {
	return 2
}

// Rollback 回滚
func (r *MongoDReplace) Rollback() error {
	return nil
}

// Init 初始化
func (r *MongoDReplace) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	r.runtime = runtime
	r.runtime.Logger.Info("start to init")
	r.BinDir = consts.GetMongoBinDir()
	mongoBin, err := common.ResolveMongoShellBin(r.BinDir)
	if err != nil {
		r.runtime.Logger.Error("resolve mongo shell fail, error:%s", err)
		return fmt.Errorf("resolve mongo shell fail, error:%s", err)
	}
	r.Mongo = mongoBin
	r.OsUser = consts.GetProcessUser()
	r.DataDir = consts.GetMongoDataDir()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.ConfParams); err != nil {
		r.runtime.Logger.Error("get parameters of mongodReplace fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of mongodReplace fail by json.Unmarshal, error:%s", err)
	}

	r.DbpathDir = filepath.Join(r.DataDir, "mongodata", strconv.Itoa(r.ConfParams.Port), "db")

	// 获取primary信息
	info, err := common.GetPrimaryInfo(r.Mongo, r.ConfParams.AdminUsername, r.ConfParams.AdminPassword,
		r.ConfParams.IP, r.ConfParams.Port)
	if err != nil {
		r.runtime.Logger.Error("get primary db info of mongodReplace fail, error:%s", err)
		return fmt.Errorf("get primary db info of mongodReplace fail, error:%s", err)
	}
	// 判断info是否为null
	if info == "" {
		r.runtime.Logger.Error("failed to resolve primary for mongod_replace: empty result")
		return fmt.Errorf("failed to resolve primary for mongod_replace: empty result")
	}
	getInfo := strings.Split(info, ":")
	r.PrimaryIP = getInfo[0]
	r.PrimaryPort, _ = strconv.Atoi(getInfo[1])
	r.StatusCh = make(chan int, 1)
	r.runtime.Logger.Info(
		"init resolved primary=%s:%d exec=%s:%d source=%s:%d target=%s:%d",
		r.PrimaryIP, r.PrimaryPort, r.ConfParams.IP, r.ConfParams.Port,
		r.ConfParams.SourceIP, r.ConfParams.SourcePort, r.ConfParams.TargetIP, r.ConfParams.TargetPort,
	)

	// 获取源端的配置信息
	if r.ConfParams.SourceIP != "" {
		_, _, _, hidden, priority, _, err := common.GetNodeInfo(r.Mongo, r.PrimaryIP, r.PrimaryPort,
			r.ConfParams.AdminUsername, r.ConfParams.AdminPassword, r.ConfParams.SourceIP, r.ConfParams.SourcePort)
		if err != nil {
			return err
		}
		r.TargetPriority = priority
		r.TargetHidden = hidden
	}
	if r.ConfParams.TargetHidden == "0" {
		r.TargetHidden = false
	} else if r.ConfParams.TargetHidden == "1" {
		r.TargetHidden = true
	}

	if r.ConfParams.TargetPriority != "" {
		r.TargetPriority, _ = strconv.Atoi(r.ConfParams.TargetPriority)
	}
	r.runtime.Logger.Info(
		"resolved target settings: target=%s:%d priority=%d hidden=%t",
		r.ConfParams.TargetIP, r.ConfParams.TargetPort, r.TargetPriority, r.TargetHidden,
	)

	r.runtime.Logger.Info("init successfully")

	// 进行校验
	if err = r.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (r *MongoDReplace) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	r.runtime.Logger.Info("start to validate parameters of mongodReplace")
	if err := validate.Struct(r.ConfParams); err != nil {
		r.runtime.Logger.Error("validate parameters of mongodReplace fail, error:%s", err)
		return fmt.Errorf("validate parameters of mongodReplace fail, error:%s", err)
	}
	r.runtime.Logger.Info("validate parameters of mongodReplace successfully")
	return nil
}

// makeAddTargetScript 创建添加脚本
func (r *MongoDReplace) makeAddTargetScript() error {
	if r.ConfParams.TargetIP == "" {
		return nil
	}
	addMember := common.NewReplicasetMemberAdd()
	addMember.Host = strings.Join([]string{r.ConfParams.TargetIP, strconv.Itoa(r.ConfParams.TargetPort)}, ":")
	addMember.Priority = r.TargetPriority
	addMember.Hidden = r.TargetHidden
	addMemberJson, err := addMember.GetJson()
	if err != nil {
		r.runtime.Logger.Error("get addMemberJson info fail, error:%s", err)
		return fmt.Errorf("get addMemberJson info fail, error:%s", err)
	}
	addTargetConfScript := strings.Join([]string{"rs.add(", addMemberJson, ")"}, "")
	r.AddTargetScript = addTargetConfScript
	return nil
}

// execAddTargetScript 执行添加脚本
func (r *MongoDReplace) execAddTargetScript() error {
	if r.ConfParams.TargetIP == "" {
		return nil
	}
	// 检查target是否已经存在
	flag, _, _, _, _, _, _ := common.GetNodeInfo(r.Mongo, r.PrimaryIP, r.PrimaryPort,
		r.ConfParams.AdminUsername, r.ConfParams.AdminPassword, r.ConfParams.TargetIP, r.ConfParams.TargetPort)
	if flag == true {
		r.runtime.Logger.Info("target %s already exists", strings.Join(
			[]string{r.ConfParams.TargetIP, strconv.Itoa(r.ConfParams.TargetPort)}, ":"))
		return nil
	}

	if err := r.runMongoEval(r.AddTargetScript); err != nil {
		r.runtime.Logger.Error("execute addTarget script fail, error:%s", err)
		return fmt.Errorf("execute addTarget script fail, error:%s", err)
	}
	r.runtime.Logger.Info(
		"rs.add %s:%d via primary %s:%d",
		r.ConfParams.TargetIP, r.ConfParams.TargetPort, r.PrimaryIP, r.PrimaryPort,
	)
	return nil
}

// checkTargetStatus 检查target状态
func (r *MongoDReplace) checkTargetStatus() {
	if r.ConfParams.TargetIP == "" {
		return
	}
	for {
		_, _, status, _, _, _, err := common.GetNodeInfo(r.Mongo, r.PrimaryIP, r.PrimaryPort,
			r.ConfParams.AdminUsername,
			r.ConfParams.AdminPassword, r.ConfParams.TargetIP, r.ConfParams.TargetPort)
		if err != nil {
			r.runtime.Logger.Error(
				"get target status fail target=%s:%d via primary=%s:%d, error:%s",
				r.ConfParams.TargetIP, r.ConfParams.TargetPort, r.PrimaryIP, r.PrimaryPort, err,
			)
		}
		if status != 0 {
			r.StatusCh <- status
			if status == 2 {
				stateStr := rsStateToString(strconv.Itoa(status))
				r.runtime.Logger.Info(
					"target node %s:%d status is %d(%s)",
					r.ConfParams.TargetIP, r.ConfParams.TargetPort, status, stateStr,
				)
				return
			}
		}
		time.Sleep(5 * time.Second)
	}
}

// primaryStepDown 主库切换
func (r *MongoDReplace) primaryStepDown() error {
	sourceIsPrimary := r.ConfParams.SourceIP == r.PrimaryIP && r.ConfParams.SourcePort == r.PrimaryPort
	if !sourceIsPrimary {
		r.runtime.Logger.Info("source is not primary, skip primary step down")
		return nil
	}

	_, err := common.AuthRsStepDown(r.Mongo, r.PrimaryIP, r.PrimaryPort, r.ConfParams.AdminUsername,
		r.ConfParams.AdminPassword)
	if err != nil {
		r.runtime.Logger.Error("convert primary secondary db fail, error:%s", err)
		return fmt.Errorf("convert primary secondary db fail, error:%s", err)
	}

	primaryAddr, err := common.GetPrimaryInfo(r.Mongo, r.ConfParams.AdminUsername, r.ConfParams.AdminPassword,
		r.ConfParams.IP, r.ConfParams.Port)
	if err != nil {
		r.runtime.Logger.Error("get new primary info fail, error:%s", err)
		return fmt.Errorf("get new primary info fail, error:%s", err)
	}
	sourceAddr := fmt.Sprintf("%s:%d", r.ConfParams.SourceIP, r.ConfParams.SourcePort)
	if primaryAddr != sourceAddr {
		r.runtime.Logger.Info("primary stepdown succeeded old=%s new=%s", sourceAddr, primaryAddr)
		primaryAddrSlice := strings.Split(primaryAddr, ":")
		r.PrimaryIP = primaryAddrSlice[0]
		r.PrimaryPort, _ = strconv.Atoi(primaryAddrSlice[1])
	} else {
		r.runtime.Logger.Info("primary stepdown failed, source=%s", sourceAddr)
		return fmt.Errorf("primary stepdown failed, source=%s", sourceAddr)
	}
	return nil
}

// removeSource 复制集中移除source
func (r *MongoDReplace) removeSource() error {
	if r.ConfParams.SourceIP == "" {
		return nil
	}
	// rs.conf() is the source of truth. Do not infer removal from rs.status():
	// an unhealthy member can disappear from status before it is removed from config.
	found, versionBefore, err := r.sourceInReplicaSetConfig()
	if err != nil {
		return fmt.Errorf("check source in rs.conf before remove fail: %w", err)
	}
	if !found {
		r.runtime.Logger.Info("source %s is already removed", strings.Join(
			[]string{r.ConfParams.SourceIP, strconv.Itoa(r.ConfParams.SourcePort)}, ":"))
		return nil
	}
	source := fmt.Sprintf("%s:%d", r.ConfParams.SourceIP, r.ConfParams.SourcePort)
	removeEval := buildReplicaSetRemoveEval(source)
	// Quorum is re-checked before every attempt: the retry window can span
	// ~25s, during which another voting member may go down.
	if err := removeWithRetry(
		func() error {
			if err := r.checkQuorumAfterRemove(); err != nil {
				return err
			}
			return r.execRsRemove(removeEval)
		},
		rsRemoveAttempts, rsRemoveInterval, time.Sleep,
		r.runtime.Logger.Warn,
	); err != nil {
		r.runtime.Logger.Error("execute remove source script fail, error:%s", err)
		return fmt.Errorf("execute remove source script fail, error:%s", err)
	}
	found, versionAfter, err := r.sourceInReplicaSetConfig()
	if err != nil {
		return fmt.Errorf("verify source removal in rs.conf fail: %w", err)
	}
	if found {
		return fmt.Errorf(
			"source still exists in rs.conf after rs.remove: source=%s:%d versionBefore=%d versionAfter=%d",
			r.ConfParams.SourceIP, r.ConfParams.SourcePort, versionBefore, versionAfter,
		)
	}
	r.runtime.Logger.Info(
		"rs.remove %s:%d via primary %s:%d confVersion %d->%d",
		r.ConfParams.SourceIP, r.ConfParams.SourcePort, r.PrimaryIP, r.PrimaryPort, versionBefore, versionAfter,
	)
	return nil
}

// checkTargetStatusAndRemoveSource 监控状态并移除
func (r *MongoDReplace) checkTargetStatusAndRemoveSource() error {
	// 移除老节点
	if r.ConfParams.TargetIP == "" {
		if err := r.removeSource(); err != nil {
			return err
		}
		return nil
	}
	// 先添加新节点再移除老节点，或者添加新节点
	for {
		select {
		// 超时时间
		case <-time.After(50 * time.Second):
			return fmt.Errorf(
				"timed out while waiting for target %s:%d to become SECONDARY",
				r.ConfParams.TargetIP, r.ConfParams.TargetPort,
			)
		case status := <-r.StatusCh:
			if status == 1 {
				targetAddr := fmt.Sprintf("%s:%d", r.ConfParams.TargetIP, r.ConfParams.TargetPort)
				r.runtime.Logger.Error(
					"target node %s status is PRIMARY(1), reject replace to avoid unexpected role takeover",
					targetAddr,
				)
				return fmt.Errorf("target node %s status is PRIMARY(1), abort mongod_replace", targetAddr)
			}
			if status == 2 && r.ConfParams.SourceIP != "" {
				if err := r.removeSource(); err != nil {
					return err
				}
				return nil
			} else if status == 2 && r.ConfParams.SourceIP == "" {
				return nil
			}
		}
	}
}
