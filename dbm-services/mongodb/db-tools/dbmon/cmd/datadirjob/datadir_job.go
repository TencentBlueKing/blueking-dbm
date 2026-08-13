// Package datadirjob 采集 mongod 实例 datadir 磁盘用量
package datadirjob

import (
	"fmt"
	"math"
	"path"
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
	bytesPerKB               = 1024
	// kbPerG 1GiB = 1024*1024 KB
	kbPerG = 1024 * 1024
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
