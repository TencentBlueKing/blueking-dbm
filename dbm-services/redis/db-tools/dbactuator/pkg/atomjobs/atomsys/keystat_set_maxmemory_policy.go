package atomsys

import (
	"encoding/json"
	"fmt"
	"net"
	"strconv"
	"strings"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
)

// KeyStatSetMaxmemoryPolicyParams 在 keystat 中心机上按记录值恢复各实例 maxmemory-policy
type KeyStatSetMaxmemoryPolicyParams struct {
	RedisPassword string            `json:"redis_password" validate:"required"`
	AddrPolicies  map[string]string `json:"addr_policies" validate:"required,min=1"`
}

// KeyStatSetMaxmemoryPolicy atom job
type KeyStatSetMaxmemoryPolicy struct {
	runtime *jobruntime.JobGenericRuntime
	params  *KeyStatSetMaxmemoryPolicyParams
}

// NewKeyStatSetMaxmemoryPolicy new
func NewKeyStatSetMaxmemoryPolicy() jobruntime.JobRunner {
	return &KeyStatSetMaxmemoryPolicy{}
}

// Name atom name
func (job *KeyStatSetMaxmemoryPolicy) Name() string {
	return "keystat_set_maxmemory_policy"
}

// Init prepare run env
func (job *KeyStatSetMaxmemoryPolicy) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	job.params = &KeyStatSetMaxmemoryPolicyParams{}
	if err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), job.params); err != nil {
		return fmt.Errorf("json.Unmarshal failed: %w", err)
	}
	validate := validator.New()
	if err := validate.Struct(job.params); err != nil {
		return fmt.Errorf("params validate failed: %w", err)
	}
	return nil
}

// Run set maxmemory-policy for each addr
func (job *KeyStatSetMaxmemoryPolicy) Run() error {
	var errs []string
	for addr, policy := range job.params.AddrPolicies {
		policy = strings.TrimSpace(policy)
		if policy == "" {
			errs = append(errs, fmt.Sprintf("%s: empty maxmemory-policy", addr))
			continue
		}
		ip, portStr, err := net.SplitHostPort(addr)
		if err != nil {
			errs = append(errs, fmt.Sprintf("%s: invalid addr: %v", addr, err))
			continue
		}
		port, err := strconv.Atoi(portStr)
		if err != nil {
			errs = append(errs, fmt.Sprintf("%s: invalid port: %v", addr, err))
			continue
		}
		current, getErr := job.getPolicy(ip, port)
		if getErr == nil && strings.EqualFold(strings.TrimSpace(current), policy) {
			job.runtime.Logger.Info("maxmemory-policy already %s, skip set, addr:%s", policy, addr)
			continue
		}
		if setErr := job.setPolicy(ip, port, policy); setErr != nil {
			errs = append(errs, fmt.Sprintf("%s: set maxmemory-policy %s failed: %v", addr, policy, setErr))
			continue
		}
		job.runtime.Logger.Info("set maxmemory-policy success, addr:%s, policy:%s", addr, policy)
	}
	if len(errs) > 0 {
		return fmt.Errorf("keystat_set_maxmemory_policy failed: %s", strings.Join(errs, "; "))
	}
	return nil
}

func (job *KeyStatSetMaxmemoryPolicy) getPolicy(ip string, port int) (string, error) {
	host := fmt.Sprintf("%s:%d", ip, port)
	return configGet(host, job.params.RedisPassword, "maxmemory-policy")
}

func (job *KeyStatSetMaxmemoryPolicy) setPolicy(ip string, port int, policy string) error {
	host := fmt.Sprintf("%s:%d", ip, port)
	return configSet(host, job.params.RedisPassword, "maxmemory-policy", policy)
}

// Retry times
func (job *KeyStatSetMaxmemoryPolicy) Retry() uint {
	return 2
}

// Rollback rollback
func (job *KeyStatSetMaxmemoryPolicy) Rollback() error {
	return nil
}
