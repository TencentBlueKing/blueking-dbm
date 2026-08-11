package atommongodb

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"

	"github.com/go-playground/validator/v10"
)

const (
	removeShardDefaultMaxWaitSeconds = 72 * 3600
	removeShardDefaultPollSeconds    = 30
	movePrimaryMinMajorMinor         = "4.4"
)

// RemoveShardConfParams 参数
type RemoveShardConfParams struct {
	IP                    string   `json:"ip" validate:"required"`
	Port                  int      `json:"port" validate:"required"`
	AdminUsername         string   `json:"adminUsername" validate:"required"`
	AdminPassword         string   `json:"adminPassword" validate:"required"`
	Shards                []string `json:"shards" validate:"required,min=1"`
	DbVersion             string   `json:"dbVersion" validate:"required"` // major.minor or full version for primaryShard gating
	MaxWaitSec            int      `json:"maxWaitSec"`                    // optional, default 72h
	PollSec               int      `json:"pollSec"`                       // optional, default 30s
	MovePrimaryTimeoutSec int      `json:"movePrimaryTimeoutSec"`         // optional, default 72h
}

// removeShardResult MongoDB removeShard 返回结构（精简）
type removeShardResult struct {
	Ok        int    `json:"ok"`
	Msg       string `json:"msg"`
	State     string `json:"state"`
	Shard     string `json:"shard"`
	Remaining *struct {
		Chunks int `json:"chunks"`
		DBs    int `json:"dbs"`
	} `json:"remaining"`
	ErrMsg string `json:"errmsg"`
}

type databasePrimary struct {
	ID      string `json:"_id"`
	Primary string `json:"primary"`
}

// RemoveShardFromCluster 从分片集群移除分片
type RemoveShardFromCluster struct {
	BaseJob
	runtime    *jobruntime.JobGenericRuntime
	BinDir     string
	Mongo      string
	OsUser     string
	ConfParams *RemoveShardConfParams
}

// NewRemoveShardFromCluster 实例化结构体
func NewRemoveShardFromCluster() jobruntime.JobRunner {
	return &RemoveShardFromCluster{}
}

// Name 获取原子任务的名字
func (r *RemoveShardFromCluster) Name() string {
	return "remove_shard_from_cluster"
}

// Run 运行原子任务。
// 幂等边界：先 handlePrimaryShards（多次 movePrimary）再逐个 removeOneShard。
// 重试整次 Run 是安全的：movePrimary 迁到同一目标无害；removeShard 对已 draining
// 的 shard 再次下发会继续推进直至 completed。
func (r *RemoveShardFromCluster) Run() error {
	if err := r.handlePrimaryShards(); err != nil {
		return err
	}
	for _, shardName := range r.ConfParams.Shards {
		if err := r.removeOneShard(shardName); err != nil {
			return err
		}
	}
	return nil
}

// Retry 允许整次 Run 重试。已完成的 movePrimary / 已 draining 的 removeShard 可安全重入。
func (r *RemoveShardFromCluster) Retry() uint {
	return 2
}

// Rollback 有意为空：已完成的 movePrimary / removeShard 不可安全撤销。
func (r *RemoveShardFromCluster) Rollback() error {
	return nil
}

// Init 初始化
func (r *RemoveShardFromCluster) Init(runtime *jobruntime.JobGenericRuntime) error {
	r.runtime = runtime
	r.runtime.Logger.Info("start to init remove_shard_from_cluster")
	r.BinDir = consts.GetMongoBinDir()
	r.Mongo = filepath.Join(r.BinDir, "mongodb", "bin", "mongo")
	r.OsUser = consts.GetProcessUser()

	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.ConfParams); err != nil {
		r.runtime.Logger.Error("get parameters of removeShardFromCluster fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of removeShardFromCluster fail by json.Unmarshal, error:%s", err)
	}
	if r.ConfParams.MaxWaitSec <= 0 {
		r.ConfParams.MaxWaitSec = removeShardDefaultMaxWaitSeconds
	}
	if r.ConfParams.PollSec <= 0 {
		r.ConfParams.PollSec = removeShardDefaultPollSeconds
	}
	if r.ConfParams.MovePrimaryTimeoutSec <= 0 {
		r.ConfParams.MovePrimaryTimeoutSec = removeShardDefaultMaxWaitSeconds
	}

	if err := r.checkParams(); err != nil {
		return err
	}
	r.runtime.Logger.Info("init remove_shard_from_cluster successfully")
	return nil
}

func (r *RemoveShardFromCluster) checkParams() error {
	validate := validator.New()
	r.runtime.Logger.Info("start to validate parameters of removeShardFromCluster")
	if err := validate.Struct(r.ConfParams); err != nil {
		r.runtime.Logger.Error("validate parameters of removeShardFromCluster fail, error:%s", err)
		return fmt.Errorf("validate parameters of removeShardFromCluster fail, error:%s", err)
	}
	if _, err := isMongoVersionBelow44(r.ConfParams.DbVersion); err != nil {
		r.runtime.Logger.Error("validate dbVersion of removeShardFromCluster fail, error:%s", err)
		return fmt.Errorf("validate dbVersion of removeShardFromCluster fail, error:%s", err)
	}
	r.runtime.Logger.Info("validate parameters of removeShardFromCluster successfully")
	return nil
}

func (r *RemoveShardFromCluster) handlePrimaryShards() error {
	primaryDBs, err := r.listPrimaryDatabasesOnShards(r.ConfParams.Shards)
	if err != nil {
		return err
	}
	if len(primaryDBs) == 0 {
		r.runtime.Logger.Info("no database primaryShard on shards to remove, skip movePrimary")
		return nil
	}

	below44, err := isMongoVersionBelow44(r.ConfParams.DbVersion)
	if err != nil {
		return fmt.Errorf("invalid dbVersion %q for primaryShard check: %w", r.ConfParams.DbVersion, err)
	}
	if below44 {
		return fmt.Errorf(
			"mongodb version %s (< 4.4) cannot remove shards that are primaryShard of databases: %s",
			r.ConfParams.DbVersion, formatPrimaryDBList(primaryDBs),
		)
	}

	targets, err := r.listRemainingShards()
	if err != nil {
		return err
	}
	r.runtime.Logger.Info(
		"movePrimary %d databases round-robin onto remaining shards %v (dbVersion=%s)",
		len(primaryDBs), targets, r.ConfParams.DbVersion,
	)
	for i, db := range primaryDBs {
		targetShard := targets[i%len(targets)]
		if err := r.movePrimary(db.ID, targetShard); err != nil {
			return err
		}
	}
	return nil
}

func isMongoVersionBelow44(version string) (bool, error) {
	if strings.TrimSpace(version) == "" {
		return false, fmt.Errorf("dbVersion is required when databases use removing shards as primaryShard")
	}
	left, err := parseMongoVersionTuple(version)
	if err != nil {
		return false, err
	}
	right, err := parseMongoVersionTuple(movePrimaryMinMajorMinor)
	if err != nil {
		return false, err
	}
	return compareMongoVersionTuples(left, right) < 0, nil
}

func formatPrimaryDBList(dbs []databasePrimary) string {
	parts := make([]string, 0, len(dbs))
	for _, db := range dbs {
		parts = append(parts, fmt.Sprintf("%s(primary=%s)", db.ID, db.Primary))
	}
	return strings.Join(parts, ", ")
}

func filterPrimaryDBsOnShards(dbs []databasePrimary, removeShards []string) []databasePrimary {
	removeSet := make(map[string]struct{}, len(removeShards))
	for _, shard := range removeShards {
		removeSet[shard] = struct{}{}
	}
	var matched []databasePrimary
	for _, db := range dbs {
		if _, ok := removeSet[db.Primary]; ok {
			matched = append(matched, db)
		}
	}
	return matched
}

// remainingShards returns shards in allShards that are not in removeShards, preserving order.
func remainingShards(allShards []string, removeShards []string) ([]string, error) {
	removeSet := make(map[string]struct{}, len(removeShards))
	for _, shard := range removeShards {
		removeSet[shard] = struct{}{}
	}
	var remaining []string
	for _, shard := range allShards {
		if _, removing := removeSet[shard]; !removing {
			remaining = append(remaining, shard)
		}
	}
	if len(remaining) == 0 {
		return nil, fmt.Errorf("no remaining shard available as movePrimary target")
	}
	return remaining, nil
}

// pickTargetShard returns the i-th remaining shard round-robin (i >= 0).
func pickTargetShard(allShards []string, removeShards []string, i int) (string, error) {
	remaining, err := remainingShards(allShards, removeShards)
	if err != nil {
		return "", err
	}
	if i < 0 {
		i = 0
	}
	return remaining[i%len(remaining)], nil
}

func (r *RemoveShardFromCluster) listPrimaryDatabasesOnShards(removeShards []string) ([]databasePrimary, error) {
	evalScript := `JSON.stringify(db.getSiblingDB("config").databases.find({},{_id:1,primary:1}).toArray())`
	stdout, err := r.runMongoEval(evalScript, 60*time.Second)
	if err != nil {
		return nil, fmt.Errorf("list config.databases fail: %w", err)
	}
	dbs, err := parseDatabasePrimaries(stdout)
	if err != nil {
		return nil, fmt.Errorf("parse config.databases fail, stdout:%q: %w", stdout, err)
	}
	return filterPrimaryDBsOnShards(dbs, removeShards), nil
}

func parseDatabasePrimaries(stdout string) ([]databasePrimary, error) {
	output := strings.TrimSpace(stdout)
	if output == "" || output == "null" {
		return nil, nil
	}
	var dbs []databasePrimary
	if err := json.Unmarshal([]byte(output), &dbs); err == nil {
		return dbs, nil
	}
	start := strings.Index(output, "[")
	end := strings.LastIndex(output, "]")
	if start < 0 || end <= start {
		return nil, fmt.Errorf("no json array found")
	}
	if err := json.Unmarshal([]byte(output[start:end+1]), &dbs); err != nil {
		return nil, err
	}
	return dbs, nil
}

func (r *RemoveShardFromCluster) listAllShardNames() ([]string, error) {
	evalScript := `JSON.stringify(db.getSiblingDB("config").shards.distinct("_id"))`
	stdout, err := r.runMongoEval(evalScript, 60*time.Second)
	if err != nil {
		return nil, fmt.Errorf("list config.shards fail: %w", err)
	}
	return parseShardNameList(stdout)
}

func parseShardNameList(stdout string) ([]string, error) {
	output := strings.TrimSpace(stdout)
	if output == "" || output == "null" {
		return nil, nil
	}
	var shards []string
	if err := json.Unmarshal([]byte(output), &shards); err == nil {
		return shards, nil
	}
	start := strings.Index(output, "[")
	end := strings.LastIndex(output, "]")
	if start < 0 || end <= start {
		return nil, fmt.Errorf("no json array found")
	}
	if err := json.Unmarshal([]byte(output[start:end+1]), &shards); err != nil {
		return nil, err
	}
	return shards, nil
}

func (r *RemoveShardFromCluster) listRemainingShards() ([]string, error) {
	allShards, err := r.listAllShardNames()
	if err != nil {
		return nil, err
	}
	return remainingShards(allShards, r.ConfParams.Shards)
}

func (r *RemoveShardFromCluster) movePrimary(dbName, toShard string) error {
	dbJSON, err := json.Marshal(dbName)
	if err != nil {
		return fmt.Errorf("marshal db name fail: %w", err)
	}
	toJSON, err := json.Marshal(toShard)
	if err != nil {
		return fmt.Errorf("marshal target shard fail: %w", err)
	}
	evalScript := fmt.Sprintf(
		`db.adminCommand({movePrimary: %s, to: %s})`,
		string(dbJSON), string(toJSON),
	)
	timeout := time.Duration(r.ConfParams.MovePrimaryTimeoutSec) * time.Second
	r.runtime.Logger.Info("start movePrimary db=%s to=%s timeout=%ds", dbName, toShard, r.ConfParams.MovePrimaryTimeoutSec)
	stdout, err := r.runMongoEval(evalScript, timeout)
	if err != nil {
		return fmt.Errorf("movePrimary db=%s to=%s fail: %w, stdout:%s", dbName, toShard, err, stdout)
	}
	if err := checkMovePrimaryOK(stdout); err != nil {
		return fmt.Errorf("movePrimary db=%s to=%s rejected: %w, stdout:%s", dbName, toShard, err, stdout)
	}

	// getDatabasePrimary is required: checkMovePrimaryOK treats empty legacy-shell stdout as OK.
	primary, err := r.getDatabasePrimary(dbName)
	if err != nil {
		return fmt.Errorf("verify movePrimary db=%s fail: %w", dbName, err)
	}
	if primary != toShard {
		return fmt.Errorf("movePrimary db=%s expected primary=%s, got %s", dbName, toShard, primary)
	}
	r.runtime.Logger.Info("movePrimary db=%s to=%s successfully", dbName, toShard)
	return nil
}

func checkMovePrimaryOK(stdout string) error {
	output := strings.TrimSpace(stdout)
	var result struct {
		Ok     int    `json:"ok"`
		ErrMsg string `json:"errmsg"`
	}
	if err := json.Unmarshal([]byte(output), &result); err != nil {
		start := strings.Index(output, "{")
		end := strings.LastIndex(output, "}")
		if start < 0 || end <= start {
			// legacy shell may print empty on success; callers MUST verify via getDatabasePrimary.
			if output == "" {
				return nil
			}
			lower := strings.ToLower(output)
			if strings.Contains(lower, `"ok" : 1`) || strings.Contains(lower, `"ok":1`) {
				return nil
			}
			return fmt.Errorf("unparseable movePrimary result")
		}
		snippet := output[start : end+1]
		if err2 := json.Unmarshal([]byte(snippet), &result); err2 != nil {
			lower := strings.ToLower(snippet)
			if strings.Contains(lower, `"ok" : 1`) || strings.Contains(lower, `"ok":1`) {
				return nil
			}
			return err2
		}
	}
	if result.Ok == 0 {
		if result.ErrMsg != "" {
			return fmt.Errorf("%s", result.ErrMsg)
		}
		return fmt.Errorf("ok=0")
	}
	return nil
}

func (r *RemoveShardFromCluster) getDatabasePrimary(dbName string) (string, error) {
	dbJSON, err := json.Marshal(dbName)
	if err != nil {
		return "", err
	}
	evalScript := fmt.Sprintf(
		`var d=db.getSiblingDB("config").databases.findOne({_id:%s},{primary:1}); print(d && d.primary ? d.primary : "")`,
		string(dbJSON),
	)
	stdout, err := r.runMongoEval(evalScript, 60*time.Second)
	if err != nil {
		return "", err
	}
	primary := strings.TrimSpace(stdout)
	lines := strings.Split(primary, "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if line != "" {
			return line, nil
		}
	}
	return "", fmt.Errorf("empty primary for db %s", dbName)
}

func (r *RemoveShardFromCluster) runMongoEval(evalScript string, timeout time.Duration) (string, error) {
	cmdBuilder := mycmd.New(
		r.Mongo,
		"-u", r.ConfParams.AdminUsername,
		"-p", mycmd.Password(r.ConfParams.AdminPassword),
		"--host", r.ConfParams.IP,
		"--port", strconv.Itoa(r.ConfParams.Port),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", evalScript,
		"admin",
	)
	masked := cmdBuilder.GetCmdLine("", true)
	ret, err := cmdBuilder.Run(timeout)
	stdout := ""
	if ret != nil {
		stdout = strings.TrimSpace(ret.GetStdout())
	}
	if err != nil {
		r.runtime.Logger.Error("mongo eval fail, cmd:%q, err:%v, stdout:%q", masked, err, stdout)
		return stdout, err
	}
	return stdout, nil
}

func (r *RemoveShardFromCluster) removeOneShard(shardName string) error {
	r.runtime.Logger.Info("start to remove shard:%s", shardName)

	exists, err := r.shardExists(shardName)
	if err != nil {
		return err
	}
	if !exists {
		r.runtime.Logger.Info("shard:%s already absent in cluster, skip", shardName)
		return nil
	}

	deadline := time.Now().Add(time.Duration(r.ConfParams.MaxWaitSec) * time.Second)
	for {
		result, err := r.execRemoveShard(shardName)
		if err != nil {
			return err
		}
		state := strings.ToLower(strings.TrimSpace(result.State))
		r.runtime.Logger.Info(
			"removeShard shard=%s state=%s msg=%s remaining=%v",
			shardName, result.State, result.Msg, result.Remaining,
		)
		if state == "completed" {
			exists, err := r.shardExists(shardName)
			if err != nil {
				return fmt.Errorf("verify shard:%s removed fail: %w", shardName, err)
			}
			if exists {
				return fmt.Errorf("remove shard:%s reported completed but shard still exists in config.shards", shardName)
			}
			r.runtime.Logger.Info("remove shard:%s completed and verified absent from config.shards", shardName)
			return nil
		}
		if time.Now().After(deadline) {
			return fmt.Errorf(
				"remove shard:%s timeout after %ds, last state=%s msg=%s remaining=%v",
				shardName, r.ConfParams.MaxWaitSec, result.State, result.Msg, result.Remaining,
			)
		}
		time.Sleep(time.Duration(r.ConfParams.PollSec) * time.Second)
	}
}

func (r *RemoveShardFromCluster) shardExists(shardName string) (bool, error) {
	shardJSON, err := json.Marshal(shardName)
	if err != nil {
		return false, fmt.Errorf("marshal shard name fail: %w", err)
	}
	evalScript := fmt.Sprintf(
		`db.getSiblingDB("config").shards.count({_id: %s})`,
		string(shardJSON),
	)
	stdout, err := r.runMongoEval(evalScript, 60*time.Second)
	if err != nil {
		return false, fmt.Errorf("check shard existence fail: %w", err)
	}
	count, err := parseShardCount(stdout)
	if err != nil {
		return false, fmt.Errorf("parse shard count fail, stdout:%q: %w", stdout, err)
	}
	return count > 0, nil
}

func parseShardCount(stdout string) (int, error) {
	output := strings.TrimSpace(stdout)
	lines := strings.Split(output, "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			continue
		}
		count, err := strconv.Atoi(line)
		if err != nil {
			return 0, fmt.Errorf("invalid shard count %q", line)
		}
		return count, nil
	}
	return 0, fmt.Errorf("empty shard count output")
}

func (r *RemoveShardFromCluster) execRemoveShard(shardName string) (*removeShardResult, error) {
	// removeShard must be issued repeatedly until completed; use adminCommand JSON form.
	evalScript := fmt.Sprintf(`db.adminCommand({removeShard: "%s"})`, shardName)
	stdout, err := r.runMongoEval(evalScript, 120*time.Second)
	if err != nil {
		return nil, fmt.Errorf("execute removeShard fail: %w", err)
	}
	parsed, err := parseRemoveShardResult(stdout)
	if err != nil {
		r.runtime.Logger.Error("parse removeShard result fail, stdout:%q, err:%v", stdout, err)
		return nil, fmt.Errorf("parse removeShard result fail: %w, stdout:%s", err, stdout)
	}
	if parsed.Ok == 0 && parsed.ErrMsg != "" {
		return nil, fmt.Errorf("removeShard command error: %s", parsed.ErrMsg)
	}
	return parsed, nil
}

func parseRemoveShardResult(stdout string) (*removeShardResult, error) {
	// mongo shell may print Extended JSON; try direct json first, then extract outermost object.
	var result removeShardResult
	if err := json.Unmarshal([]byte(stdout), &result); err == nil {
		return &result, nil
	}
	start := strings.Index(stdout, "{")
	end := strings.LastIndex(stdout, "}")
	if start < 0 || end <= start {
		return nil, fmt.Errorf("no json object found")
	}
	snippet := stdout[start : end+1]
	// legacy shell may use unquoted keys; replace common keys for a best-effort parse
	snippet = strings.ReplaceAll(snippet, "NumberLong(", "")
	snippet = strings.ReplaceAll(snippet, ")", "")
	if err := json.Unmarshal([]byte(snippet), &result); err != nil {
		// Fall back to regex-ish field extraction via simple contains for state.
		lower := strings.ToLower(snippet)
		if strings.Contains(lower, `"state" : "completed"`) || strings.Contains(lower, `"state":"completed"`) ||
			strings.Contains(lower, "state : \"completed\"") || strings.Contains(lower, "state: \"completed\"") {
			return &removeShardResult{Ok: 1, State: "completed"}, nil
		}
		if strings.Contains(lower, "completed") && strings.Contains(lower, "state") {
			return &removeShardResult{Ok: 1, State: "completed"}, nil
		}
		if strings.Contains(lower, "ongoing") || strings.Contains(lower, "started") || strings.Contains(lower, "draining") {
			state := "ongoing"
			if strings.Contains(lower, "started") {
				state = "started"
			}
			return &removeShardResult{Ok: 1, State: state, Msg: snippet}, nil
		}
		return nil, err
	}
	return &result, nil
}
