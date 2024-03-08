package atommongodb

import (
	"dbm-services/mongo/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"
	"dbm-services/mongo/db-tools/dbmon/config"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/backupsys"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/report"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/toolkit/logical"
	"encoding/json"
	"fmt"
	"path"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/mongo"
)

const backupTypeLogical string = "logical"
const backupTypePhysical string = "physical" // 未实现

// 备份
// 1. 分析参数，确定要备份的库和表
// 2. 执行备份
// 3. 上报备份记录
// 4. 上报到备份系统，等待备份系统完成

// backupParams 备份任务参数，由前端传入
type backupParams struct {
	// 这个参数是不是可以从bk-dbmon.conf中获得？
	BkDbmInstance         config.BkDbmLabel `json:"bk_dbm_instance"`
	IP                    string            `json:"ip"`
	Port                  int               `json:"port"`
	AdminUsername         string            `json:"adminUsername"`
	AdminPassword         string            `json:"adminPassword"`
	SkipBackupSystemDb    bool              `json:"skipBackupSysDb"`
	WaitBackupSysTaskDone bool              `json:"waitBackupSysTaskDone"`
	BsTag                 string            `json:"bs_tag"`
	BackupType            string            `json:"backupType"` // 只能是 logical
	Args                  struct {
		BackupNode string      `json:"backupNode"`
		IsPartial  bool        `json:"isPartial"` // 为true时，备份指定库和表
		Oplog      bool        `json:"oplog"`     // 是否备份oplog，只有在IsPartial为false可为true
		NsFilter   NsFilterArg `json:"nsFilter"`
	} `json:"args"`
}

type backupJob struct {
	BaseJob
	BinDir         string
	MongoDump      string
	ConfParams     *backupParams
	MongoInst      *mymongo.MongoHost
	MongoClient    *mongo.Client
	ReportFilePath string
}

func (s *backupJob) Param() string {
	o, _ := json.MarshalIndent(backupParams{}, "", "\t")
	return string(o)
}

// NewBackupJob 实例化结构体
func NewBackupJob() jobruntime.JobRunner {
	return &backupJob{}
}

// Name 获取原子任务的名字
func (s *backupJob) Name() string {
	return "mongodb_backup"
}

// Run 运行原子任务
func (s *backupJob) Run() error {
	switch s.ConfParams.BackupType {
	case backupTypeLogical:
		return s.doLogicalBackup()
	default:
		return errors.Errorf("backupType %s not implemented", s.ConfParams.BackupType)
	}
	return nil
}

// getBackupPath return path Like /data/dbbak
func getBackupPath() (string, error) {
	backupPath := path.Join(consts.GetMongoBackupDir(), "dbbak")
	if !util.FileExists(backupPath) {
		return "", errors.Errorf("Dir Not Exists, Dir:%s", backupPath)
	}
	return backupPath, nil
}

// getMongoDumpOutPath return path Like /data/dbbak/mongodump-$unixtime
func getMongoDumpOutPath() (string, string, error) {
	backupDir, err := getBackupPath()
	if err != nil {
		return "", "", err
	}

	for i := 0; i < 10; i++ {
		tmpName := fmt.Sprintf("mongodump-%d", time.Now().Unix())
		tmpDir := path.Join(backupDir, tmpName)
		if util.FileExists(tmpDir) {
			time.Sleep(time.Second)
			continue
		}
		err = util.MkDirsIfNotExists([]string{tmpDir})
		if err != nil {
			return "", "", err
		}
		err = util.LocalDirChownMysql(tmpDir)
		return tmpDir, tmpName, err

	}
	return "", "", errors.New("getBackupPath failed")
}

// doLogicalBackup backup by mongodump
func (s *backupJob) doLogicalBackup() error {
	tmpPath, tmpDir, err := getMongoDumpOutPath()
	if err != nil {
		return errors.Wrap(err, "getMongoDumpOutPath")
	}
	helper := logical.NewMongoDumpHelper(s.MongoInst, s.MongoDump,
		s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "admin", s.OsUser)
	var startTime, endTime time.Time
	startTime = time.Now()
	if s.ConfParams.Args.IsPartial {
		// backupType = "dumpPartial"
		partialArgs := s.ConfParams.Args.NsFilter
		filter := logical.NewNsFilter(
			partialArgs.DbList, partialArgs.IgnoreDbList,
			partialArgs.ColList, partialArgs.IgnoreColList)

		cmdLineList, cmdLine, err := helper.DumpPartial(tmpPath, "dump.log", filter)

		if err != nil {
			s.runtime.Logger.Error("exec cmd fail, cmd: %s, error:%s", cmdLine, err)
			return errors.Wrap(err, "LogicalDumpPartial")
		}
		s.runtime.Logger.Info("exec cmd success, cmd: %+v", cmdLineList)
	} else {
		// backupType = "dumpAll"
		cmdLine, err := helper.LogicalDumpAll(tmpPath, "dump.log")
		if err != nil {
			s.runtime.Logger.Error("exec cmd fail, cmd: %s, error:%s", cmdLine, err)
			return err
		}
		s.runtime.Logger.Info("exec cmd success, cmd: %s", cmdLine)
		// admin 目录不备份 s.param.Args.IsPartial == false
		if s.ConfParams.SkipBackupSystemDb {
			err = helper.RemoveAdminDir(tmpPath)
			if err != nil {
				s.runtime.Logger.Error("remove %s/admin failed, err %v", tmpPath, err)
				return errors.Wrap(err, "RemoveAdminDir")
			}
		}
	}

	tarFile := fmt.Sprintf("%s.tar", tmpDir)
	tarPath := path.Join(path.Dir(tmpPath), tarFile)
	if err = s.chdir(path.Dir(tmpPath)); err != nil {
		return errors.Wrap(err, "chdir")
	}

	tarCmd := mycmd.New("tar", "cvf", tarPath, tmpDir)
	var exitCode int
	exitCode, _, _, err = tarCmd.Run(time.Hour * 24)
	s.runtime.Logger.Info("exec cmd: %q, exitCode:%d, err:%v", tarCmd.GetCmdLine2(true), exitCode, err)
	if exitCode != 0 {
		return errors.Wrap(err, "tar")
	}
	if err = s.removeDir(tmpDir); err != nil {
		return err
	}
	endTime = time.Now()
	fSize, _ := util.GetFileSize(tarPath)
	s.runtime.Logger.Info("backup file: %s size: %d", tarPath, fSize)
	// 上报备份记录。
	task, err := backupsys.UploadFile(tarPath, s.ConfParams.BsTag)
	// 如果此处失败，任务失败。
	// TODO: 如何让下次重试可以继续上传？
	if err != nil {
		s.runtime.Logger.Error("UploadFileToBackupSys Failed, err:%v", err)
		return errors.Wrap(err, "UploadFileToBackupSys")
	}
	s.runtime.Logger.Info("BackupSys taskid %s", task.TaskId)
	// 上报备份记录

	if err = task.SaveToFile(); err != nil {
		s.runtime.Logger.Error("SaveToFile Failed, err:%v", err)
		return errors.Wrap(err, "SaveToFile")
	}

	return s.appendToReportFile(startTime, endTime, task, tarPath, tarFile, fSize)
}

func (s *backupJob) appendToReportFile(
	startTime, endTime time.Time, task *backupsys.TaskInfo,
	tarPath, tarFile string, fSize int64) error {
	rec := report.NewBackupRecord()
	rec.AppendFileInfo(startTime.Local().Format(time.RFC3339),
		endTime.Local().Format(time.RFC3339),
		tarPath, tarFile, fSize)
	rec.AppendMetaLabel(&s.ConfParams.BkDbmInstance)
	rec.AppendBillSrc(s.runtime.UID, "todo", 1, 1)
	rec.AppendBsInfo(task.TaskId, task.Tag)
	err := report.AppendObjectToFile(s.ReportFilePath, rec)
	if err != nil {
		s.runtime.Logger.Error("Add Record to BackupReport Failedreport file:%s, record %+v", s.ReportFilePath, err)
		return errors.Wrap(err, "Add Record to BackupReport")
	} else {
		s.runtime.Logger.Info("Add Record to BackupReport Success, report file:%s, record %+v", s.ReportFilePath, rec)
	}
	return nil

}

// Retry 重试
func (s *backupJob) Retry() uint {
	// do nothing
	return 2
}

// Rollback 回滚
func (s *backupJob) Rollback() error {
	return nil
}

// Init 初始化
func (s *backupJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.OsUser = "" // 备份进程，不再需要sudo，请以普通用户执行
	if checkIsRootUser() {
		s.runtime.Logger.Error("This job cannot be executed as root user")
		return errors.New("This job cannot be executed as root user")
	}
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error(tmpErr.Error())
		return tmpErr
	}

	// todo Check Filter Args
	if s.ConfParams.Args.IsPartial {

	}

	s.ReportFilePath, _, _ = consts.GetMongoBackupReportPath()
	if err := report.PrepareReportPath(s.ReportFilePath); err != nil {
		return errors.Wrap(err, "PrepareReportPath")
	}

	s.MongoInst = mymongo.NewMongoHost(
		s.ConfParams.IP, fmt.Sprintf("%d", s.ConfParams.Port),
		"admin", s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "", s.ConfParams.IP)

	// prepare mongo client and mongodump path
	client, err := s.MongoInst.Connect()
	if err != nil {
		return errors.Wrap(err, "Connect")
	}
	version, err := mymongo.GetMongoServerVersion(client)
	if err != nil {
		return errors.Wrap(err, "GetMongoServerVersion")
	}
	// Set Tools Path
	s.MongoDump, err = consts.GetMongodumpBin(version)
	if err != nil {
		return errors.Wrap(err, "get mongodump")
	}
	if !util.FileExists(s.MongoDump) {
		return errors.Errorf("mongodump not exists, path:%s", s.MongoDump)
	}
	return nil
}

// checkParams 校验参数
func (s *backupJob) checkParams() error {
	// 校验配置参数
	validate := validator.New()
	if err := validate.Struct(s.ConfParams); err != nil {
		return fmt.Errorf("validate parameters of deleteUser fail, error:%s", err)
	}

	if s.ConfParams.BackupType == backupTypePhysical {
		err := errors.New("not implemented")
		return err
	} else if s.ConfParams.BackupType == backupTypeLogical {
		// todo
	} else {
		err := errors.Errorf("bad BackupType:%s", s.ConfParams.BackupType)
		return err
	}
	return nil
}
