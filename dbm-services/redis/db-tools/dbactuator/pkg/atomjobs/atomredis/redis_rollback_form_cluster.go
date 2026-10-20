package atomredis

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/rollback"

	"github.com/go-playground/validator/v10"
)

const (
	formClusterTimeout = 5 * time.Minute
	formClusterPoll    = 2 * time.Second
)

// RedisRollbackFormClusterParams lists every temp instance of the plan with its slots. The password
// is read from the local conf of a node on DestIP: every temp instance of a plan shares it.
type RedisRollbackFormClusterParams struct {
	DestIP string              `json:"dest_ip" validate:"required"`
	Nodes  []rollback.FormNode `json:"nodes" validate:"required,dive"`
}

// RedisRollbackFormCluster forms the cluster protocol temp cluster once every port is restored.
type RedisRollbackFormCluster struct {
	runtime *jobruntime.JobGenericRuntime
	params  RedisRollbackFormClusterParams
}

var _ jobruntime.JobRunner = (*RedisRollbackFormCluster)(nil)

// NewRedisRollbackFormCluster creates a new runner.
func NewRedisRollbackFormCluster() jobruntime.JobRunner {
	return &RedisRollbackFormCluster{}
}

// Init validates params.
func (job *RedisRollbackFormCluster) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	if err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params); err != nil {
		job.runtime.Logger.Error("json.Unmarshal failed,err:%+v", err)
		return err
	}
	if err := validator.New().Struct(job.params); err != nil {
		job.runtime.Logger.Error("RedisRollbackFormCluster Init params validate failed,err:%v,params:%+v",
			err, job.params)
		return err
	}
	return nil
}

// Name returns atom job name.
func (job *RedisRollbackFormCluster) Name() string {
	return "redis_rollback_form_cluster"
}

// Retry returns 0: a retry of the bamboo node runs it again, skipping what is done.
func (job *RedisRollbackFormCluster) Retry() uint {
	return 0
}

// Rollback leaves a partly formed cluster to the next retry.
func (job *RedisRollbackFormCluster) Rollback() error {
	return nil
}

// Run forms the cluster.
func (job *RedisRollbackFormCluster) Run() error {
	password, err := job.localPassword()
	if err != nil {
		return err
	}
	connect := rollback.ClusterNodeConnector(password)
	if err = rollback.FormCluster(job.params.Nodes, connect, formClusterTimeout, formClusterPoll); err != nil {
		job.runtime.Logger.Error("RedisRollbackFormCluster: %v", err)
		return err
	}
	job.runtime.Logger.Info("RedisRollbackFormCluster: %d nodes formed as planned", len(job.params.Nodes))
	return nil
}

func (job *RedisRollbackFormCluster) localPassword() (string, error) {
	for _, n := range job.params.Nodes {
		if n.IP == job.params.DestIP {
			return myredis.GetRedisPasswdFromConfFile(n.Port)
		}
	}
	return "", fmt.Errorf("no temp instance on %s to read the password from", job.params.DestIP)
}
