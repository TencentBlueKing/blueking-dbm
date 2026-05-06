package atommongodb

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
	"dbm-services/mongodb/db-tools/dbmon/config"
	dbmonconsts "dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/backupsys"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/report"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/logical"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/pitr"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/mongo"
)

const backupTypeLogical string = "logical"

// 备份
// 1. 分析参数，确定要备份的库和表
// 2. 执行备份
// 3. 上报备份记录
// 4. 上报到备份系统，等待备份系统完成

// backupParams 备份任务参数，由前端传入
type backupParams struct {
	BkDbmInstance         config.BkDbmLabel `json:"bk_dbm_instance"`
	IP                    string            `json:"ip"`
	Port                  int               `json:"port"`
	AdminUsername         string            `json:"adminUsername"`
	AdminPassword         string            `json:"adminPassword"`
	SkipBackupSystemDb    bool              `json:"skipBackupSysDb"`
	WaitBackupSysTaskDone bool              `json:"waitBackupSysTaskDone"`
	FileTag               string            `json:"fileTag"`        // fileTag normal_backup or forever_backup
	BackupType            string            `json:"backupType"`     // 只能是 logical
	MaxConcurrency        int               `json:"maxConcurrency"` // 最大并发数，默认为4
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
	// fetch concurrency lock
	lock, err := s.GetConcurrentLock(s.ConfParams.MaxConcurrency)
	if err != nil {
		s.runtime.Logger.Error("GetConcurrentLock failed, err:%s", err)
		return errors.Wrap(err, "GetConcurrentLock")
	}
	defer lock.Unlock()

	err = s.removeOldBackupFilesStep()
	if err != nil {
		s.runtime.Logger.Error("removeOldBackupFilesStep failed, err:%s", err)
		return errors.Wrap(err, "removeOldBackupFilesStep")
	}

	switch s.ConfParams.BackupType {
	case backupTypeLogical:
		return s.doLogicalBackup()
	default:
		return errors.Errorf("backupType %s not implemented", s.ConfParams.BackupType)
	}
}

// getBackupPath return path Like /data/dbbak
func getBackupPath() (string, error) {
	dbbakPath := path.Join(consts.GetMongoBackupDir(), "dbbak")
	if !util.FileExists(dbbakPath) {
		return "", errors.Errorf("Dir Not Exists, Dir:%s", dbbakPath)
	}
	backupPath := path.Join(dbbakPath, "billdump")
	err := util.MkDirsIfNotExists([]string{backupPath})
	if err != nil {
		return "", errors.Wrap(err, "MkDirsIfNotExists")
	}
	return backupPath, nil
}

// getMongoDumpOutPath return path Like /data/dbbak/mongodump-$unixtime
func getMongoDumpOutPath(ip string, port int) (string, string, error) {
	backupDir, err := getBackupPath()
	if err != nil {
		return "", "", err
	}

	for i := 0; i < 10; i++ {
		tmpName := fmt.Sprintf("mongodump-%s-%d-%d", ip, port, time.Now().Unix())
		tmpDir := path.Join(backupDir, tmpName)
		if util.FileExists(tmpDir) {
			time.Sleep(time.Second)
			continue
		}
		err = util.MkDirsIfNotExists([]string{tmpDir})
		if err != nil {
			return "", "", err
		}

		// err = util.LocalDirChownMysql(tmpDir)
		return tmpDir, tmpName, err

	}
	return "", "", errors.New("getBackupPath failed")
}

func (s *backupJob) removeOldBackupFilesStep() error {
	// removeOldBackupFiles
	billDumpDir := path.Join(consts.GetMongoBackupDir(), "dbbak", "billdump")
	if !util.FileExists(billDumpDir) {
		// billDumpDir not exists, skip
		return nil
	}

	rmLockFile := path.Join(billDumpDir, "remove_old_backup_files.lock")
	rmLock, err := util.GetFileLock(rmLockFile, 1)
	if err == nil {
		s.runtime.Logger.Info("removeOldBackupFiles start")
		s.removeOldBackupFiles(billDumpDir)
		rmLock.Unlock()
		s.runtime.Logger.Info("removeOldBackupFiles end")
	}
	return nil
}

// removeOldBackupFiles remove old backup files
// 删除上次备份产生的备份文件
// 1. 属于taskinfo.文件或者备份文件
// 2. 文件时间超过30天 或者 task status 为 done
// 要避免把刚产生的文件删除掉了.
// 要避免多个备份任务同时去调用这个函数

func (s *backupJob) removeOldBackupFiles(backupDir string) error {
	fileList := []string{}
	// get all files in backupDir, exclude sub directories
	files, err := os.ReadDir(backupDir)
	if err != nil {
		return errors.Wrap(err, "ReadDir")
	}
	for _, file := range files {
		if file.IsDir() {
			continue
		}
		filePath := path.Join(backupDir, file.Name())
		fileList = append(fileList, filePath)
	}

	minSaveDay := 1
	savedDay := 30
	for _, file := range fileList {
		fileName := filepath.Base(file)
		isTaskInfo := strings.HasPrefix(fileName, "taskinfo.")
		if !isTaskInfo && !isBackupFileName(fileName) {
			// 不是taskinfo.文件或者备份文件，跳过
			s.runtime.Logger.Info("removeOldBackupFiles: Not taskinfo. file or backup file, file:%s", file)
			continue
		}

		fileInfo, err := os.Stat(file)
		if err != nil {
			continue
		}

		// 如果更新时间在1天内，跳过
		if fileInfo.ModTime().After(time.Now().Add(-time.Hour * 24 * time.Duration(minSaveDay))) {
			continue
		}

		// 文件时间超过savedDay天，则删除
		if fileInfo.ModTime().Before(time.Now().Add(-time.Hour * 24 * time.Duration(savedDay))) { // savedDay天前
			err = os.Remove(file)
			s.runtime.Logger.Info("Remove backup file %s %v", file, retStringBool(err))
			continue
		}

		// 是taskinfo.文件，则处理taskinfo.文件
		if isTaskInfo {
			taskInfo, err := backupsys.LoadTaskInfoFile(file)
			if err != nil {
				s.runtime.Logger.Warn("LoadTaskInfoFile file %s failed, err:%v", file, err)
				continue
			}
			if taskInfo.TaskId == "" {
				s.runtime.Logger.Warn("TaskInfo.TaskId is empty, file:%s", file)
				continue
			}

			if taskInfo.FilePath == "" {
				s.runtime.Logger.Warn("TaskInfo.FilePath is empty, file:%s", file)
				continue
			}

			// if taskInfo.FilePath is not exists
			if !util.FileExists(taskInfo.FilePath) {
				s.runtime.Logger.Warn("TaskInfo.FilePath not exists, file:%s", taskInfo.FilePath)
				// 删除taskinfo.文件
				err = os.Remove(file)
				s.runtime.Logger.Info("Remove taskinfo file %s %v", file, retStringBool(err))
				continue
			} else {
				// 如果filePath是绝对路径，且在backupDir目录下，则尝试处理taskinfo.文件中的备份文件
				if filepath.IsAbs(taskInfo.FilePath) && isBackupFileName(taskInfo.FilePath) {
					// GetTaskInfo 获取备份系统中的任务状态
					backupInfo, err := backupsys.GetTaskInfo(taskInfo.TaskId)
					if err != nil {
						s.runtime.Logger.Warn("GetTaskInfo file %s failed, err:%v", file, err)
						continue
					}
					if backupInfo.Status == backupsys.TaskStatusDone {
						err = os.Remove(taskInfo.FilePath)
						s.runtime.Logger.Info("Remove backup file %s %v", taskInfo.FilePath, retStringBool(err))
						err = os.Remove(file)
						s.runtime.Logger.Info("Remove taskinfo file %s %v", file, retStringBool(err))
						continue
					}
				} else {
					s.runtime.Logger.Warn("TaskInfo.FilePath is not in backupDir, file:%s", taskInfo.FilePath)
				}
			}
		}
	}
	return nil
}

func isBackupFileName(filePath string) bool {
	fileName := filepath.Base(filePath)
	return strings.HasPrefix(fileName, "mongodump-") &&
		(strings.HasSuffix(fileName, ".tar.zstd") || strings.HasSuffix(fileName, ".tar"))
}

func retStringBool(err error) string {
	if err != nil {
		return "failed: " + err.Error()
	}
	return "success"
}

// doLogicalBackup backup by mongodump
func (s *backupJob) doLogicalBackup() error {
	s.runtime.Logger.Info("dump start")
	tmpPath, tmpDirName, err := getMongoDumpOutPath(s.ConfParams.IP, s.ConfParams.Port)
	if err != nil {
		return errors.Wrap(err, "getMongoDumpOutPath")
	}
	helper := logical.NewMongoDumpHelper(s.MongoInst, s.MongoDump,
		s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "admin", s.OsUser)
	var startTime, endTime time.Time
	startTime = time.Now()
	isEmptyBackup := 0

	// 规则. setName为-conf的，认为是configsvr
	isConfigBackup := 0
	if strings.HasSuffix(s.ConfParams.BkDbmInstance.SetName, "-conf") {
		isConfigBackup = 1
	}

	if s.ConfParams.Args.IsPartial {
		// backupType = "dumpPartial"
		partialArgs := s.ConfParams.Args.NsFilter
		filter := logical.NewNsFilter(
			partialArgs.DbList, partialArgs.IgnoreDbList,
			partialArgs.ColList, partialArgs.IgnoreColList)
		_, lastCmdLine, dbColList, _, err := helper.DumpPartial(tmpPath, "dump.log", filter, nil)

		if err != nil {
			s.runtime.Logger.Error("exec cmd fail, cmd: %s, error:%s", lastCmdLine, err)
			return errors.Wrap(err, "LogicalDumpPartial")
		}

		dbCount, colCount := 0, 0
		for _, ns := range dbColList {
			if len(ns.Col) > 0 {
				dbCount++
				colCount += len(ns.Col)
			}
		}
		for _, ns := range dbColList {
			if len(ns.Col) == 0 {
				s.runtime.Logger.Info(fmt.Sprintf("db %q has no matched collection", ns.Db))
			} else {
				s.runtime.Logger.Info(fmt.Sprintf("db %q has %d matched collection: %q", ns.Db,
					len(ns.Col), strings.Join(ns.Col, ",")))
			}
		}

		if dbCount == 0 {
			isEmptyBackup = 1
			s.runtime.Logger.Warn("no matched db and collection, will create a empty backup record")
			os.MkdirAll(tmpPath, 0755)
			err = os.WriteFile(path.Join(tmpPath, "dump.log"),
				[]byte("no matched db and collection, will create a empty backup record"), 0644)
			if err != nil {
				s.runtime.Logger.Error("create empty backup record failed, err:%v", err)
				return errors.Wrap(err, "create empty backup record")
			}
		}

		s.runtime.Logger.Info("exec cmd success,  db:%d collection:%d", dbCount, colCount)
	} else {
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

	// 非configsvr 不备份config
	if isConfigBackup == 0 {
		err = helper.RemoveConfigDir(tmpPath)
		if err == nil {
			s.runtime.Logger.Info("remove %s/config success", tmpPath)
		}
	}
	s.runtime.Logger.Info("dump end, start make archive file")
	tarStartTime := time.Now()
	var tarPath, tarFileName string
	if isTlinux12() {
		tarPath, tarFileName, err = s.makeArchiveFileGzip(tmpPath, tmpDirName)
	} else {
		tarPath, tarFileName, err = s.makeArchiveFileZstd(tmpPath, tmpDirName)
	}
	endTime = time.Now()
	s.runtime.Logger.Info("makeArchiveFile cost time: %0.1f seconds", endTime.Sub(tarStartTime).Seconds())
	if err != nil {
		return errors.Wrap(err, "makeArchiveFile")
	}

	fSize, _ := util.GetFileSize(tarPath)
	s.runtime.Logger.Info("backup file: %s size: %d", tarPath, fSize)
	fileTag, err := getMongoBackupFileTag(s.ConfParams.FileTag)
	if err != nil {
		return errors.Wrap(err, "getMongoBackupFileTag")
	}
	// 上报备份记录。
	task, err := backupsys.UploadFile(tarPath, fileTag)
	if err != nil {
		s.runtime.Logger.Error("backupsys.UploadFile Failed, err:%v", err)
		return errors.Wrap(err, "backupsys.UploadFile")
	}
	s.runtime.Logger.Info("BackupSys taskid %s", task.TaskId)
	// 上报备份记录

	if err = task.SaveToFile(); err != nil {
		s.runtime.Logger.Error("SaveToFile Failed, err:%v", err)
		return errors.Wrap(err, "SaveToFile")
	}

	// 保存备份系统任务信息
	return s.appendToReportFile(startTime, endTime, task, tarPath, tarFileName, fSize, isEmptyBackup, isConfigBackup)
}

// isTlinux12 判断是否是tlinux1.2系统. 读取/etc/os-release文件，判断是否包含tlinux1.2
func isTlinux12() bool {
	v12 := "Tencent tlinux release 1.2"
	osReleaseFile := "/etc/tlinux-release"
	if !util.FileExists(osReleaseFile) {
		return false
	}
	osRelease, err := os.ReadFile(osReleaseFile)
	if err != nil {
		return false
	}

	return strings.Contains(string(osRelease), v12)
}

// makeArchiveFile 制作归档文件. 使用tar命令，并使用zstd压缩. 如果系统是tlinux1.2 则使用gzip
func (s *backupJob) makeArchiveFileZstd(tmpPath, tmpDirName string) (string, string, error) {
	tarFileName := fmt.Sprintf("%s.tar.zstd", tmpDirName)
	tarPath := path.Join(path.Dir(tmpPath), tarFileName)
	if err := s.chdir(path.Dir(tmpPath)); err != nil {
		return "", "", errors.Wrap(err, "chdir")
	}
	zstdPath, err := dbmonconsts.FindBinPath("zstd", dbmonconsts.GetDbTool("mongotools"))
	if err != nil {
		return "", "", errors.Wrap(err, "zstd bin not found in path: "+dbmonconsts.GetDbTool("mongotools"))
	}
	ret, err := mycmd.New("tar", "--remove-files", "-I", zstdPath, "-cf", tarPath, tmpDirName).Run(time.Hour * 24)
	if err != nil {
		return "", "", errors.Wrap(err, "tar")
	}
	s.runtime.Logger.Info("exec cmd: %q, exitCode:%d, err:%v", ret.Cmdline, ret.ExitCode, err)
	return tarPath, tarFileName, nil
}

// makeArchiveFile 制作归档文件. 使用tar命令，并使用zstd压缩. 如果系统是tlinux1.2 则使用gzip
// 使用--remove-files参数，删除临时目录
func (s *backupJob) makeArchiveFileGzip(tmpPath, tmpDirName string) (string, string, error) {
	tarFileName := fmt.Sprintf("%s.tar.gz", tmpDirName)
	tarPath := path.Join(path.Dir(tmpPath), tarFileName)
	if err := s.chdir(path.Dir(tmpPath)); err != nil {
		return "", "", errors.Wrap(err, "chdir")
	}

	ret, err := mycmd.New("tar", "--remove-files", "-czf", tarPath, tmpDirName).Run(time.Hour * 24)
	if err != nil {
		return "", "", errors.Wrap(err, "tar")
	}
	s.runtime.Logger.Info("exec cmd: %q, exitCode:%d, err:%v", ret.Cmdline, ret.ExitCode, err)
	return tarPath, tarFileName, nil
}

func (s *backupJob) appendToReportFile(
	startTime, endTime time.Time, task *backupsys.TaskInfo,
	tarPath, tarFile string, fSize int64, isEmptyBackup, isConfigBackup int) error {
	rec := report.NewBackupRecord()
	rec.AppendFileInfo(startTime.Local().Format(time.RFC3339),
		endTime.Local().Format(time.RFC3339),
		tarPath, tarFile, fSize)
	rec.AppendMetaLabel(&s.ConfParams.BkDbmInstance)
	rec.AppendBillSrc(s.runtime.UID, "todo", 1, 1, isEmptyBackup, isConfigBackup)
	rec.AppendBsInfo(task.TaskId, task.Tag)
	err := report.AppendObjectToFile(s.ReportFilePath, rec)
	if err != nil {
		s.runtime.Logger.Error("Add Record to BackupReport Failedreport file:%s, record %+v", s.ReportFilePath, err)
		return errors.Wrap(err, "Add Record to BackupReport")
	} else {
		json, _ := json.Marshal(rec)
		s.runtime.Logger.Info("Add Record to BackupReport Success, report file:%s, labels:%s", s.ReportFilePath,
			string(json))
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

	s.ReportFilePath, _, _ = dbmonconsts.GetMongoBackupReportPath()
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
	s.MongoDump, err = pitr.GetMongoDumpBin(version)
	if err != nil {
		return errors.Wrap(err, "get mongodump")
	}
	if !util.FileExists(s.MongoDump) {
		return errors.Errorf("mongodump not exists, path:%s", s.MongoDump)
	}

	// set default file tag if not set
	if s.ConfParams.FileTag == "" {
		s.ConfParams.FileTag = consts.NormalBackupType
	}

	_, err = getMongoBackupFileTag(s.ConfParams.FileTag)
	if err != nil {
		return errors.Wrap(err, "getMongoBackupFileTag")
	}
	return nil
}

/*
getMongoBackupFileTag 备份Tag映射关系：
备份Tag来自前端传入，需要映射到备份系统支持的Tag，兼容以后直接使用前端传入的Tag

	normal_backup -> DBFILE1M
	half_year_backup -> DBFILE6M
	a_year_backup -> DBFILE1Y
	forever_backup -> DBFILE3Y
*/
func getMongoBackupFileTag(fileTag string) (string, error) {
	tagMap := map[string]string{
		consts.NormalBackupType:  "DBFILE1M",
		consts.ForeverBackupType: "DBFILE3Y",
		"half_year_backup":       "DBFILE6M",
		"a_year_backup":          "DBFILE1Y",
		"DBFILE1M":               "DBFILE1M",
		"DBFILE6M":               "DBFILE6M",
		"DBFILE1Y":               "DBFILE1Y",
		"DBFILE3Y":               "DBFILE3Y",
	}

	if tag, ok := tagMap[fileTag]; ok {
		return tag, nil
	}
	return "", errors.Errorf("invalid file tag: %s", fileTag)

}
