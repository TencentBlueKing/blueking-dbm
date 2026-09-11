// Package datadirjob 采集 mongod 实例 datadir 磁盘用量
package datadirjob

import (
	"bytes"
	"context"
	"fmt"
	"math"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbmon/cmd/basejob"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/dbmon/pkg/mongoconf"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/disk"

	"go.uber.org/zap"
)

const (
	// MetricDatadirDiskUsedKB 实例 datadir 已用容量（KB）
	MetricDatadirDiskUsedKB = "mongo_datadir_disk_used_kb"
	// MetricDatadirDiskTotalKB 实例分摊后的磁盘总容量（同盘实例均分，KB）
	MetricDatadirDiskTotalKB = "mongo_datadir_disk_total_kb"
	// MetricDatadirDiskRWOk datadir 所在文件系统读写探测是否成功（1/0）
	MetricDatadirDiskRWOk = "mongo_datadir_disk_rw_ok"
	// MetricDatadirDiskRWLatencyMs datadir 读写探测耗时（毫秒，仅成功时上报）
	MetricDatadirDiskRWLatencyMs = "mongo_datadir_disk_rw_latency_ms"
	bytesPerKB                   = 1024
	// kbPerG 1GiB = 1024*1024 KB
	kbPerG = 1024 * 1024
	// diskRWProbeTimeout 磁盘读写探测超时，避免 hang 住整轮采集
	diskRWProbeTimeout = 3 * time.Second
)

var (
	globDatadirJob *Job
	datadirOnce    sync.Once
)

// Job datadir 磁盘用量采集
type Job struct {
	basejob.BaseJob
}

// GetJob 获取 datadir 采集任务单例
func GetJob(conf *config.DbMonConfig, logger *zap.Logger, jobName string) *Job {
	datadirOnce.Do(func() {
		globDatadirJob = &Job{
			BaseJob: basejob.BaseJob{
				Name:   jobName,
				Conf:   conf,
				Logger: logger.With(zap.String("job", jobName)),
			},
		}
	})
	return globDatadirJob
}

type instanceDiskInfo struct {
	server  *config.ConfServerItem
	dbPath  string
	used    uint64
	fsTotal uint64
	major   uint32
	minor   uint32
}

func deviceKey(major, minor uint32) string {
	return fmt.Sprintf("%d:%d", major, minor)
}

func isMongos(svr *config.ConfServerItem) bool {
	return svr.RoleType == "mongos" || svr.MetaRole == "mongos"
}

// Run 采集所有 mongod 节点的 datadir 用量并上报
func (job *Job) Run() {
	job.LoopTimes++
	job.Logger.Info("start", zap.Uint64("loopTimes", job.LoopTimes))
	defer job.Logger.Info("end", zap.Uint64("loopTimes", job.LoopTimes))

	if err := job.UpdateConf(); err != nil {
		job.Logger.Warn(fmt.Sprintf("UpdateConf return err %s", err.Error()))
		return
	}
	if len(job.MyConf.Servers) == 0 {
		job.Logger.Warn("no server in config")
		return
	}

	infos := make([]*instanceDiskInfo, 0, len(job.MyConf.Servers))
	deviceCount := make(map[string]int)

	// 先解析路径与块设备并计入同盘实例数；du 失败的实例仍参与均分，避免存活实例 total 被放大。
	for i := range job.MyConf.Servers {
		svr := &job.MyConf.Servers[i]
		if isMongos(svr) {
			job.Logger.Info("skip mongos", zap.String("instance", svr.Addr()))
			continue
		}
		info, err := job.resolveDevice(svr)
		if err != nil {
			job.Logger.Warn("resolve datadir device failed",
				zap.String("instance", svr.Addr()), zap.Error(err))
			continue
		}
		deviceCount[deviceKey(info.major, info.minor)]++

		// 磁盘读写健康探测：超时或失败上报 ok=0，不阻塞整轮采集
		rwOk, rwLatencyMs := probeDiskRW(info.dbPath, diskRWProbeTimeout)
		if err := job.reportRWMetrics(svr, rwOk, rwLatencyMs); err != nil {
			job.Logger.Warn("report datadir rw metrics failed",
				zap.String("instance", svr.Addr()), zap.Error(err))
		} else {
			job.Logger.Info("report datadir rw metrics ok",
				zap.String("instance", svr.Addr()),
				zap.String("dbPath", info.dbPath),
				zap.Float64("rw_ok", rwOk),
				zap.Float64("rw_latency_ms", rwLatencyMs))
		}

		used, err := duDirBytes(info.dbPath)
		if err != nil {
			job.Logger.Warn("collect datadir used failed",
				zap.String("instance", svr.Addr()),
				zap.String("dbPath", info.dbPath),
				zap.Error(err))
			continue
		}
		info.used = used
		infos = append(infos, info)
	}

	for _, info := range infos {
		n := shareCount(deviceCount, info.major, info.minor)
		avgTotalKB := float64(info.fsTotal) / float64(n) / bytesPerKB
		totalKB := roundTotalKB(avgTotalKB)
		usedKB := float64(info.used) / bytesPerKB
		if err := job.reportMetrics(info.server, usedKB, totalKB); err != nil {
			job.Logger.Warn("report datadir metrics failed",
				zap.String("instance", info.server.Addr()), zap.Error(err))
			continue
		}
		job.Logger.Info("report datadir metrics ok",
			zap.String("instance", info.server.Addr()),
			zap.String("dbPath", info.dbPath),
			zap.Float64("used_kb", usedKB),
			zap.Float64("total_avg_kb", avgTotalKB),
			zap.Float64("total_kb", totalKB),
			zap.Int("share_n", n))
	}
}

// shareCount 返回同盘实例数，至少为 1。
func shareCount(deviceCount map[string]int, major, minor uint32) int {
	n := deviceCount[deviceKey(major, minor)]
	if n <= 0 {
		return 1
	}
	return n
}

// roundTotalKB 对实例分摊后的磁盘总容量尽量取整：
// >= 1000G 取整为 100G 的倍数；>= 100G 取整为 10G 的倍数；否则取整为 1G 的倍数。
func roundTotalKB(totalKB float64) float64 {
	if totalKB <= 0 {
		return totalKB
	}
	g := totalKB / float64(kbPerG)
	switch {
	case g >= 1000:
		return math.Round(g/100) * 100 * float64(kbPerG)
	case g >= 100:
		return math.Round(g/10) * 10 * float64(kbPerG)
	default:
		return math.Round(g) * float64(kbPerG)
	}
}

func (job *Job) resolveDevice(svr *config.ConfServerItem) (*instanceDiskInfo, error) {
	dbPath, err := resolveDbPath(svr.Port)
	if err != nil {
		return nil, err
	}
	fsInfo, err := disk.GetInfo(dbPath)
	if err != nil {
		return nil, err
	}
	return &instanceDiskInfo{
		server:  svr,
		dbPath:  dbPath,
		fsTotal: fsInfo.Total,
		major:   fsInfo.Major,
		minor:   fsInfo.Minor,
	}, nil
}

func resolveDbPath(port int) (string, error) {
	conf, err := mongoconf.LoadMongodConfig(port)
	if err == nil && conf.Storage.DbPath != "" {
		return conf.Storage.DbPath, nil
	}
	portStr := strconv.Itoa(port)
	dataDir := consts.GetMongoDataDir(portStr)
	if dataDir == "" {
		if err != nil {
			return "", fmt.Errorf("load mongod config failed: %w", err)
		}
		return "", fmt.Errorf("empty dbPath for port %d", port)
	}
	// 约定回退路径: <dataDir>/mongodata/<port>/db
	return path.Join(dataDir, "mongodata", portStr, "db"), nil
}

func duDirBytes(dbPath string) (uint64, error) {
	ret, err := mycmd.New("env", "LC_ALL=C", "du", "-sb", dbPath).Run(5 * time.Minute)
	if err != nil || ret.ExitCode != 0 {
		return 0, fmt.Errorf("du -sb failed: exit=%d err=%v stderr=%q",
			ret.ExitCode, err, ret.GetStderr())
	}
	fields := strings.Fields(strings.TrimSpace(ret.GetStdout()))
	if len(fields) < 1 {
		return 0, fmt.Errorf("unexpected du output: %q", ret.GetStdout())
	}
	return strconv.ParseUint(fields[0], 10, 64)
}

// probeDiskRW 在 dbPath（或父目录）写入临时文件并 fsync/读回/删除，探测文件系统读写是否可用。
// 超时或失败返回 ok=0；成功返回 ok=1 与耗时毫秒。超时后后台 goroutine 可能仍挂起，属预期。
func probeDiskRW(dbPath string, timeout time.Duration) (ok float64, latencyMs float64) {
	type probeResult struct {
		latencyMs float64
		err       error
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	ch := make(chan probeResult, 1)
	go func() {
		start := time.Now()
		err := doDiskRWProbe(dbPath)
		ch <- probeResult{latencyMs: float64(time.Since(start).Milliseconds()), err: err}
	}()

	select {
	case <-ctx.Done():
		return 0, -1
	case r := <-ch:
		if r.err != nil {
			return 0, -1
		}
		return 1, r.latencyMs
	}
}

func doDiskRWProbe(dbPath string) error {
	dir := dbPath
	payload := []byte("dbmon-disk-rw-probe")
	f, err := os.CreateTemp(dir, ".dbmon_disk_rw_*")
	if err != nil {
		// dbPath 不可写时回退到父目录（同盘）
		parent := filepath.Dir(dir)
		f, err = os.CreateTemp(parent, ".dbmon_disk_rw_*")
		if err != nil {
			return fmt.Errorf("create temp file under %s or %s: %w", dir, parent, err)
		}
	}
	name := f.Name()
	defer func() {
		_ = f.Close()
		_ = os.Remove(name)
	}()

	if _, err = f.Write(payload); err != nil {
		return fmt.Errorf("write probe file: %w", err)
	}
	if err = f.Sync(); err != nil {
		return fmt.Errorf("fsync probe file: %w", err)
	}
	if _, err = f.Seek(0, 0); err != nil {
		return fmt.Errorf("seek probe file: %w", err)
	}
	got := make([]byte, len(payload))
	n, err := f.Read(got)
	if err != nil {
		return fmt.Errorf("read probe file: %w", err)
	}
	if n != len(payload) || !bytes.Equal(got, payload) {
		return fmt.Errorf("probe file content mismatch: got %q", got[:n])
	}
	return nil
}

func (job *Job) reportMetrics(svr *config.ConfServerItem, usedKB, totalKB float64) error {
	beat := &job.MyConf.BkMonitorBeat
	msgH, err := config.GetBkMonitorBeatSender(beat, svr)
	if err != nil {
		return err
	}
	msgH.SetLabel("port", strconv.Itoa(svr.Port))
	if err = msgH.SendTimeSeriesMsg(beat.MetricConfig.DataID, beat.MetricConfig.Token,
		svr.IP, MetricDatadirDiskUsedKB, usedKB, job.Logger); err != nil {
		return err
	}
	// 重新取 sender，避免维度/metrics 互相覆盖
	msgH2, err := config.GetBkMonitorBeatSender(beat, svr)
	if err != nil {
		return err
	}
	msgH2.SetLabel("port", strconv.Itoa(svr.Port))
	return msgH2.SendTimeSeriesMsg(beat.MetricConfig.DataID, beat.MetricConfig.Token,
		svr.IP, MetricDatadirDiskTotalKB, totalKB, job.Logger)
}

func (job *Job) reportRWMetrics(svr *config.ConfServerItem, rwOk, latencyMs float64) error {
	beat := &job.MyConf.BkMonitorBeat
	msgH, err := config.GetBkMonitorBeatSender(beat, svr)
	if err != nil {
		return err
	}
	msgH.SetLabel("port", strconv.Itoa(svr.Port))
	if err = msgH.SendTimeSeriesMsg(beat.MetricConfig.DataID, beat.MetricConfig.Token,
		svr.IP, MetricDatadirDiskRWOk, rwOk, job.Logger); err != nil {
		return err
	}
	// 失败时跳过 latency，避免无意义的 -1 干扰面板（ok 已表达失败）
	if rwOk < 1 {
		return nil
	}
	msgH2, err := config.GetBkMonitorBeatSender(beat, svr)
	if err != nil {
		return err
	}
	msgH2.SetLabel("port", strconv.Itoa(svr.Port))
	return msgH2.SendTimeSeriesMsg(beat.MetricConfig.DataID, beat.MetricConfig.Token,
		svr.IP, MetricDatadirDiskRWLatencyMs, latencyMs, job.Logger)
}
