package atomredis

import (
	"encoding/json"

	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/rollback"

	"github.com/go-playground/validator/v10"
)

// RedisRollbackVerifyParams names the manifest the flow pushed next to the downloads; the file
// list itself never travels in the payload.
type RedisRollbackVerifyParams struct {
	DestIP       string `json:"dest_ip" validate:"required"`
	DestDir      string `json:"dest_dir"`
	ManifestFile string `json:"manifest_file" validate:"required"`
	Fingerprint  string `json:"fingerprint"`
}

// RedisRollbackVerify checks the downloaded backups against the plan before anything is restored.
type RedisRollbackVerify struct {
	runtime *jobruntime.JobGenericRuntime
	params  RedisRollbackVerifyParams
}

var _ jobruntime.JobRunner = (*RedisRollbackVerify)(nil)

// NewRedisRollbackVerify creates a new verify runner.
func NewRedisRollbackVerify() jobruntime.JobRunner {
	return &RedisRollbackVerify{}
}

// Init validates params.
func (job *RedisRollbackVerify) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	if err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params); err != nil {
		job.runtime.Logger.Error("json.Unmarshal failed,err:%+v", err)
		return err
	}
	if err := validator.New().Struct(job.params); err != nil {
		job.runtime.Logger.Error("RedisRollbackVerify Init params validate failed,err:%v,params:%+v", err, job.params)
		return err
	}
	return nil
}

// Name returns atom job name.
func (job *RedisRollbackVerify) Name() string {
	return "redis_rollback_verify"
}

// Retry returns 0: a retry of the bamboo node runs it again.
func (job *RedisRollbackVerify) Retry() uint {
	return 0
}

// Rollback has nothing to undo: the job only reads.
func (job *RedisRollbackVerify) Rollback() error {
	return nil
}

// Run verifies the downloads.
func (job *RedisRollbackVerify) Run() error {
	saveDir := job.params.DestDir
	if saveDir == "" {
		saveDir = rollback.DefaultSaveDir()
	}
	if err := rollback.VerifyDownloads(saveDir, job.params.ManifestFile, job.params.Fingerprint); err != nil {
		job.runtime.Logger.Error("RedisRollbackVerify %s: %v", job.params.DestIP, err)
		return err
	}
	return nil
}
