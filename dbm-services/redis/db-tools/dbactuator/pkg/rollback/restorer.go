// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

// Package rollback restores temporary redis instances from backups, one Restorer per storage engine.
// atomredis.RedisRollback only parses the payload, picks the Restorer and runs it.
package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// doneMarkerFile records backup fingerprint for idempotency.
const doneMarkerFile = "rollback.done"

// pendingMarkerFile is written once data is in place and before startup, so a retry
// can tell a still-loading instance of this backup from a half-restored one.
const pendingMarkerFile = "rollback.pending"

// BinlogRange is the inclusive file index range of the binlogs replayed on top of a full backup.
type BinlogRange struct {
	FirstIndex int64 `json:"first_index"`
	LastIndex  int64 `json:"last_index"`
}

// InstanceRestore is one dest port and the backup it is restored from.
// Binlogs arrive as a digest only; the files themselves are found in the save dir.
type InstanceRestore struct {
	SourceIP          string      `json:"source_ip"`
	SourcePort        int         `json:"source_port"`
	DestPort          int         `json:"dest_port" validate:"required"`
	FullFiles         []string    `json:"full_files"`
	BinlogRange       BinlogRange `json:"binlog_range"`
	BinlogCount       int         `json:"binlog_count"`
	BinlogFingerprint string      `json:"binlog_fingerprint"`
	// BinlogSegments is for logs only, e.g. "[1000-1001],[1003-1004]"; never compared.
	BinlogSegments string `json:"binlog_segments"`
}

// Fingerprint identifies the backup restored into this port.
func (inst InstanceRestore) Fingerprint() string {
	fp := Fingerprint(inst.FullFiles)
	if inst.BinlogFingerprint != "" {
		fp += "|" + inst.BinlogFingerprint
	}
	return fp
}

// Host is what a Restorer needs from the atom job: media, config rendering and process control.
type Host interface {
	// InstallTools installs dbtools (zstd, lzop, tredisbinlog, redis-cli).
	InstallTools() error
	// Prepare creates instance dirs and renders redis.conf without starting anything.
	Prepare(ports []int) error
	InstanceDir(port int) string
	Start(port int) error
	Stop(port int) error
	// MediaName is the redis package base name, e.g. redis-2.8.17-rocksdb-v1.3.10.
	MediaName() string
}

// Job is one host's rollback request.
type Job struct {
	DestIP    string
	SaveDir   string
	RecoverAt string
	Instances []InstanceRestore
	Host      Host
}

// Restorer restores every instance of a Job for one storage engine.
type Restorer interface {
	DoRollback() error
}

// New returns the Restorer for dbType, the cluster type carried in the install payload.
func New(dbType string, job Job) (Restorer, error) {
	if job.SaveDir == "" {
		job.SaveDir = DefaultSaveDir()
	}
	switch {
	case consts.IsRedisInstanceDbType(dbType):
		return &cacheRestorer{Job: job}, nil
	case consts.IsTendisSSDInstanceDbType(dbType):
		return &ssdRestorer{Job: job}, nil
	default:
		return nil, fmt.Errorf("redis_rollback does not support %s yet", dbType)
	}
}

// DefaultSaveDir returns the staging directory for downloaded backups.
func DefaultSaveDir() string {
	return filepath.Join(consts.GetRedisBackupDir(), recoverSubDir)
}

// Fingerprint computes a deterministic fingerprint for backup files.
func Fingerprint(files []string) string {
	names := make([]string, 0, len(files))
	for _, f := range files {
		names = append(names, filepath.Base(f))
	}
	sort.Strings(names)
	return strings.Join(names, ",")
}

// IsDone checks if the instance has already restored this exact backup.
// Verifying the fingerprint prevents skipping half-restored instances.
func IsDone(instDir, fingerprint string) bool {
	return markerMatches(filepath.Join(instDir, doneMarkerFile), fingerprint)
}

// MarkDone writes the completion marker after successful verification.
func MarkDone(instDir, fingerprint string) error {
	if err := os.WriteFile(filepath.Join(instDir, doneMarkerFile), []byte(fingerprint), 0644); err != nil {
		return err
	}
	_ = os.Remove(filepath.Join(instDir, pendingMarkerFile))
	return nil
}

// ClearDone removes stale markers before re-running a port.
func ClearDone(instDir string) {
	_ = os.Remove(filepath.Join(instDir, doneMarkerFile))
	_ = os.Remove(filepath.Join(instDir, pendingMarkerFile))
}

// MarkPending records that this backup's data file is in place and the instance is about to start.
func MarkPending(instDir, fingerprint string) error {
	return os.WriteFile(filepath.Join(instDir, pendingMarkerFile), []byte(fingerprint), 0644)
}

// IsPending checks if the instance was started from this exact backup but not yet verified.
func IsPending(instDir, fingerprint string) bool {
	return markerMatches(filepath.Join(instDir, pendingMarkerFile), fingerprint)
}

func markerMatches(file, fingerprint string) bool {
	data, err := os.ReadFile(file)
	if err != nil {
		return false
	}
	return strings.TrimSpace(string(data)) == fingerprint
}

func portsOf(instances []InstanceRestore) []int {
	ports := make([]int, 0, len(instances))
	for _, inst := range instances {
		ports = append(ports, inst.DestPort)
	}
	return ports
}
