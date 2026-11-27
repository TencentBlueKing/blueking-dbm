package atommongodb

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"
)

const (
	mongoshakeOpStart    = "start"
	mongoshakeOpWait     = "wait"
	mongoshakeOpWaitStop = "wait_stop"
	mongoshakeOpStop     = "stop"
	mongoshakeBinName    = "collector.linux"
	cutTargetDelaySec    = int64(3153600000) // 100 years: hold the first new batch until ExitPoint is installed.
	cutLeadSeconds       = uint32(60)
)

var mongoshakeWorkDirRe = regexp.MustCompile(`^/data/mongo-dts/mongodts[A-Za-z0-9]{1,12}$`)

// mongoshakeCollectorParam 在执行机上启动、等待追平、追平后停止或停止 MongoShake collector。
// 不在流程脚本里用 python/shell 拉起进程。
type mongoshakeCollectorParam struct {
	Op              string `json:"op"`
	WorkDir         string `json:"workDir"`
	PkgPath         string `json:"pkgPath"`
	Conf            string `json:"conf"`
	ConfFile        string `json:"confFile"`
	FullHTTPPort    int    `json:"fullHttpPort"`
	IncrHTTPPort    int    `json:"incrHttpPort"`
	LagSeconds      int    `json:"lagSeconds"`
	StableRounds    int    `json:"stableRounds"`
	PollSeconds     int    `json:"pollSeconds"`
	DeadlineSeconds int    `json:"deadlineSeconds"`
	RemoveConf      bool   `json:"removeConf"`
}

type mongoshakeCollectorJob struct {
	BaseJob
	param *mongoshakeCollectorParam
}

// NewMongoShakeCollectorJob 实例化
func NewMongoShakeCollectorJob() jobruntime.JobRunner {
	return &mongoshakeCollectorJob{}
}

func (s *mongoshakeCollectorJob) Name() string {
	return "mongoshake_collector"
}

func (s *mongoshakeCollectorJob) Param() string {
	raw, _ := json.MarshalIndent(mongoshakeCollectorParam{}, "", "\t")
	return string(raw)
}

func (s *mongoshakeCollectorJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	s.runtime = runtime
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.param); err != nil {
		return errors.Wrap(err, "payload json.Unmarshal failed")
	}
	if err := validateMongoShakeWorkDir(s.param.WorkDir); err != nil {
		return err
	}
	switch s.param.Op {
	case mongoshakeOpStart, mongoshakeOpWait, mongoshakeOpWaitStop, mongoshakeOpStop:
	default:
		return errors.Errorf("op must be start, wait, wait_stop or stop, got %s", s.param.Op)
	}
	if s.param.LagSeconds <= 0 {
		s.param.LagSeconds = 15
	}
	if s.param.StableRounds <= 0 {
		s.param.StableRounds = 3
	}
	if s.param.PollSeconds <= 0 {
		s.param.PollSeconds = 10
	}
	if s.param.DeadlineSeconds <= 0 {
		s.param.DeadlineSeconds = 82800
	}
	return nil
}

func (s *mongoshakeCollectorJob) Run() error {
	switch s.param.Op {
	case mongoshakeOpStart:
		return s.start()
	case mongoshakeOpWait:
		return s.waitCaughtUp(false)
	case mongoshakeOpWaitStop:
		return s.waitCaughtUp(true)
	case mongoshakeOpStop:
		return s.stop()
	default:
		return errors.Errorf("unknown op %s", s.param.Op)
	}
}

func validateMongoShakeWorkDir(workDir string) error {
	if !mongoshakeWorkDirRe.MatchString(workDir) {
		return errors.Errorf("workDir %s is not under /data/mongo-dts/mongodts*", workDir)
	}
	return nil
}

func (s *mongoshakeCollectorJob) start() error {
	confText, err := s.confText()
	if err != nil {
		return err
	}
	pkg := filepath.Clean(s.param.PkgPath)
	if filepath.Base(pkg) != "mongo-dts.tar.gz" || !filepath.IsAbs(pkg) || strings.Contains(s.param.PkgPath, "..") {
		return errors.Errorf("pkgPath must be an absolute mongo-dts.tar.gz")
	}
	if _, err = os.Stat(pkg); err != nil {
		return errors.Wrap(err, "pkgPath")
	}
	work := s.param.WorkDir
	unpack := filepath.Join(work, "pkg")
	if err = os.RemoveAll(unpack); err != nil {
		return errors.Wrap(err, "remove unpack dir")
	}
	if err = os.MkdirAll(filepath.Join(work, "logs"), 0755); err != nil {
		return errors.Wrap(err, "mkdir logs")
	}
	if err = os.MkdirAll(unpack, 0755); err != nil {
		return errors.Wrap(err, "mkdir unpack")
	}
	if err = untarGz(pkg, unpack); err != nil {
		return err
	}
	bin, err := findCollectorBin(unpack)
	if err != nil {
		return err
	}
	if err = os.Chmod(bin, 0755); err != nil {
		return errors.Wrap(err, "chmod collector")
	}
	confPath := filepath.Join(work, "collector.conf")
	if err = os.WriteFile(confPath, []byte(confText), 0600); err != nil {
		return errors.Wrap(err, "write collector.conf")
	}
	if alive, pid := collectorPidAlive(work); alive {
		return errors.Errorf("collector already running pid=%d", pid)
	}
	// 源端在增量起点之后一直没有写入时，wait_stop 以这个位点为起点检查源端是否有变更。
	startTs, err := sourceOpTimes(confText)
	if err != nil {
		return errors.Wrap(err, "get source operationTimes")
	}
	if err = writeStartTsMap(work, startTs); err != nil {
		return errors.Wrap(err, "write start timestamps")
	}
	stdout, err := os.OpenFile(filepath.Join(work, "collector.stdout"), os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		return errors.Wrap(err, "open collector.stdout")
	}
	defer stdout.Close()
	cmd := exec.Command(bin, "-conf="+confPath)
	cmd.Dir = work
	cmd.Stdout = stdout
	cmd.Stderr = stdout
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if err = cmd.Start(); err != nil {
		return errors.Wrap(err, "start collector")
	}
	pid := cmd.Process.Pid
	if err = os.WriteFile(filepath.Join(work, "collector.pid"), []byte(strconv.Itoa(pid)), 0644); err != nil {
		_ = cmd.Process.Kill()
		return errors.Wrap(err, "write collector.pid")
	}
	_ = cmd.Process.Release()
	time.Sleep(time.Second)
	if alive, _ := collectorPidAlive(work); !alive {
		tail, _ := os.ReadFile(filepath.Join(work, "collector.stdout"))
		return errors.Errorf("collector exited immediately: %s", tailOf(string(tail), 500))
	}
	s.logInfo("collector started pid=%d workDir=%s", pid, work)
	return nil
}

func (s *mongoshakeCollectorJob) logInfo(format string, args ...interface{}) {
	if s.runtime == nil || s.runtime.Logger == nil {
		return
	}
	s.runtime.Logger.Info(format, args...)
}

func (s *mongoshakeCollectorJob) confText() (string, error) {
	if strings.TrimSpace(s.param.Conf) != "" {
		return s.param.Conf, nil
	}
	if s.param.ConfFile == "" {
		return "", errors.New("conf or confFile is required")
	}
	clean := filepath.Clean(s.param.ConfFile)
	prefix := s.param.WorkDir + string(os.PathSeparator)
	if clean != filepath.Join(s.param.WorkDir, "collector.conf") && !strings.HasPrefix(clean, prefix) {
		return "", errors.New("confFile must be inside workDir")
	}
	raw, err := os.ReadFile(clean)
	if err != nil {
		return "", errors.Wrap(err, "read confFile")
	}
	if strings.TrimSpace(string(raw)) == "" {
		return "", errors.New("confFile is empty")
	}
	return string(raw), nil
}

// waitCaughtUp 轮询到追平。stopWhenCaught 为假时保持 collector 运行，供人工确认后再停。
func (s *mongoshakeCollectorJob) waitCaughtUp(stopWhenCaught bool) error {
	if s.param.FullHTTPPort <= 0 || s.param.IncrHTTPPort <= 0 {
		return errors.New("fullHttpPort and incrHttpPort are required")
	}
	raw, err := os.ReadFile(filepath.Join(s.param.WorkDir, "collector.conf"))
	if err != nil {
		return errors.Wrap(err, "read collector.conf")
	}
	sources, err := resolveShakeSources(string(raw))
	if err != nil {
		return err
	}
	startTs, err := readStartTsMap(s.param.WorkDir)
	if err != nil {
		return errors.Wrap(err, "read source start timestamps")
	}
	deadline := time.Now().Add(time.Duration(s.param.DeadlineSeconds) * time.Second)
	client := &http.Client{Timeout: 5 * time.Second}
	stable := 0
	seenFull := false
	var lastProgress time.Time
	for time.Now().Before(deadline) {
		alive, pid := collectorPidAlive(s.param.WorkDir)
		if !alive {
			return errors.New("collector exited before catch-up")
		}
		now := time.Now()
		logNow := shouldLogProgress(lastProgress, now)
		if !seenFull {
			progresses, progressErr := readFullProgress(client, s.param.FullHTTPPort)
			seenFull = progressErr == nil && allFullProgressFinished(progresses)
			if logNow {
				s.logFullProgress(progresses, progressErr)
				lastProgress = now
			}
			time.Sleep(time.Duration(s.param.PollSeconds) * time.Second)
			continue
		}
		repls, err := readReplLags(client, s.param.IncrHTTPPort)
		if err != nil {
			stable = 0
			if logNow {
				s.logInfo("mongoshake progress stage=incr full=100%% repl_not_ready err=%s", err.Error())
				lastProgress = now
			}
			time.Sleep(time.Duration(s.param.PollSeconds) * time.Second)
			continue
		}
		caught, detail, checkErr := s.sourcesCaughtUp(sources, startTs, repls)
		if checkErr != nil {
			caught = false
		}
		if caught {
			stable++
		} else {
			stable = 0
		}
		if logNow {
			if checkErr != nil {
				s.logInfo("mongoshake progress stage=incr source_check_failed err=%s", checkErr.Error())
			}
			s.logInfo("mongoshake progress stage=incr full=100%% %s stable=%d/%d", detail, stable, s.param.StableRounds)
			lastProgress = now
		}
		if stable >= s.param.StableRounds {
			if !stopWhenCaught {
				s.logInfo("mongoshake caught up, collector kept running pid=%d", pid)
				return nil
			}
			return s.cutAndStop(pid, sources, startTs, client, deadline)
		}
		time.Sleep(time.Duration(s.param.PollSeconds) * time.Second)
	}
	return errors.New("catch-up timeout")
}

func (s *mongoshakeCollectorJob) logFullProgress(progresses []shakeProgress, err error) {
	if err != nil {
		s.logInfo("mongoshake progress stage=full unavailable err=%s", err.Error())
		return
	}
	for _, prog := range progresses {
		s.logInfo(
			"mongoshake progress stage=full progress=%s finished=%d total=%d processing=%d waiting=%d",
			prog.Progress, prog.FinishedCollection, prog.TotalCollection, prog.ProcessingCollection, prog.WaitCollection,
		)
	}
}

// shouldLogProgress 进入等待后立刻打一次，之后每分钟一次。轮询间隔仍用于判断追平。
func shouldLogProgress(last, now time.Time) bool {
	return last.IsZero() || now.Sub(last) >= time.Minute
}

// cutAndStop first gates target writes, then installs one future whole-second ExitPoint.
// The packaged MongoShake's Shutdown sentinel deadlocks; do not use it.
func (s *mongoshakeCollectorJob) cutAndStop(
	pid int,
	sources []shakeSource,
	startTs map[string]primitive.Timestamp,
	client *http.Client,
	deadline time.Time,
) (retErr error) {
	if err := postSentinelOptions(client, s.param.IncrHTTPPort, map[string]interface{}{
		"TargetDelay": cutTargetDelaySec,
	}); err != nil {
		return errors.Wrap(err, "gate mongoshake target writes")
	}
	gateActive := true
	cutInstalled := false
	defer func() {
		if retErr != nil && cutInstalled && pidRunning(pid) {
			_ = s.signalStop(pid)
			retErr = errors.Wrap(retErr, "collector stopped after armed cut failed")
			return
		}
		if gateActive && pidRunning(pid) {
			rollbackErr := postSentinelOptions(
				client,
				s.param.IncrHTTPPort,
				map[string]interface{}{"TargetDelay": int64(0)},
			)
			if rollbackErr != nil {
				_ = s.signalStop(pid)
				if retErr == nil {
					retErr = errors.Wrap(rollbackErr, "restore TargetDelay; collector stopped")
				} else {
					retErr = errors.Wrapf(retErr, "restore TargetDelay failed (%v); collector stopped", rollbackErr)
				}
			}
		}
	}()
	stable := 0
	for time.Now().Before(deadline) {
		if !pidRunning(pid) {
			return errors.New("collector exited while gating target writes")
		}
		workers, err := readWorkers(client, s.param.IncrHTTPPort)
		if err == nil && workersDrained(workers) {
			stable++
		} else {
			stable = 0
		}
		if stable >= 2 {
			break
		}
		time.Sleep(time.Duration(s.param.PollSeconds) * time.Second)
	}
	if stable < 2 {
		return errors.New("timeout waiting mongoshake workers to drain")
	}

	var maxSourceSecond uint32
	for _, source := range sources {
		ts, err := newestOplogTimestamp(source)
		if err != nil {
			return errors.Wrapf(err, "read newest oplog for %s", source.Replset)
		}
		if ts.T > maxSourceSecond {
			maxSourceSecond = ts.T
		}
	}
	if maxSourceSecond > ^uint32(0)-cutLeadSeconds {
		return errors.New("source oplog timestamp overflow")
	}
	// TargetDelay is already holding new batches. Keep the cut far enough in the
	// future that a batch entering the gate while ExitPoint is posted cannot cross it.
	cutTs := primitive.Timestamp{T: maxSourceSecond + cutLeadSeconds}
	packedCut := int64(cutTs.T) << 32
	if err := postSentinelOptions(client, s.param.IncrHTTPPort, map[string]interface{}{
		"ExitPoint": packedCut,
	}); err != nil {
		return errors.Wrap(err, "set mongoshake ExitPoint")
	}
	cutInstalled = true
	s.logInfo("mongoshake cut installed timestamp=%d,0 packed=%d", cutTs.T, packedCut)
	if err := waitSourcesPastCut(sources, cutTs, deadline, time.Duration(s.param.PollSeconds)*time.Second); err != nil {
		return err
	}
	if err := postSentinelOptions(client, s.param.IncrHTTPPort, map[string]interface{}{
		"TargetDelay": int64(0),
	}); err != nil {
		return errors.Wrap(err, "release mongoshake target delay")
	}
	gateActive = false

	for time.Now().Before(deadline) {
		if !pidRunning(pid) {
			if collectorExitedAtCut(s.param.WorkDir) {
				s.removeConf()
				s.logInfo("mongoshake exited at cut timestamp=%d,0", cutTs.T)
				return nil
			}
			return errors.New("collector exited before confirming ExitPoint")
		}
		workers, workerErr := readWorkers(client, s.param.IncrHTTPPort)
		repls, replErr := readReplLags(client, s.param.IncrHTTPPort)
		if workerErr == nil && replErr == nil && workersDrained(workers) {
			applied, err := cutApplied(sources, startTs, repls, cutTs)
			if err != nil {
				return err
			}
			if applied {
				s.logInfo("mongoshake cut applied on every source; stopping collector pid=%d", pid)
				return s.signalStop(pid)
			}
		}
		time.Sleep(time.Duration(s.param.PollSeconds) * time.Second)
	}
	return errors.New("timeout waiting mongoshake ExitPoint")
}

func postSentinelOptions(client *http.Client, port int, values map[string]interface{}) error {
	raw, err := json.Marshal(values)
	if err != nil {
		return err
	}
	url := fmt.Sprintf("http://127.0.0.1:%d/sentinel/options", port)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(raw))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return errors.Errorf("POST %s status %d", url, resp.StatusCode)
	}
	var result map[string]string
	if err = json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return err
	}
	if result["sentinel"] != "success" {
		return errors.Errorf("POST %s failed: %s", url, result["sentinel"])
	}
	return nil
}

func newestOplogTimestamp(source shakeSource) (primitive.Timestamp, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	client, err := connectShakeSource(ctx, source)
	if err != nil {
		return primitive.Timestamp{}, err
	}
	defer client.Disconnect(context.Background())
	var row struct {
		TS primitive.Timestamp `bson:"ts"`
	}
	err = client.Database("local").Collection("oplog.rs").FindOne(
		ctx,
		bson.D{},
		options.FindOne().SetSort(bson.D{{Key: "$natural", Value: -1}}).SetProjection(bson.D{{Key: "ts", Value: 1}}),
	).Decode(&row)
	if err != nil {
		return primitive.Timestamp{}, err
	}
	if row.TS.T == 0 {
		return primitive.Timestamp{}, errors.New("newest oplog timestamp is empty")
	}
	return row.TS, nil
}

func waitSourcesPastCut(sources []shakeSource, cutTs primitive.Timestamp, deadline time.Time, poll time.Duration) error {
	for time.Now().Before(deadline) {
		allPast := true
		for _, source := range sources {
			ts, err := newestOplogTimestamp(source)
			if err != nil {
				return errors.Wrapf(err, "read newest oplog for %s", source.Replset)
			}
			if primitive.CompareTimestamp(ts, cutTs) <= 0 {
				allPast = false
				break
			}
		}
		if allPast {
			return nil
		}
		time.Sleep(poll)
	}
	return errors.New("timeout waiting every source oplog to pass cut timestamp")
}

func cutApplied(
	sources []shakeSource,
	startTs map[string]primitive.Timestamp,
	repls []shakeRepl,
	cutTs primitive.Timestamp,
) (bool, error) {
	byName := make(map[string]shakeRepl, len(repls))
	for _, repl := range repls {
		byName[repl.Replset] = repl
	}
	for _, source := range sources {
		repl, ok := byName[source.Replset]
		if !ok && len(sources) == 1 && len(repls) == 1 {
			repl, ok = repls[0], true
		}
		if !ok {
			return false, errors.Errorf("missing /repl status for %s", source.Replset)
		}
		ack, err := repl.LsnAck.packed()
		if err != nil {
			return false, err
		}
		checkpoint, err := repl.LsnCkpt.packed()
		if err != nil {
			return false, err
		}
		from := startTs[source.Replset]
		if checkpoint > 0 {
			from = packedTimestamp(checkpoint)
		}
		if ack > 0 && primitive.CompareTimestamp(packedTimestamp(ack), cutTs) > 0 {
			return false, errors.Errorf("source %s ack %v passed cut %v", source.Replset, packedTimestamp(ack), cutTs)
		}
		if primitive.CompareTimestamp(from, cutTs) == 0 {
			continue
		}
		pending, err := sourcePendingThrough(source, nextTimestamp(from), cutTs)
		if err != nil {
			return false, errors.Wrapf(err, "check cut progress for %s", source.Replset)
		}
		if pending {
			return false, nil
		}
	}
	return true, nil
}

func sourcePendingThrough(source shakeSource, since, through primitive.Timestamp) (bool, error) {
	return sourceHasPendingDML(source, since, &through)
}

func sourceHasPendingDML(source shakeSource, since primitive.Timestamp, through *primitive.Timestamp) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	client, err := connectShakeSource(ctx, source)
	if err != nil {
		return false, err
	}
	defer client.Disconnect(context.Background())
	tsRange := bson.D{{Key: "$gte", Value: since}}
	if through != nil {
		tsRange = append(tsRange, bson.E{Key: "$lte", Value: *through})
	}
	filter := bson.D{
		{Key: "ts", Value: tsRange},
		{Key: "$or", Value: oplogDMLFilters(source.Whitelist)},
	}
	err = client.Database("local").Collection("oplog.rs").FindOne(
		ctx,
		filter,
		options.FindOne().SetProjection(bson.D{{Key: "ts", Value: 1}}),
	).Err()
	if err == mongo.ErrNoDocuments {
		return false, nil
	}
	if err != nil {
		return false, errors.Wrap(err, "query source oplog")
	}
	return true, nil
}

func oplogDMLFilters(whitelist []string) bson.A {
	nsCondition := oplogNamespaceCondition(whitelist)
	dmlOps := bson.D{{Key: "$in", Value: bson.A{"i", "u", "d"}}}
	return bson.A{
		bson.D{
			{Key: "op", Value: dmlOps},
			{Key: "ns", Value: nsCondition},
		},
		bson.D{
			{Key: "op", Value: "c"},
			{Key: "o.applyOps", Value: bson.D{{Key: "$elemMatch", Value: bson.D{
				{Key: "op", Value: dmlOps},
				{Key: "ns", Value: nsCondition},
			}}}},
		},
	}
}

func oplogNamespaceCondition(whitelist []string) bson.D {
	if len(whitelist) == 0 {
		return bson.D{{Key: "$not", Value: primitive.Regex{Pattern: "^(admin|config|local)\\."}}}
	}
	patterns := make(bson.A, 0, len(whitelist))
	for _, ns := range whitelist {
		pattern := "^" + regexp.QuoteMeta(ns)
		if dbName, coll, ok := strings.Cut(ns, "."); ok {
			pattern += "$"
			patterns = append(patterns, primitive.Regex{Pattern: pattern})
			if !strings.HasPrefix(coll, "system.buckets.") {
				bucketNS := dbName + ".system.buckets." + coll
				patterns = append(patterns, primitive.Regex{Pattern: "^" + regexp.QuoteMeta(bucketNS) + "$"})
			}
		} else {
			pattern += "\\."
			patterns = append(patterns, primitive.Regex{Pattern: pattern})
		}
	}
	return bson.D{{Key: "$in", Value: patterns}}
}

func packedTimestamp(value int64) primitive.Timestamp {
	return primitive.Timestamp{T: uint32(uint64(value) >> 32), I: uint32(value)}
}

func collectorExitedAtCut(work string) bool {
	raw, err := os.ReadFile(filepath.Join(work, "collector.stdout"))
	return err == nil && strings.Contains(string(raw), "all syncer shutdown")
}

func (s *mongoshakeCollectorJob) stop() error {
	alive, pid := collectorPidAlive(s.param.WorkDir)
	if !alive {
		s.removeConf()
		s.logInfo("collector already stopped")
		return nil
	}
	return s.signalStop(pid)
}

func (s *mongoshakeCollectorJob) signalStop(pid int) error {
	_ = syscall.Kill(pid, syscall.SIGTERM)
	stopped := false
	for i := 0; i < 30; i++ {
		if !pidRunning(pid) {
			stopped = true
			break
		}
		time.Sleep(time.Second)
	}
	if !stopped {
		_ = syscall.Kill(pid, syscall.SIGKILL)
		s.logInfo("collector killed pid=%d", pid)
	} else {
		s.logInfo("collector stopped pid=%d", pid)
	}
	s.removeConf()
	return nil
}

func (s *mongoshakeCollectorJob) removeConf() {
	if !s.param.RemoveConf {
		return
	}
	_ = os.Remove(filepath.Join(s.param.WorkDir, "collector.conf"))
}

func collectorPidAlive(work string) (bool, int) {
	raw, err := os.ReadFile(filepath.Join(work, "collector.pid"))
	if err != nil {
		return false, 0
	}
	pid, err := strconv.Atoi(strings.TrimSpace(string(raw)))
	if err != nil || pid <= 0 {
		return false, 0
	}
	if !pidRunning(pid) {
		return false, pid
	}
	return true, pid
}

// pidRunning 把僵尸进程视为已退出。本进程 fork 出来的 collector 在被信号杀掉后、
// 未被 Wait 之前会停在 Z 状态，kill(pid,0) 仍然成功。
func pidRunning(pid int) bool {
	if pid <= 0 {
		return false
	}
	if err := syscall.Kill(pid, 0); err != nil {
		return false
	}
	raw, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))
	if err != nil {
		return false
	}
	text := string(raw)
	i := strings.LastIndex(text, ")")
	if i < 0 || i+2 >= len(text) {
		return true
	}
	state := text[i+2]
	return state != 'Z' && state != 'X'
}

// mongoShakeCaughtUp 用 lsn - lsn_ack 判断写入端跟上了拉取端。
// 这只是必要条件：lsn 是已拉取位点，不代表源端最新位点，源端是否还有积压由 sourcePendingAfter 判断。
// 源端写入后再空闲时 lsn/lsn_ack 相等且长期不变，ack > 0 即可；从未有增量时两者为 0，见 pendingCheckFrom。
func mongoShakeCaughtUp(lsn, ack, lagSeconds int64) (int64, bool) {
	if ack <= 0 || lsn < ack {
		return -1, false
	}
	lag := lsn - ack
	return lag, lag <= lagSeconds
}

func (s *mongoshakeCollectorJob) sourcesCaughtUp(
	sources []shakeSource,
	startTs map[string]primitive.Timestamp,
	repls []shakeRepl,
) (bool, string, error) {
	byName := make(map[string]shakeRepl, len(repls))
	for _, repl := range repls {
		if repl.Replset != "" {
			byName[repl.Replset] = repl
		}
	}
	allCaught := true
	details := make([]string, 0, len(sources))
	for _, source := range sources {
		repl, ok := byName[source.Replset]
		if !ok && len(sources) == 1 && len(repls) == 1 {
			repl, ok = repls[0], true
		}
		if !ok {
			return false, strings.Join(details, " "), errors.Errorf("missing /repl status for %s", source.Replset)
		}
		if repl.FetcherStatus != "" && repl.FetcherStatus != "normal" {
			allCaught = false
			details = append(details, fmt.Sprintf("%s(fetcher=%s)", source.Replset, repl.FetcherStatus))
			continue
		}
		lsn, ack := repl.unixLSN()
		lag, caught := mongoShakeCaughtUp(lsn, ack, int64(s.param.LagSeconds))
		pending := false
		pendingAck := ack
		if checkpoint := repl.unixCheckpoint(); checkpoint > 0 && checkpoint < pendingAck {
			pendingAck = checkpoint
		}
		if since, check := s.pendingCheckFrom(lsn, pendingAck, caught, startTs[source.Replset]); check {
			caught = true
			var err error
			pending, err = sourcePendingAfter(source, since)
			if err != nil {
				return false, strings.Join(details, " "), errors.Wrapf(err, "check source %s", source.Replset)
			}
			if pending {
				caught = false
			}
		}
		if !caught {
			allCaught = false
		}
		details = append(
			details,
			fmt.Sprintf("%s(lag=%d,pending=%t,caught=%t)", source.Replset, lag, pending, caught),
		)
	}
	return allCaught, strings.Join(details, " "), nil
}

func nextTimestamp(ts primitive.Timestamp) primitive.Timestamp {
	if ts.I == ^uint32(0) {
		return primitive.Timestamp{T: ts.T + 1}
	}
	return primitive.Timestamp{T: ts.T, I: ts.I + 1}
}

// pendingCheckFrom 返回单个源检查积压的起点。
func (s *mongoshakeCollectorJob) pendingCheckFrom(
	lsn, ack int64, caught bool, startTs primitive.Timestamp,
) (primitive.Timestamp, bool) {
	if caught {
		return primitive.Timestamp{T: uint32(ack + int64(s.param.LagSeconds) + 1)}, true
	}
	if lsn != 0 || ack != 0 {
		return primitive.Timestamp{}, false
	}
	if startTs.T == 0 {
		return primitive.Timestamp{}, false
	}
	return nextTimestamp(startTs), true
}

const collectorStartTsFile = "collector.start_ts"

// sourceOpTime 单测里替换，避免连接真实源端。
var sourceOpTimes = sourceOperationTimes

type storedTimestamp struct {
	T uint32 `json:"t"`
	I uint32 `json:"i"`
}

func writeStartTsMap(work string, timestamps map[string]primitive.Timestamp) error {
	stored := make(map[string]storedTimestamp, len(timestamps))
	for name, ts := range timestamps {
		stored[name] = storedTimestamp{T: ts.T, I: ts.I}
	}
	raw, err := json.Marshal(stored)
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(work, collectorStartTsFile), raw, 0600)
}

func readStartTsMap(work string) (map[string]primitive.Timestamp, error) {
	raw, err := os.ReadFile(filepath.Join(work, collectorStartTsFile))
	if err != nil {
		return nil, errors.Wrap(err, "read start timestamps")
	}
	var stored map[string]storedTimestamp
	if err = json.Unmarshal(raw, &stored); err != nil {
		return nil, errors.Wrap(err, "decode start timestamps")
	}
	timestamps := make(map[string]primitive.Timestamp, len(stored))
	for name, ts := range stored {
		if name == "" || ts.T == 0 {
			return nil, errors.Errorf("bad start timestamp for %q", name)
		}
		timestamps[name] = primitive.Timestamp{T: ts.T, I: ts.I}
	}
	if len(timestamps) == 0 {
		return nil, errors.New("source start timestamps are empty")
	}
	return timestamps, nil
}

type shakeSource struct {
	URI       string
	Direct    bool
	Replset   string
	Whitelist []string
}

// shakeSourceConf 是 collector.conf 中判断源端积压需要的字段。
type shakeSourceConf struct {
	Sources   []shakeSource
	Whitelist []string
}

func parseShakeSourceConf(text string) (shakeSourceConf, error) {
	kv := map[string]string{}
	for _, line := range strings.Split(text, "\n") {
		k, v, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		kv[strings.TrimSpace(k)] = strings.TrimSpace(v)
	}
	conf := shakeSourceConf{}
	direct := kv["mongo_connect_mode"] == "standalone"
	if uri := kv["mongo_s_url"]; uri != "" {
		conf.Sources = []shakeSource{{URI: uri}}
	} else {
		for _, uri := range strings.Split(kv["mongo_urls"], ";") {
			if uri = strings.TrimSpace(uri); uri != "" {
				conf.Sources = append(conf.Sources, shakeSource{URI: uri, Direct: direct})
			}
		}
	}
	if len(conf.Sources) == 0 {
		return conf, errors.New("collector.conf: mongo_s_url or mongo_urls is required")
	}
	for _, ns := range strings.Split(kv["filter.namespace.white"], ";") {
		if ns = strings.TrimSpace(ns); ns != "" {
			conf.Whitelist = append(conf.Whitelist, ns)
		}
	}
	return conf, nil
}

func connectShakeSource(ctx context.Context, source shakeSource) (*mongo.Client, error) {
	opt := options.Client().ApplyURI(source.URI).
		SetReadPreference(readpref.SecondaryPreferred()).
		SetServerSelectionTimeout(15 * time.Second)
	if source.Direct {
		opt.SetDirect(true)
	}
	client, err := mongo.Connect(ctx, opt)
	if err != nil {
		return nil, errors.Wrap(err, "connect source")
	}
	return client, nil
}

func resolveShakeSources(confText string) ([]shakeSource, error) {
	conf, err := parseShakeSourceConf(confText)
	if err != nil {
		return nil, err
	}
	seen := map[string]struct{}{}
	for i := range conf.Sources {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		client, connectErr := connectShakeSource(ctx, conf.Sources[i])
		if connectErr != nil {
			cancel()
			return nil, connectErr
		}
		raw, commandErr := client.Database("admin").RunCommand(ctx, bson.D{{Key: "isMaster", Value: 1}}).DecodeBytes()
		_ = client.Disconnect(context.Background())
		cancel()
		if commandErr != nil {
			return nil, errors.Wrap(commandErr, "isMaster source")
		}
		name, ok := raw.Lookup("setName").StringValueOK()
		if !ok || name == "" {
			name = "mongos"
		}
		if _, ok = seen[name]; ok {
			return nil, errors.Errorf("duplicated source replset %s", name)
		}
		seen[name] = struct{}{}
		conf.Sources[i].Replset = name
		conf.Sources[i].Whitelist = append([]string(nil), conf.Whitelist...)
	}
	return conf.Sources, nil
}

// sourceOperationTimes 取每个源端当前 operationTime，作为 collector 启动前的源端位点。
func sourceOperationTimes(confText string) (map[string]primitive.Timestamp, error) {
	sources, err := resolveShakeSources(confText)
	if err != nil {
		return nil, err
	}
	timestamps := make(map[string]primitive.Timestamp, len(sources))
	for _, source := range sources {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		client, connectErr := connectShakeSource(ctx, source)
		if connectErr != nil {
			cancel()
			return nil, connectErr
		}
		raw, commandErr := client.Database("admin").RunCommand(ctx, bson.D{{Key: "ping", Value: 1}}).DecodeBytes()
		_ = client.Disconnect(context.Background())
		cancel()
		if commandErr != nil {
			return nil, errors.Wrap(commandErr, "ping source")
		}
		t, i, ok := raw.Lookup("operationTime").TimestampOK()
		if !ok || t == 0 {
			return nil, errors.Errorf("source %s reply has no operationTime", source.Replset)
		}
		timestamps[source.Replset] = primitive.Timestamp{T: t, I: i}
	}
	return timestamps, nil
}

// sourcePendingAfter 直接检查 backup oplog 中尚未同步的白名单 DML。
func sourcePendingAfter(source shakeSource, since primitive.Timestamp) (bool, error) {
	return sourceHasPendingDML(source, since, nil)
}

type shakeTime struct {
	Unix int64  `json:"unix"`
	TS   string `json:"ts"`
}

type shakeRepl struct {
	Replset       string     `json:"replset"`
	Lsn           *shakeTime `json:"lsn"`
	LsnAck        *shakeTime `json:"lsn_ack"`
	LsnCkpt       *shakeTime `json:"lsn_ckpt"`
	FetcherStatus string     `json:"fetcher_status"`
}

func (r shakeRepl) unixLSN() (int64, int64) {
	var lsn, ack int64
	if r.Lsn != nil {
		lsn = r.Lsn.Unix
	}
	if r.LsnAck != nil {
		ack = r.LsnAck.Unix
	}
	return lsn, ack
}

func (r shakeRepl) unixCheckpoint() int64 {
	if r.LsnCkpt == nil {
		return 0
	}
	return r.LsnCkpt.Unix
}

func (t *shakeTime) packed() (int64, error) {
	if t == nil {
		return 0, nil
	}
	if t.TS == "" {
		return t.Unix << 32, nil
	}
	value, err := strconv.ParseInt(t.TS, 10, 64)
	if err != nil {
		return 0, errors.Wrapf(err, "parse mongoshake timestamp %q", t.TS)
	}
	return value, nil
}

type shakeProgress struct {
	Progress             string `json:"progress"`
	TotalCollection      int    `json:"total_collection_number"`
	FinishedCollection   int    `json:"finished_collection_number"`
	ProcessingCollection int    `json:"processing_collection_number"`
	WaitCollection       int    `json:"wait_collection_number"`
}

type shakeWorker struct {
	WorkerID    int `json:"worker_id"`
	JobsInQueue int `json:"jobs_in_queue"`
	JobsUnack   int `json:"jobs_unack_buffer"`
}

func readFullProgress(client *http.Client, port int) ([]shakeProgress, error) {
	return getJSONList[shakeProgress](client, fmt.Sprintf("http://127.0.0.1:%d/progress", port))
}

func allFullProgressFinished(progresses []shakeProgress) bool {
	if len(progresses) == 0 {
		return false
	}
	for _, progress := range progresses {
		if !strings.HasPrefix(strings.TrimSpace(progress.Progress), "100") {
			return false
		}
	}
	return true
}

func readReplLags(client *http.Client, port int) ([]shakeRepl, error) {
	return getJSONList[shakeRepl](client, fmt.Sprintf("http://127.0.0.1:%d/repl", port))
}

func readWorkers(client *http.Client, port int) ([]shakeWorker, error) {
	return getJSONList[shakeWorker](client, fmt.Sprintf("http://127.0.0.1:%d/worker", port))
}

func workersDrained(workers []shakeWorker) bool {
	if len(workers) == 0 {
		return false
	}
	for _, worker := range workers {
		if worker.JobsInQueue != 0 || worker.JobsUnack != 0 {
			return false
		}
	}
	return true
}

func getJSONList[T any](client *http.Client, url string) ([]T, error) {
	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, errors.Errorf("GET %s status %d", url, resp.StatusCode)
	}
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	raw = bytes.TrimSpace(raw)
	if len(raw) == 0 {
		return nil, errors.Errorf("GET %s returned an empty body", url)
	}
	if raw[0] == '[' {
		var values []T
		if err = json.Unmarshal(raw, &values); err != nil {
			return nil, err
		}
		if len(values) == 0 {
			return nil, errors.Errorf("GET %s returned an empty array", url)
		}
		return values, nil
	}
	var value T
	if err = json.Unmarshal(raw, &value); err != nil {
		return nil, err
	}
	return []T{value}, nil
}

func findCollectorBin(root string) (string, error) {
	var found string
	err := filepath.Walk(root, func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if info.IsDir() {
			return nil
		}
		if info.Name() == mongoshakeBinName {
			found = path
			return io.EOF
		}
		return nil
	})
	if err != nil && err != io.EOF {
		return "", errors.Wrap(err, "find collector.linux")
	}
	if found == "" {
		return "", errors.New("collector.linux not found in mongo-dts.tar.gz")
	}
	return found, nil
}

func untarGz(src, dst string) error {
	file, err := os.Open(src)
	if err != nil {
		return errors.Wrap(err, "open tar")
	}
	defer file.Close()
	gz, err := gzip.NewReader(file)
	if err != nil {
		return errors.Wrap(err, "gzip")
	}
	defer gz.Close()
	tr := tar.NewReader(gz)
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return errors.Wrap(err, "tar next")
		}
		name := filepath.Clean(hdr.Name)
		if name == "." || strings.HasPrefix(name, "..") || strings.Contains(name, "../") {
			return errors.Errorf("illegal tar path %s", hdr.Name)
		}
		target := filepath.Join(dst, name)
		if !strings.HasPrefix(target, dst+string(os.PathSeparator)) && target != dst {
			return errors.Errorf("tar path escapes unpack dir: %s", hdr.Name)
		}
		switch hdr.Typeflag {
		case tar.TypeDir:
			if err = os.MkdirAll(target, 0755); err != nil {
				return err
			}
		case tar.TypeReg:
			if err = os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				return err
			}
			out, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, os.FileMode(hdr.Mode)&0777)
			if err != nil {
				return err
			}
			if _, err = io.Copy(out, tr); err != nil {
				out.Close()
				return err
			}
			out.Close()
		}
	}
}

func tailOf(text string, n int) string {
	if len(text) <= n {
		return text
	}
	return text[len(text)-n:]
}
