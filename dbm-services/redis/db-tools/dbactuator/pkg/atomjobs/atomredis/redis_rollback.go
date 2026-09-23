package atomredis

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/rollback"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// RollbackInstance describes a target instance and its backup files.
type RollbackInstance struct {
	SourceIP    string   `json:"source_ip"`
	SourcePort  int      `json:"source_port"`
	DestPort    int      `json:"dest_port" validate:"required"`
	FullFiles   []string `json:"full_files"`
	BinlogFiles []string `json:"binlog_files"`
}

// RedisRollbackParams holds parameters for redis rollback.
type RedisRollbackParams struct {
	DestIP    string             `json:"dest_ip" validate:"required"`
	DestDir   string             `json:"dest_dir"`
	RecoverAt string             `json:"recover_at"`
	Install   json.RawMessage    `json:"install"`
	Instances []RollbackInstance `json:"instances" validate:"required"`
}

// RedisRollback restores cache redis instances from backup files.
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

// Run prepares instances and restores cache full backups.
func (job *RedisRollback) Run() error {
	install, err := job.initInstall()
	if err != nil {
		return err
	}

	redo, resume, err := job.resolvePending(install)
	if err != nil {
		return err
	}
	if len(redo) == 0 && len(resume) == 0 {
		job.runtime.Logger.Info("RedisRollback %s: all ports already rolled back, nothing to do", job.params.DestIP)
		return nil
	}

	saveDir := job.params.DestDir
	if saveDir == "" {
		saveDir = rollback.DefaultSaveDir()
	}
	job.runtime.Logger.Info("RedisRollback dest_ip=%s dest_dir=%s redo=%d resume=%d total=%d",
		job.params.DestIP, saveDir, len(redo), len(resume), len(job.params.Instances))

	if len(redo) > 0 {
		staged, err := job.stageBackups(saveDir, redo)
		if err != nil {
			return err
		}

		install.params.Ports = portsOf(redo)
		if err = install.Prepare(); err != nil {
			job.runtime.Logger.Error("RedisRollback prepare instances failed: %v", err)
			return err
		}

		if err = job.applyBackups(install, redo, staged); err != nil {
			return err
		}
		if err = job.startAll(install, redo); err != nil {
			return err
		}
	}
	return job.waitAndMark(install, saveDir, append(redo, resume...))
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

// resolvePending splits instances into ports to restore from scratch and ports to only wait on.
// Completed ports with matching fingerprints are skipped so bamboo retries do not fail
// on in-use ports. A running port started from this same backup (pending marker) may
// still be loading, so it is resumed rather than killed. Any other running port is redone.
func (job *RedisRollback) resolvePending(install *RedisInstall) (redo, resume []RollbackInstance, err error) {
	for _, inst := range job.params.Instances {
		instDir := job.instanceDir(install, inst.DestPort)
		fingerprint := rollback.Fingerprint(inst.FullFiles)
		inUse, err := util.CheckPortIsInUse(job.params.DestIP, strconv.Itoa(inst.DestPort))
		if err != nil {
			return nil, nil, err
		}
		switch {
		case inUse && rollback.IsDone(instDir, fingerprint):
			job.runtime.Logger.Info("dest_port=%d already rolled back with the same backup, skip", inst.DestPort)
			continue
		case inUse && rollback.IsPending(instDir, fingerprint):
			job.runtime.Logger.Info("dest_port=%d was started from the same backup, resume waiting", inst.DestPort)
			resume = append(resume, inst)
			continue
		case inUse:
			job.runtime.Logger.Info("dest_port=%d is in use without a matching marker, stop it and redo",
				inst.DestPort)
			rollback.ClearDone(instDir)
			if err = stopRedisViaScript(job.params.DestIP, inst.DestPort, job.runtime.Logger); err != nil {
				return nil, nil, err
			}
		}
		redo = append(redo, inst)
	}
	return redo, resume, nil
}

// stageBackups unpacks full backups and identifies persistence format (AOF/RDB).
// Placeholder instances without backup files are skipped.
func (job *RedisRollback) stageBackups(
	saveDir string, pending []RollbackInstance,
) (map[int]rollback.StagedBackup, error) {
	staged := make(map[int]rollback.StagedBackup, len(pending))
	var mu sync.Mutex
	err := rollback.RunBounded(len(pending), rollback.StageConcurrency(), func(i int) error {
		inst := pending[i]
		if len(inst.FullFiles) == 0 {
			job.runtime.Logger.Info("dest_port=%d has no full files, keep it empty", inst.DestPort)
			return nil
		}
		job.runtime.Logger.Info("stage source=%s:%d dest_port=%d files=%v",
			inst.SourceIP, inst.SourcePort, inst.DestPort, inst.FullFiles)
		item, err := rollback.StageBackup(saveDir, toRestore(inst))
		if err != nil {
			job.runtime.Logger.Error("RedisRollback stage %s:%d -> %d failed: %v",
				inst.SourceIP, inst.SourcePort, inst.DestPort, err)
			return err
		}
		mu.Lock()
		staged[inst.DestPort] = item
		mu.Unlock()
		return nil
	})
	if err != nil {
		return nil, err
	}
	return staged, nil
}

func toRestore(inst RollbackInstance) rollback.InstanceRestore {
	return rollback.InstanceRestore{
		SourceIP:    inst.SourceIP,
		SourcePort:  inst.SourcePort,
		DestPort:    inst.DestPort,
		FullFiles:   inst.FullFiles,
		BinlogFiles: inst.BinlogFiles,
	}
}

// applyBackups updates appendonly in redis.conf and moves staged data files into place before startup.
func (job *RedisRollback) applyBackups(
	install *RedisInstall, pending []RollbackInstance, staged map[int]rollback.StagedBackup,
) error {
	for _, inst := range pending {
		instDir := job.instanceDir(install, inst.DestPort)
		// Placeholder instances have nothing staged and keep default persistence from dbconfig.
		if item, ok := staged[inst.DestPort]; ok {
			if err := rollback.SetAppendonly(filepath.Join(instDir, "redis.conf"), item.IsAOF); err != nil {
				job.runtime.Logger.Error("RedisRollback set appendonly for %d failed: %v", inst.DestPort, err)
				return err
			}
			if err := rollback.PlaceDataFile(filepath.Join(instDir, "data"), item); err != nil {
				job.runtime.Logger.Error("RedisRollback place data file for %d failed: %v", inst.DestPort, err)
				return err
			}
		}
		if err := rollback.MarkPending(instDir, rollback.Fingerprint(inst.FullFiles)); err != nil {
			return err
		}
	}
	return nil
}

// startAll starts every instance before waiting, so large data files load in parallel.
// Exporter configs are intentionally skipped for temporary rollback instances.
func (job *RedisRollback) startAll(install *RedisInstall, pending []RollbackInstance) error {
	for _, inst := range pending {
		if err := job.startInstance(install, inst.DestPort); err != nil {
			job.runtime.Logger.Error("RedisRollback start %s:%d failed: %v", job.params.DestIP, inst.DestPort, err)
			return err
		}
	}
	return nil
}

// waitAndMark waits for every instance to finish loading, marks each one done as it succeeds
// and frees its staged files. Failed ports keep their downloads for the next retry.
func (job *RedisRollback) waitAndMark(install *RedisInstall, saveDir string, pending []RollbackInstance) error {
	return rollback.RunBounded(len(pending), len(pending), func(i int) error {
		inst := pending[i]
		instDir := job.instanceDir(install, inst.DestPort)
		addr := fmt.Sprintf("%s:%d", job.params.DestIP, inst.DestPort)
		password, err := myredis.GetRedisPasswdFromConfFile(inst.DestPort)
		if err != nil {
			return err
		}
		deadline := rollback.LoadDeadline(rollback.DataFileBytes(filepath.Join(instDir, "data")))
		if err = rollback.WaitLoaded(addr, password, deadline); err != nil {
			job.runtime.Logger.Error("RedisRollback %s: %v", addr, err)
			return err
		}
		if err = rollback.MarkDone(instDir, rollback.Fingerprint(inst.FullFiles)); err != nil {
			return err
		}
		if err = rollback.CleanupStaged(saveDir, toRestore(inst)); err != nil {
			job.runtime.Logger.Warn("RedisRollback cleanup staged files for %d failed: %v", inst.DestPort, err)
		}
		return nil
	})
}

// instanceDir returns instance data directory, e.g. /data/redis/{port}.
func (job *RedisRollback) instanceDir(install *RedisInstall, port int) string {
	if install != nil && install.RealDataDir != "" {
		return filepath.Join(install.RealDataDir, strconv.Itoa(port))
	}
	return filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(port))
}

// startInstance starts a single redis instance under mysql user without requiring an empty db.
func (job *RedisRollback) startInstance(install *RedisInstall, port int) error {
	binDir := ""
	if install != nil {
		binDir = install.RedisBinDir
	}
	if binDir == "" {
		binDir = filepath.Join(consts.UsrLocal, "redis", "bin")
	}
	startScript := filepath.Join(binDir, "start-redis.sh")
	job.runtime.Logger.Info("su %s -c \"%s\"", consts.MysqlAaccount, startScript+"  "+strconv.Itoa(port))
	_, err := util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c",
		startScript + "  " + strconv.Itoa(port)}, "", nil, 20*time.Minute)
	return err
}

func portsOf(instances []RollbackInstance) []int {
	ports := make([]int, 0, len(instances))
	for _, inst := range instances {
		ports = append(ports, inst.DestPort)
	}
	return ports
}
