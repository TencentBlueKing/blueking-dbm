package atommongodb

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/mongo"
)

// instance_op 对单个mongod/mongos进程作一些起停操作

// instOpParams 原子任务参数
type instOpParams struct {
	IP             string `json:"ip"`
	Port           int    `json:"port"`
	AdminUsername  string `json:"adminUsername"`
	AdminPassword  string `json:"adminPassword"`
	Op             string `json:"op"` // start, stop, check_empty_data, start_standalone
	SetName        string `json:"set_name,omitempty"`
	CurrentVersion string `json:"currentVersion,omitempty"`
	// OldFullVersion mongodb-x.y.z (upgrade hop source); used by backup_mongodata directory name.
	OldFullVersion   string `json:"oldFullVersion,omitempty"`
	GrantRolesToUser struct {
		Username string   `json:"username,omitempty"`
		Roles    []string `json:"roles,omitempty"`
	} `json:"grantRolesToUser,omitempty"`
}

type instOpJob struct {
	BaseJob
	ConfParams  *instOpParams
	MongoInst   *mymongo.MongoHost
	MongoClient *mongo.Client
}

func (s *instOpJob) Param() string {
	o, _ := json.MarshalIndent(instOpParams{}, "", "\t")
	return string(o)
}

// NewInstOpJob 实例化结构体
func NewInstOpJob() jobruntime.JobRunner {
	return &instOpJob{}
}

// Name 获取原子任务的名字
func (s *instOpJob) Name() string {
	return "mongodb_instance_op"
}

// Run 运行原子任务
func (s *instOpJob) Run() error {
	var op = s.GetInstanceOp()
	s.runtime.Logger.Info("do op %s", s.ConfParams.Op)
	switch s.ConfParams.Op {
	case "rs_remove_other_node":
		// remove me from the replica set
		return s.doRemoveOtherMember()
	case "rs_join":
		// add me to the replica set
		return s.doAddMember()
	case "rs_init":
		// exec rs.initiate()
		return s.doInit()
	case "grantRolesToUser":
		// grant roles to user
		return op.GrantRolesToUser(s.ConfParams.GrantRolesToUser.Username, s.ConfParams.GrantRolesToUser.Roles)
	case "stop_dbmon":
		return s.doStopDbmon()
	case "start_dbmon":
		return s.doStartDbmon()
	case "shield_dbmon":
		return s.doShieldDbmon()
	case "unblock_dbmon":
		return s.doUnblockDbmon()
	case "stop":
		return op.DoStop()
	case "start":
		pid, running, err := op.IsRunning()
		if err != nil {
			return errors.Wrap(err, "IsRunning")
		}
		if running {
			s.runtime.Logger.Info("instance is running pid = %d , skip start", pid)
			return nil
		}
		return op.DoStart("auth")
	case "start_as_standalone":
		err := op.DoStop()
		if err != nil {
			return errors.Wrap(err, "DoStop")
		}
		return op.DoStartAsStandAlone()
	case "check_empty_data":
		_, err := op.DoCheckEmptyData()
		if err == nil {
			s.runtime.Logger.Info("is_empty_data: true")
		}
		return err
	case "show_tables":
		// 列出db简单信息. 未实现
		return errors.New("not implemented")
	case "flush_router_config":
		// 刷新router的配置
		return op.DoFlushRouterConfig()
	case "service_status_check":
		// 检查服务状态
		return op.DoServiceStatusCheck(s.runtime.Logger)
	case "backup_mongodata":
		return s.doBackupMongodata()
	case "precheck_upgrade":
		return s.doPrecheckUpgrade()
	case "precheck_disk_upgrade":
		return s.doPrecheckDiskBeforeUpgrade()
	}

	return errors.New("unknown op " + s.ConfParams.Op)
}

func (s *instOpJob) doBackupMongodata() error {
	op := s.GetInstanceOp()
	_, running, err := op.IsRunning()
	if err != nil {
		return errors.Wrap(err, "IsRunning check before backup")
	}
	if running {
		return fmt.Errorf("instance %s:%d is still running, refuse to backup data directory",
			s.ConfParams.IP, s.ConfParams.Port)
	}
	dbPath, err := op.GetDBPathFromConfig()
	if err != nil {
		return errors.Wrap(err, "GetDBPathFromConfig")
	}
	uniqId := s.runtime.UID
	oldVer := strings.TrimSpace(s.ConfParams.OldFullVersion)
	if oldVer == "" {
		oldVer = strings.TrimSpace(s.ConfParams.CurrentVersion)
	}
	if oldVer == "" {
		oldVer = "unknown"
	}
	oldVer = sanitizePathSegmentForBackupDir(oldVer)
	// backup_db_${uniqId}_${old_full_ver} next to data directory (same parent as dbPath)
	dstPath := filepath.Join(filepath.Dir(dbPath), fmt.Sprintf("backup_db_%s_%s", uniqId, oldVer))
	log := s.runtime.Logger

	dfRet, dfErr := dfRunWithLocale(dbPath, "-hP").Run(30 * time.Second)
	log.Info(
		"backup_mongodata precheck filesystem (df -hP): cmd=%s exitCode=%d err=%v stdout=%q stderr=%q",
		dfRet.Cmdline, dfRet.ExitCode, dfErr,
		strings.TrimSpace(dfRet.GetStdout()), strings.TrimSpace(dfRet.GetStderr()),
	)

	duRet, duErr := duRunWithLocale(dbPath, "-sh").Run(5 * time.Minute)
	log.Info(
		"backup_mongodata precheck db directory size (du -sh): cmd=%s exitCode=%d err=%v stdout=%q stderr=%q",
		duRet.Cmdline, duRet.ExitCode, duErr,
		strings.TrimSpace(duRet.GetStdout()), strings.TrimSpace(duRet.GetStderr()),
	)

	// Best-effort disk space check: need >= data size + 5% margin on the filesystem hosting dbPath.
	usedBytes, errDu := duDirBytes(dbPath)
	_, availBytes, errDf := dfTotalAvailBytes(dbPath)
	if errDu != nil || errDf != nil {
		log.Info(
			"backup_mongodata disk space precheck skipped (du/df parse): du_err=%v df_err=%v",
			errDu,
			errDf,
		)
	} else {
		need := usedBytes * 105 / 100
		if availBytes < need {
			return fmt.Errorf(
				"backup_mongodata: insufficient disk space: need ~%d bytes (data dir %d bytes with 5%% margin), available %d",
				need,
				usedBytes,
				availBytes,
			)
		}
		log.Info(
			"backup_mongodata disk space precheck OK: used=%d avail=%d need=%d",
			usedBytes,
			availBytes,
			need,
		)
	}

	backupCmd := fmt.Sprintf(
		"set -e; src=%q; dst=%q; cp -a \"$src\" \"$dst\"",
		dbPath,
		dstPath,
	)
	copyStart := time.Now()
	ret, err := mycmd.New("bash", "-lc", backupCmd).Run(time.Second * 600)
	copyElapsed := time.Since(copyStart)
	log.Info("exec %s, exitCode:%d, err:%v, copy_elapsed:%s", ret.Cmdline, ret.ExitCode, err, copyElapsed)
	if err != nil {
		_ = os.RemoveAll(dstPath)
		return errors.Wrap(err, "backup mongodata failed")
	}
	if ret.ExitCode != 0 {
		_ = os.RemoveAll(dstPath)
		return fmt.Errorf("backup mongodata failed: exitCode=%d stderr=%q", ret.ExitCode, strings.TrimSpace(ret.GetStderr()))
	}
	log.Info("backup_mongodata copy finished OK: src=%s dst=%s copy_elapsed:%s", dbPath, dstPath, copyElapsed)
	return nil
}

func sanitizePathSegmentForBackupDir(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return "unknown"
	}
	var b strings.Builder
	for _, r := range s {
		switch r {
		case '/', '\\', ':', '\x00':
			b.WriteByte('_')
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

func (s *instOpJob) doStartDbmon() error {
	startSh := "/home/mysql/bk-dbmon/start.sh"
	_, err := mycmd.New(startSh).Run(time.Second * 60)
	if err != nil {
		return errors.Wrap(err, "start dbmon failed")
	}
	return nil
}

func (s *instOpJob) doStopDbmon() error {
	stopSh := "/home/mysql/bk-dbmon/stop.sh"
	ret, err := mycmd.New(stopSh).Run(time.Second * 600)
	s.runtime.Logger.Info("exec %s, exitCode:%d, err:%v", ret.Cmdline, ret.ExitCode, err)
	if err != nil {
		return errors.Wrap(err, "stop dbmon failed")
	}
	return nil
}

func (s *instOpJob) doShieldDbmon() error {
	cmd := fmt.Sprintf(
		"cd /home/mysql/bk-dbmon && /home/mysql/bk-dbmon/bk-dbmon alarm shield --port %d",
		s.ConfParams.Port,
	)
	ret, err := mycmd.New("bash", "-lc", cmd).Run(time.Second * 60)
	s.runtime.Logger.Info("exec %s, exitCode:%d, err:%v", ret.Cmdline, ret.ExitCode, err)
	if err != nil {
		return errors.Wrap(err, "shield dbmon failed")
	}
	return nil
}

func (s *instOpJob) doUnblockDbmon() error {
	cmd := fmt.Sprintf(
		"cd /home/mysql/bk-dbmon && /home/mysql/bk-dbmon/bk-dbmon alarm unblock --port %d",
		s.ConfParams.Port,
	)
	ret, err := mycmd.New("bash", "-lc", cmd).Run(time.Second * 60)
	s.runtime.Logger.Info("exec %s, exitCode:%d, err:%v", ret.Cmdline, ret.ExitCode, err)
	if err != nil {
		return errors.Wrap(err, "unblock dbmon failed")
	}
	return nil
}

// versionMajorMinor extracts "M.m" from a version string like "M.m.p", "M.m",
// or prefixed forms like "mongodb-M.m.p".
func versionMajorMinor(version string) string {
	v := strings.TrimPrefix(version, "mongodb-")
	parts := strings.SplitN(v, ".", 3)
	if len(parts) >= 2 {
		return parts[0] + "." + parts[1]
	}
	return v
}

func (s *instOpJob) doPrecheckUpgrade() error {
	if s.ConfParams.CurrentVersion == "" {
		return fmt.Errorf("currentVersion is required for precheck_upgrade")
	}
	mongoBin := filepath.Join(consts.GetMongoBinDir(), "mongodb", "bin", "mongo")
	expectedMajor := versionMajorMinor(s.ConfParams.CurrentVersion)
	ip := s.ConfParams.IP
	port := s.ConfParams.Port
	user := s.ConfParams.AdminUsername
	pass := s.ConfParams.AdminPassword

	// 1. Check running version major matches current_version major
	evalScript := "db.adminCommand({buildInfo:1}).version"
	ret, err := mycmd.New(
		mongoBin,
		"-u", user,
		"-p", mycmd.Password(pass),
		"--host", ip,
		"--port", strconv.Itoa(port),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", evalScript,
		"admin",
	).Run(60 * time.Second)
	if err != nil {
		return fmt.Errorf(
			"get buildInfo version failed: cmd=%q exitCode=%d err=%v stdout=%q stderr=%q",
			ret.Cmdline, ret.ExitCode, err, ret.GetStdout(), ret.GetStderr(),
		)
	}
	runningVersion := strings.TrimSpace(ret.GetStdout())
	runningMajor := versionMajorMinor(runningVersion)
	s.runtime.Logger.Info("precheck: running version=%s (major=%s), expected major=%s", runningVersion, runningMajor, expectedMajor)
	if runningMajor != expectedMajor {
		return fmt.Errorf("running version major %s does not match expected %s (from current_version %s)",
			runningMajor, expectedMajor, s.ConfParams.CurrentVersion)
	}

	// 2. Check featureCompatibilityVersion matches expected
	fcv, err := common.GetFCV(mongoBin, ip, port, user, pass)
	if err != nil {
		return errors.Wrap(err, "get featureCompatibilityVersion")
	}
	s.runtime.Logger.Info("precheck: featureCompatibilityVersion=%s, expected=%s", fcv, expectedMajor)
	if fcv != expectedMajor {
		return fmt.Errorf("featureCompatibilityVersion %s does not match expected %s (from current_version %s)",
			fcv, expectedMajor, s.ConfParams.CurrentVersion)
	}

	s.runtime.Logger.Info("precheck_upgrade passed for %s:%d", ip, port)
	return nil
}

const minFreeDiskRatioForUpgradePrecheck = 0.6

func (s *instOpJob) doPrecheckDiskBeforeUpgrade() error {
	op := s.GetInstanceOp()
	dbPath, err := op.GetDBPathFromConfig()
	if err != nil {
		return errors.Wrap(err, "GetDBPathFromConfig")
	}
	log := s.runtime.Logger
	ret, err := dfRunWithLocale(dbPath, "-B1", "-P").Run(30 * time.Second)
	stdout := strings.TrimSpace(ret.GetStdout())
	combined := fmt.Sprintf("stdout=%q stderr=%q", ret.GetStdout(), ret.GetStderr())
	if err != nil || ret.ExitCode != 0 {
		log.Error("precheck_disk_upgrade: df failed: cmdline=%s exitCode=%d %s err=%v", ret.Cmdline, ret.ExitCode, combined, err)
		return fmt.Errorf("precheck_disk_upgrade: df failed: %s", combined)
	}
	totalBytes, availBytes, perr := parseDfB1POutput(stdout)
	if perr != nil {
		log.Error("precheck_disk_upgrade: parse df output: %v %s", perr, combined)
		return fmt.Errorf("precheck_disk_upgrade: abnormal df output (%s): %w", combined, perr)
	}
	if totalBytes == 0 {
		return fmt.Errorf("precheck_disk_upgrade: total filesystem size is zero")
	}
	ratio := float64(availBytes) / float64(totalBytes)
	const bytesPerGiB = 1024 * 1024 * 1024
	totalGiB := float64(totalBytes) / bytesPerGiB
	availGiB := float64(availBytes) / bytesPerGiB
	log.Info(
		"precheck_disk_upgrade: dbPath=%s total_GB=%.2f avail_GB=%.2f free_ratio=%.4f",
		dbPath,
		totalGiB,
		availGiB,
		ratio,
	)
	if ratio < minFreeDiskRatioForUpgradePrecheck {
		// Use "%" as an argument instead of %% in the format string so fmt never mis-parses percent signs.
		return fmt.Errorf(
			"precheck_disk_upgrade: insufficient free space on data disk: need >= %.0f%s free, got %.2f%s (avail_GB=%.2f total_GB=%.2f)",
			minFreeDiskRatioForUpgradePrecheck*100,
			"%",
			ratio*100,
			"%",
			availGiB,
			totalGiB,
		)
	}
	return nil
}

func duDirBytes(dbPath string) (uint64, error) {
	ret, err := duRunWithLocale(dbPath, "-sb").Run(5 * time.Minute)
	if err != nil || ret.ExitCode != 0 {
		return 0, fmt.Errorf("du -sb failed: exit=%d err=%v stderr=%q", ret.ExitCode, err, ret.GetStderr())
	}
	fields := strings.Fields(strings.TrimSpace(ret.GetStdout()))
	if len(fields) < 2 {
		return 0, fmt.Errorf("unexpected du output: %q", ret.GetStdout())
	}
	return strconv.ParseUint(fields[0], 10, 64)
}

func dfTotalAvailBytes(dbPath string) (uint64, uint64, error) {
	ret, err := dfRunWithLocale(dbPath, "-B1", "-P").Run(30 * time.Second)
	out := strings.TrimSpace(ret.GetStdout())
	if err != nil || ret.ExitCode != 0 {
		return 0, 0, fmt.Errorf("df failed: exit=%d err=%v stderr=%q", ret.ExitCode, err, ret.GetStderr())
	}
	total, avail, err := parseDfB1POutput(out)
	if err != nil {
		return 0, 0, err
	}
	return total, avail, nil
}

// dfRunWithLocale runs df under LC_ALL=C so POSIX -P layout and column labels stay stable
// (avoids localized headers like 文件系统 breaking parsing).
func dfRunWithLocale(dbPath string, dfArgs ...string) *mycmd.CmdBuilder {
	b := mycmd.New("env", "LC_ALL=C", "df")
	for _, a := range dfArgs {
		b.Append(a)
	}
	b.Append(dbPath)
	return b
}

// duRunWithLocale runs du under LC_ALL=C so du -sh logs use English size suffixes (K/M/G).
func duRunWithLocale(dbPath string, duArgs ...string) *mycmd.CmdBuilder {
	b := mycmd.New("env", "LC_ALL=C", "du")
	for _, a := range duArgs {
		b.Append(a)
	}
	b.Append(dbPath)
	return b
}

func parseDfB1POutput(stdout string) (totalBytes, availBytes uint64, err error) {
	lines := strings.Split(strings.TrimSpace(stdout), "\n")
	if len(lines) == 0 {
		return 0, 0, fmt.Errorf("empty df output")
	}
	// Prefer last line that looks like a data row (2nd field is numeric); works with any locale header.
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 4 {
			continue
		}
		totalBytes, err = strconv.ParseUint(fields[1], 10, 64)
		if err != nil {
			continue
		}
		availBytes, err = strconv.ParseUint(fields[3], 10, 64)
		if err != nil {
			return 0, 0, fmt.Errorf("parse avail: %w", err)
		}
		return totalBytes, availBytes, nil
	}
	return 0, 0, fmt.Errorf("no parseable df data line in output")
}

func (s *instOpJob) doInit() error {
	rsInfo := common.RsConf{}
	rsInfo.Id = s.ConfParams.SetName
	rsInfo.Hosts = append(rsInfo.Hosts, common.RsConfMember{
		Id:   0,
		Host: fmt.Sprintf("%s:%d", s.ConfParams.IP, s.ConfParams.Port),
	})
	rsInfo.Configsvr = strings.HasSuffix(s.ConfParams.SetName, "-conf")

	inst := common.NewInstance(s.ConfParams.IP, s.ConfParams.Port,
		s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "mongod")

	RsOpHandle := common.NewRsOp()
	out, err := RsOpHandle.Initiate(inst, &rsInfo, 120)
	s.runtime.Logger.Info("Initiate in: %+v, out: %+v, err:%v", &rsInfo, out, err)
	if err != nil || out.Ok != 1 {
		return errors.New("Initiate failed")
	}
	return nil
}

func (s *instOpJob) doRemoveOtherMember() error {
	op := s.GetInstanceOp()
	// 1. set myself as primary
	// if not primary, set myself as primary
	rsInfo, err := op.IsMaster()
	if err != nil {
		return errors.Wrap(err, "IsMaster")
	}
	if rsInfo.Primary == "" {
		return errors.New("no primary, maybe not a replica set")
	}
	s.runtime.Logger.Info("isMaster me:%s primary:%s", rsInfo.Me, rsInfo.Primary)
	RsOpHandle := common.NewRsOp()

	if !rsInfo.IsMaster {
		err = RsOpHandle.SetPriority(op.Instance, rsInfo.Me, 10)
		// wait for new primary
		// conf, err := RsOpHandle.GetRsConf(op.Instance)
		// s.runtime.Logger.Info("get rs conf %+v %v", conf, err)
		for i := 0; i < 10; i++ {
			rsInfo, err = op.IsMaster()
			if err != nil {
				return errors.Wrap(err, "IsMaster")
			}
			if rsInfo.Primary == rsInfo.Me {
				break
			}
			time.Sleep(2 * time.Second)
		}
	}
	conf, err := RsOpHandle.GetRsConf(op.Instance)
	if err != nil {
		return errors.Wrap(err, "GetRsConf")
	}
	s.runtime.Logger.Info("get rs conf %+v", conf)

	newHost := make([]common.RsConfMember, 0)
	for _, m := range conf.Config.Hosts {
		if m.Host == rsInfo.Me {
			newHost = append(newHost, m)
		}
	}
	conf.Config.Hosts = newHost
	out, err := RsOpHandle.ReConfig(op.Instance, &conf.Config, 120)
	if err != nil {
		s.runtime.Logger.Error("ReConfig val  %+v", &conf.Config)
		return errors.Wrap(err, "ReConfig")
	}
	if out.Ok != 1 {
		return errors.New("ReConfig failed")
	}
	time.Sleep(2 * time.Second)
	conf, err = RsOpHandle.GetRsConf(op.Instance)
	if err != nil {
		return errors.Wrap(err, "GetRsConf")
	}
	s.runtime.Logger.Info("get rs conf %+v", conf)
	if len(conf.Config.Hosts) == 1 {
		return nil
	} else {
		return errors.New("remove other member failed")
	}
}

// not implemented
func (s *instOpJob) doAddMember() error {
	return nil
	// op := s.GetInstanceOp()
	// return op.DoAddMember()
}

func (s *instOpJob) GetInstanceOp() *common.InstanceOp {
	return common.NewInstanceOp(s.ConfParams.IP,
		s.ConfParams.Port,
		s.ConfParams.AdminUsername,
		s.ConfParams.AdminPassword,
		s.runtime.Logger,
	)
}

// Init 初始化
func (s *instOpJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.OsUser = ""
	if checkIsRootUser() {
		s.runtime.Logger.Error("This job cannot be executed as root user")
		return errors.New("This job cannot be executed as root user")
	}
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error("%s", tmpErr.Error())
		return tmpErr
	}
	return nil
}
