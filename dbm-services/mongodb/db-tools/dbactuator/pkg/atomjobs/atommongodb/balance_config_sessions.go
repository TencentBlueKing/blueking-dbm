package atommongodb

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

const (
	sessionsNS                        = "config.system.sessions"
	sessionsChunkCount                = 1024
	sessionsBalanceTimeout            = 2 * time.Hour
	sessionsSplitRetries              = 3
	sessionsRetryInterval             = 2 * time.Second
	sessionsCollectionWaitTimeout     = 6 * time.Minute
	sessionsCollectionWaitInterval    = 5 * time.Second
	sessionsStopBalancerRetries       = 3
	sessionsStopBalancerRetryInterval = 5 * time.Second
)

// BalanceSessionsConfParams 均衡 config.system.sessions 的参数。
type BalanceSessionsConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
	// DbVersion 部署版本。主版本 < 6 时直接跳过。
	DbVersion string `json:"dbVersion"`
}

// BalanceConfigSessions 把 config.system.sessions 的 chunk 均衡到各个分片。
// 分割点与 MongoDB 6.0 的 1024 个 UUID 区间一致。空 chunk 按数据量均衡时会留在同一个分片上，
// 所以部署时自己 split/moveChunk，并且不打开 balancer。
type BalanceConfigSessions struct {
	BaseJob
	runtime    *jobruntime.JobGenericRuntime
	BinDir     string
	Mongo      string
	OsUser     string
	ConfParams *BalanceSessionsConfParams
}

// NewBalanceConfigSessions 实例化结构体
func NewBalanceConfigSessions() jobruntime.JobRunner {
	return &BalanceConfigSessions{}
}

// Name 原子任务名字
func (b *BalanceConfigSessions) Name() string {
	return "balance_config_sessions"
}

// Run 按 UUID 分割点 split，再用 moveChunk 把 chunk 摊到各分片，最后确认 balancer 已关闭。
func (b *BalanceConfigSessions) Run() error {
	if b.ConfParams.DbVersion != "" {
		major, err := mongodbMajorVersion(b.ConfParams.DbVersion)
		if err != nil {
			return err
		}
		if major < 6 {
			b.runtime.Logger.Info(
				"skip balance config.system.sessions, dbVersion=%s", b.ConfParams.DbVersion)
			return nil
		}
	}

	scriptPath, err := b.writeScript()
	if err != nil {
		return err
	}
	defer os.Remove(scriptPath)

	b.runtime.Logger.Info("start to balance %s", sessionsNS)
	scriptErr := b.execScript(scriptPath)
	// 脚本不打开 balancer。这里再确认一次已关闭，避免部署结束后 balancer 仍开着。
	// stopBalancer 失败不能因为脚本已有错误而忽略。
	stopErr := b.stopBalancer()
	if scriptErr != nil || stopErr != nil {
		return errors.Join(scriptErr, stopErr)
	}
	b.runtime.Logger.Info("balance %s successfully", sessionsNS)
	return nil
}

// Retry 重试
func (b *BalanceConfigSessions) Retry() uint {
	return 2
}

// Rollback 回滚
func (b *BalanceConfigSessions) Rollback() error {
	return nil
}

// Init 初始化
func (b *BalanceConfigSessions) Init(runtime *jobruntime.JobGenericRuntime) error {
	b.runtime = runtime
	b.runtime.Logger.Info("start to init")
	b.BinDir = consts.GetMongoBinDir()
	mongoBin, err := common.ResolveMongoShellBin(b.BinDir)
	if err != nil {
		b.runtime.Logger.Error("resolve mongo shell fail, error:%s", err)
		return fmt.Errorf("resolve mongo shell fail, error:%s", err)
	}
	b.Mongo = mongoBin
	b.OsUser = consts.GetProcessUser()

	if err := json.Unmarshal([]byte(b.runtime.PayloadDecoded), &b.ConfParams); err != nil {
		b.runtime.Logger.Error("get parameters of balanceConfigSessions fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of balanceConfigSessions fail by json.Unmarshal, error:%s", err)
	}
	validate := validator.New()
	if err := validate.Struct(b.ConfParams); err != nil {
		b.runtime.Logger.Error("validate parameters of balanceConfigSessions fail, error:%s", err)
		return fmt.Errorf("validate parameters of balanceConfigSessions fail, error:%s", err)
	}
	b.runtime.Logger.Info("init successfully")
	return nil
}

func (b *BalanceConfigSessions) writeScript() (string, error) {
	body := strings.ReplaceAll(sessionsBalanceScript, "__CFG__", sessionsBalanceConfig())
	file, err := os.CreateTemp("", "balance-config-sessions-*.js")
	if err != nil {
		return "", fmt.Errorf("create sessions balance script: %w", err)
	}
	path := file.Name()
	if _, err := file.WriteString(body); err != nil {
		file.Close()
		os.Remove(path)
		return "", fmt.Errorf("write sessions balance script: %w", err)
	}
	if err := file.Close(); err != nil {
		os.Remove(path)
		return "", fmt.Errorf("close sessions balance script: %w", err)
	}
	return path, nil
}

func (b *BalanceConfigSessions) stopBalancer() error {
	attempt := 0
	return retryStopBalancer(
		sessionsStopBalancerRetries,
		sessionsStopBalancerRetryInterval,
		time.Sleep,
		func() error {
			attempt++
			err := b.stopBalancerOnce()
			if err != nil {
				b.runtime.Logger.Error(
					"stop balancer after sessions balance, attempt %d/%d, error:%s",
					attempt, sessionsStopBalancerRetries, err)
			}
			return err
		},
	)
}

func (b *BalanceConfigSessions) stopBalancerOnce() error {
	_, err := mycmd.New(
		b.Mongo,
		"-u", b.ConfParams.AdminUsername,
		"-p", mycmd.Password(b.ConfParams.AdminPassword),
		"--host", b.ConfParams.IP,
		"--port", strconv.Itoa(b.ConfParams.Port),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", `
sh.stopBalancer();
var state = sh.getBalancerState();
var running = sh.isBalancerRunning();
if (state || (running && running.inBalancerRound)) {
  throw new Error("balancer is still enabled or running after stop");
}
`,
	).Run(2 * time.Minute)
	if err != nil {
		return fmt.Errorf("stop balancer after sessions balance: %w", err)
	}
	return nil
}

// retryStopBalancer 最多尝试 attempts 次。前一次失败后等待 interval，再执行下一次。
func retryStopBalancer(attempts int, interval time.Duration, sleep func(time.Duration), stop func() error) error {
	if attempts < 1 {
		return fmt.Errorf("stop balancer attempts must be positive")
	}
	var err error
	for attempt := 1; attempt <= attempts; attempt++ {
		err = stop()
		if err == nil {
			return nil
		}
		if attempt < attempts {
			sleep(interval)
		}
	}
	return err
}

func (b *BalanceConfigSessions) execScript(scriptPath string) error {
	args := []any{
		b.Mongo,
		"-u", b.ConfParams.AdminUsername,
		"-p", mycmd.Password(b.ConfParams.AdminPassword),
		"--host", b.ConfParams.IP,
		"--port", strconv.Itoa(b.ConfParams.Port),
		"--authenticationDatabase=admin",
		"--quiet",
	}
	if strings.HasSuffix(b.Mongo, "mongosh") {
		args = append(args, "--file")
	}
	args = append(args, scriptPath)

	var stderr bytes.Buffer
	stdout := &lineLogWriter{log: func(line string) { b.runtime.Logger.Info("%s", line) }}
	ret, err := mycmd.New(args...).Run3(sessionsBalanceTimeout, stdout, &stderr)
	stdout.Flush()
	if err != nil {
		if text := strings.TrimSpace(stderr.String()); text != "" {
			b.runtime.Logger.Error("%s", text)
		}
		return fmt.Errorf("balance %s fail, exitCode:%d, err:%w", sessionsNS, ret.ExitCode, err)
	}
	return nil
}

// sessionsSplitUUID 是 MongoDB balancer 切 config.system.sessions 用的第 i 个分割点。
// 1024 是 2^10，分割点取 UUID 高 10 bit 的全部排列，其余位补 0。i 从 1 到 1023。
func sessionsSplitUUID(i int) string {
	high := uint32(i) << 22
	return fmt.Sprintf("%08x-0000-0000-0000-000000000000", high)
}

func sessionsBalanceConfig() string {
	splitUUIDs := make([]string, 0, sessionsChunkCount-1)
	for i := 1; i < sessionsChunkCount; i++ {
		splitUUIDs = append(splitUUIDs, sessionsSplitUUID(i))
	}
	payload, err := json.Marshal(map[string]any{
		"ns":                     sessionsNS,
		"targetChunks":           sessionsChunkCount,
		"splitRetries":           sessionsSplitRetries,
		"retryMs":                int(sessionsRetryInterval / time.Millisecond),
		"sessionsWaitTimeoutMs":  int(sessionsCollectionWaitTimeout / time.Millisecond),
		"sessionsWaitIntervalMs": int(sessionsCollectionWaitInterval / time.Millisecond),
		"splitUUIDs":             splitUUIDs,
	})
	if err != nil {
		panic(fmt.Sprintf("marshal sessions balance config: %v", err))
	}
	return string(payload)
}

func mongodbMajorVersion(version string) (int, error) {
	raw := strings.TrimSpace(version)
	raw = strings.TrimPrefix(strings.ToLower(raw), "mongodb-")
	if raw == "" {
		return 0, fmt.Errorf("empty mongodb version")
	}
	majorText := raw
	if dot := strings.IndexByte(raw, '.'); dot >= 0 {
		majorText = raw[:dot]
	}
	major, err := strconv.Atoi(majorText)
	if err != nil {
		return 0, fmt.Errorf("parse mongodb version %q: %w", version, err)
	}
	return major, nil
}

// lineLogWriter 把脚本输出按行写进任务日志，部署时能看到等待和迁移进度。
type lineLogWriter struct {
	log func(string)
	buf []byte
}

func (w *lineLogWriter) Write(p []byte) (int, error) {
	w.buf = append(w.buf, p...)
	for {
		idx := bytes.IndexByte(w.buf, '\n')
		if idx < 0 {
			break
		}
		w.emit(w.buf[:idx])
		w.buf = w.buf[idx+1:]
	}
	return len(p), nil
}

func (w *lineLogWriter) Flush() {
	if len(w.buf) == 0 {
		return
	}
	w.emit(w.buf)
	w.buf = nil
}

func (w *lineLogWriter) emit(line []byte) {
	text := strings.TrimSpace(string(line))
	if text == "" {
		return
	}
	w.log(text)
}

// sessionsBalanceScript 在 mongos 上执行。
// 1. 关掉 balancer，避免和手工 split/moveChunk 抢同一个集合。
// 2. 等待 config server 创建 config.system.sessions 及其首个 chunk。
// 3. 没切满 1024 就按 UUID 分割点补 split。
// 4. moveChunk 按 chunk 顺序轮转到各个分片。
const sessionsBalanceScript = `
var cfg = __CFG__;
var ns = cfg.ns;

function num(v) {
  if (v === null || v === undefined) return 0;
  return Number(v);
}

// legacy mongo shell 提供 tojson；mongosh 1.10 没有，退回 EJSON/JSON。
function jstr(v) {
  try {
    return tojson(v);
  } catch (e) {
    if (typeof EJSON !== "undefined" && typeof EJSON.stringify === "function") return EJSON.stringify(v);
    return JSON.stringify(v);
  }
}

function balancerOn() {
  var r = sh.getBalancerState();
  return typeof r === "boolean" ? r : !!r;
}

function balancerRunning() {
  var r = sh.isBalancerRunning();
  return typeof r === "boolean" ? r : !!(r && r.inBalancerRound);
}

function sessionsColl() {
  return db.getSiblingDB("config").collections.findOne({_id: ns});
}

function chunkCount() {
  var coll = sessionsColl();
  if (!coll || !coll.uuid) return 0;
  return num(db.getSiblingDB("config").chunks.countDocuments({uuid: coll.uuid}));
}

function sessionsCollectionReady() {
  var coll = sessionsColl();
  return !!(coll && coll.uuid &&
    db.getSiblingDB("config").chunks.countDocuments({uuid: coll.uuid}) > 0);
}

function splitPointExists(uuid) {
  var coll = sessionsColl();
  if (!coll || !coll.uuid) return false;
  return !!db.getSiblingDB("config").chunks.findOne({
    uuid: coll.uuid,
    min: {_id: {id: UUID(uuid)}}
  });
}

function retryableSplitError(res) {
  if (!res) return true;
  var code = Number(res.code);
  if ([112, 117, 13388, 133, 63].indexOf(code) >= 0) return true;
  return /ConflictingOperationInProgress|LockBusy|LockTimeout|WriteConflict|StaleConfig/i.test(res.errmsg || "");
}

function fail(msg) {
  try { sh.stopBalancer(); } catch (e) { print("stop balancer on fail " + e); }
  print("BALANCE_SESSIONS_FAIL " + msg);
  quit(1);
}

print("stop balancer before split/move");
sh.stopBalancer();
var stopped = false;
for (var j = 0; j < 12; j++) {
  if (!balancerOn() && !balancerRunning()) { stopped = true; break; }
  sleep(5000);
}
if (!stopped) fail("balancer did not stop");

var waitStarted = Date.now();
var ready = false;
while (Date.now() - waitStarted < cfg.sessionsWaitTimeoutMs) {
  if (sessionsCollectionReady()) {
    ready = true;
    break;
  }
  print("waiting for " + ns + " to be created by config server");
  sleep(cfg.sessionsWaitIntervalMs);
}
if (!ready) {
  fail(ns + " was not created with an initial chunk within " + cfg.sessionsWaitTimeoutMs + "ms");
}

var beforeSplit = chunkCount();
print("chunks before manual split=" + beforeSplit);
if (beforeSplit < cfg.targetChunks) {
  var splitFailures = [];
  for (var k = 0; k < cfg.splitUUIDs.length; k++) {
    var splitPoint = cfg.splitUUIDs[k];
    var splitOK = splitPointExists(splitPoint);
    var last;
    for (var attempt = 1; !splitOK && attempt <= cfg.splitRetries; attempt++) {
      try {
        last = db.adminCommand({split: ns, middle: {_id: {id: UUID(splitPoint)}}});
      } catch (e) {
        last = {ok: 0, code: e.code, errmsg: e.message || String(e)};
      }
      if (last.ok == 1 || splitPointExists(splitPoint)) {
        splitOK = true;
        break;
      }
      print("split failed point=" + splitPoint + " attempt=" + attempt + " " + jstr(last));
      if (!retryableSplitError(last)) break;
      sleep(cfg.retryMs);
    }
    if (!splitOK) splitFailures.push({point: splitPoint, response: last});
    if ((k + 1) % 200 == 0) print("split progress " + (k + 1));
  }
  if (splitFailures.length > 0) fail("split failed points=" + jstr(splitFailures));
}
var afterSplit = chunkCount();
print("chunks after split=" + afterSplit);
if (afterSplit < cfg.targetChunks) fail("chunks " + afterSplit + " < " + cfg.targetChunks);

var shards = db.getSiblingDB("config").shards.find({}, {_id: 1}).sort({_id: 1}).toArray();
print("shards=" + shards.length);
if (shards.length == 0) fail("no shards");
if (shards.length == 1) {
  print("BALANCE_SESSIONS_OK single shard");
  quit(0);
}

var coll = sessionsColl();
var chunks = db.getSiblingDB("config").chunks.find({uuid: coll.uuid}, {min: 1, max: 1, shard: 1}).sort({min: 1}).toArray();
var moved = 0;
var failed = 0;
for (var c = 0; c < chunks.length; c++) {
  var dest = shards[c % shards.length]._id;
  if (chunks[c].shard == dest) continue;
  var last;
  var ok = false;
  for (var attempt = 1; attempt <= 3; attempt++) {
    try {
      last = db.adminCommand({moveChunk: ns, bounds: [chunks[c].min, chunks[c].max], to: dest});
    } catch (e) {
      last = {ok: 0, code: e.code, errmsg: e.message || String(e)};
    }
    if (last.ok == 1) { ok = true; break; }
    print("moveChunk retry " + attempt + " to " + dest + " " + jstr(last));
    sleep(2000);
  }
  if (!ok) {
    failed++;
    print("moveChunk fail to " + dest + " " + jstr(last));
    if (failed >= 5) fail("too many moveChunk errors");
    continue;
  }
  moved++;
  if (moved % 50 == 0) print("moved " + moved);
}
if (failed > 0) fail("moveChunk failed=" + failed);

var dist = db.getSiblingDB("config").chunks.aggregate([
  {$match: {uuid: coll.uuid}},
  {$group: {_id: "$shard", n: {$sum: 1}}}
]).toArray();
print("distribution " + jstr(dist));
if (dist.length != shards.length) fail("shard missing chunks");
var minC = num(dist[0].n);
var maxC = minC;
for (var d = 0; d < dist.length; d++) {
  var cnt = num(dist[d].n);
  if (cnt < minC) minC = cnt;
  if (cnt > maxC) maxC = cnt;
}
if (maxC - minC > 1) fail("unbalanced max=" + maxC + " min=" + minC);
print("BALANCE_SESSIONS_OK moved=" + moved + " chunks=" + chunks.length);
`
