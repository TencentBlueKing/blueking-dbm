package atomredis

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/rollback"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// RedisRollbackParams holds parameters for redis rollback.
type RedisRollbackParams struct {
	DestIP    string `json:"dest_ip" validate:"required"`
	DestDir   string `json:"dest_dir"`
	RecoverAt string `json:"recover_at"`
	// MaxConcurrency only lowers the per-stage limits sized from the host; 0 leaves them.
	MaxConcurrency int `json:"max_concurrency"`
	// WriteBufferMB is the Tendisplus temp instances' write buffer for the replay; 0, as older
	// payloads send it, keeps the conf template's.
	WriteBufferMB int `json:"write_buffer_mb"`
	// AllowBinlogNonconsecutive is the plan's: binlog chains may skip indexes. Older payloads leave
	// it out, and their chains are only checked against the plan's digest.
	AllowBinlogNonconsecutive *bool `json:"allow_binlog_nonconsecutive"`
	// HeartbeatToleranceSec bounds a Tendisplus source heartbeat's distance from recover_at; 0 is
	// the default, 10 minutes as in v1.
	HeartbeatToleranceSec int                        `json:"heartbeat_tolerance_sec"`
	Install               json.RawMessage            `json:"install"`
	Instances             []rollback.InstanceRestore `json:"instances" validate:"required"`
}

// RedisRollback restores redis instances from backup files, dispatching on the storage engine.
type RedisRollback struct {
	runtime *jobruntime.JobGenericRuntime
	params  RedisRollbackParams
}

var _ jobruntime.JobRunner = (*RedisRollback)(nil)

// NewRedisRollback creates a new rollback runner.
func NewRedisRollback() jobruntime.JobRunner {
	return &RedisRollback{}
}

// Init validates params and initializes runtime.
func (job *RedisRollback) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	if err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params); err != nil {
		job.runtime.Logger.Error("json.Unmarshal failed,err:%+v", err)
		return err
	}
	validate := validator.New()
	if err := validate.Struct(job.params); err != nil {
		job.runtime.Logger.Error("RedisRollback Init params validate failed,err:%v,params:%+v", err, job.params)
		return err
	}
	if len(job.params.Instances) == 0 {
		return fmt.Errorf("RedisRollback instances empty")
	}
	if len(job.params.Install) == 0 {
		return fmt.Errorf("RedisRollback install params empty")
	}
	return nil
}

// Name returns atom job name.
func (job *RedisRollback) Name() string {
	return "redis_rollback"
}

// Retry returns 0: jobmanager does not retry atom jobs; bamboo node retry re-runs Run.
func (job *RedisRollback) Retry() uint {
	return 0
}

// Rollback cleans up on task failure.
func (job *RedisRollback) Rollback() error {
	return nil
}

// Run hands the instances to the restorer of the cluster's storage engine.
func (job *RedisRollback) Run() error {
	install, err := job.initInstall()
	if err != nil {
		return err
	}
	restorer, err := rollback.New(install.params.DbType, rollback.Job{
		DestIP:                    job.params.DestIP,
		SaveDir:                   job.params.DestDir,
		UnpackDir:                 rollbackUnpackDir(install),
		RecoverAt:                 job.params.RecoverAt,
		MaxConcurrency:            job.params.MaxConcurrency,
		WriteBufferMB:             job.params.WriteBufferMB,
		AllowBinlogNonconsecutive: job.params.AllowBinlogNonconsecutive,
		HeartbeatTolerance:        time.Duration(job.params.HeartbeatToleranceSec) * time.Second,
		Instances:                 job.params.Instances,
		Host:                      &rollbackHost{install: install, ip: job.params.DestIP, runtime: job.runtime},
	})
	if err != nil {
		job.runtime.Logger.Error("RedisRollback: %v", err)
		return err
	}
	return restorer.DoRollback()
}

// initInstall creates a RedisInstall runner to reuse its directory and media setup.
func (job *RedisRollback) initInstall() (*RedisInstall, error) {
	installRuntime := *job.runtime
	installRuntime.PayloadDecoded = string(job.params.Install)
	install := &RedisInstall{}
	if err := install.Init(&installRuntime); err != nil {
		job.runtime.Logger.Error("RedisRollback install init failed: %v", err)
		return nil, err
	}
	if err := install.GetRealDataDir(); err != nil {
		return nil, err
	}
	return install, nil
}

// rollbackUnpackDir sits next to the instances' own dir, e.g. /data1/recover_redis beside
// /data1/redis, so unpacked data is on their filesystem.
func rollbackUnpackDir(install *RedisInstall) string {
	if install.RealDataDir != "" {
		return filepath.Join(filepath.Dir(install.RealDataDir), "recover_redis")
	}
	return rollback.DefaultUnpackDir()
}

// rollbackHost implements rollback.Host on top of RedisInstall.
type rollbackHost struct {
	install *RedisInstall
	ip      string
	runtime *jobruntime.JobGenericRuntime
}

func (h *rollbackHost) InstallTools() error {
	return h.install.params.DbToolsPkg.Install()
}

func (h *rollbackHost) Prepare(ports []int) error {
	h.install.params.Ports = ports
	return h.install.Prepare()
}

// InstanceDir returns instance data directory, e.g. /data/redis/{port}.
func (h *rollbackHost) InstanceDir(port int) string {
	if h.install.RealDataDir != "" {
		return filepath.Join(h.install.RealDataDir, strconv.Itoa(port))
	}
	return filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(port))
}

// Start starts a single instance under mysql user without requiring an empty db.
// Exporter configs are intentionally skipped for temporary rollback instances.
func (h *rollbackHost) Start(port int) error {
	binDir := h.install.RedisBinDir
	if binDir == "" {
		binDir = filepath.Join(consts.UsrLocal, "redis", "bin")
	}
	startScript := filepath.Join(binDir, "start-redis.sh")
	_, err := util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c",
		startScript + "  " + strconv.Itoa(port)}, "", nil, 20*time.Minute)
	if err != nil {
		return fmt.Errorf("su %s -c \"%s %d\": %v", consts.MysqlAaccount, startScript, port, err)
	}
	return nil
}

func (h *rollbackHost) Stop(port int) error {
	return stopRedisViaScript(h.ip, port, h.runtime.Logger)
}

func (h *rollbackHost) MediaName() string {
	return h.install.params.GePkgBaseName()
}

// ProcessID finds the instance by its redis.conf, which start-redis.sh passes on its command line.
func (h *rollbackHost) ProcessID(port int) (int, uint64, error) {
	return rollback.ProcessByArg(filepath.Join(h.InstanceDir(port), "redis.conf"))
}
