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
)

// RemoveShardConfParams 参数
type RemoveShardConfParams struct {
	IP            string   `json:"ip" validate:"required"`
	Port          int      `json:"port" validate:"required"`
	AdminUsername string   `json:"adminUsername" validate:"required"`
	AdminPassword string   `json:"adminPassword" validate:"required"`
	Shards        []string `json:"shards" validate:"required,min=1"`
	MaxWaitSec    int      `json:"maxWaitSec"` // optional, default 72h
	PollSec       int      `json:"pollSec"`    // optional, default 30s
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

// Run 运行原子任务
func (r *RemoveShardFromCluster) Run() error {
	for _, shardName := range r.ConfParams.Shards {
		if err := r.removeOneShard(shardName); err != nil {
			return err
		}
	}
	return nil
}

// Retry 重试
func (r *RemoveShardFromCluster) Retry() uint {
	return 2
}

// Rollback 回滚
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
	r.runtime.Logger.Info("validate parameters of removeShardFromCluster successfully")
	return nil
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
	ret, err := cmdBuilder.Run(60 * time.Second)
	if err != nil {
		r.runtime.Logger.Error("check shard existence fail, cmd:%q, err:%v", masked, err)
		return false, fmt.Errorf("check shard existence fail: %w", err)
	}
	count, err := parseShardCount(ret.GetStdout())
	if err != nil {
		return false, fmt.Errorf("parse shard count fail, stdout:%q: %w", ret.GetStdout(), err)
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
	ret, err := cmdBuilder.Run(120 * time.Second)
	if err != nil {
		r.runtime.Logger.Error("execute removeShard fail, cmd:%q, err:%v, stdout:%q", masked, err, ret.GetStdout())
		return nil, fmt.Errorf("execute removeShard fail: %w", err)
	}
	stdout := strings.TrimSpace(ret.GetStdout())
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
