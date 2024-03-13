package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/logical"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/mongo"
)

// BsTaskArg 备份任务，作为参数传入
type BsTaskArg struct {
	TaskId   string `json:"task_id"`
	FileName string `json:"file_name"`
}

// 回档
// 1. 将备份文件解压到临时目录.
// 2. 检查目标MongoDB中，没有要恢复的库和表.
// 3. 执行恢复，并将恢复日志写入到文件中.
// 4. 检查恢复日志，如果有错误，返回错误.
// 5. 删除临时目录

// restoreParam 备份任务参数，由前端传入
type restoreParam struct {
	IP            string `json:"ip"`
	Port          int    `json:"port"`
	AdminUsername string `json:"adminUsername"`
	AdminPassword string `json:"adminPassword"`
	InstanceType  string `json:"instanceType"`

	Args struct {
		RecoverDir string      `json:"RecoverDir"` // /data/dbbak/recover_mg/
		SrcFile    []BsTaskArg `json:"srcFile"`    // 目前只需要1个文件，但是为了兼容，还是使用数组.
		IsPartial  bool        `json:"isPartial"`  // 为true时，备份指定库和表
		Oplog      bool        `json:"oplog"`      // 是否备份oplog，只有在IsPartial为false可为true
		NsFilter   NsFilterArg `json:"nsFilter"`
	} `json:"Args"`
}

type restoreJob struct {
	BaseJob
	param           *restoreParam
	BinDir          string
	MongoRestoreBin string
	MongoInst       *mymongo.MongoHost
	MongoClient     *mongo.Client
}

func (s *restoreJob) Param() string {
	o, _ := json.MarshalIndent(restoreParam{}, "", "\t")
	return string(o)
}

// NewRestoreJob 实例化结构体
func NewRestoreJob() jobruntime.JobRunner {
	return &restoreJob{}
}

// Name 获取原子任务的名字
func (s *restoreJob) Name() string {
	return "mongo_restore"
}

// Run 运行原子任务
func (s *restoreJob) Run() error {
	err := s.checkDstMongo()
	if err != nil {
		return errors.Wrap(err, "checkDstMongo")
	}
	s.runtime.Logger.Info("checkDstMongo ok")
	// 1. check dst mongo is ok
	return s.doLogicalRestore()
}

// checkDstMongo 检查目标MongoDB中，没有要恢复的库和表.
func (s *restoreJob) checkDstMongo() error {
	// todo Check Filter Args
	if s.param.Args.IsPartial {
		// 1. 按照db和col过滤，检查目标库表是否已经存在. 如果存在，报错.
		filter := logical.NewNsFilter(s.param.Args.NsFilter.DbList,
			s.param.Args.NsFilter.IgnoreDbList,
			s.param.Args.NsFilter.ColList,
			s.param.Args.NsFilter.IgnoreColList)

		dbColList, err := logical.GetDbCollectionWithFilter(s.MongoInst.Host, s.MongoInst.Port,
			s.MongoInst.User, s.MongoInst.Pass, s.MongoInst.AuthDb, filter)
		if err != nil {
			return errors.Wrap(err, "GetDbCollectionWithFilter")
		}
		if len(dbColList) >= 0 {
			return errors.New("some db or col already exists")
		}
	}

	return nil
}

// doLogicalRestore do Restore From a File
func (s *restoreJob) doLogicalRestore() error {
	log := s.runtime.Logger
	helper := logical.NewMongoRestoreHelper(s.MongoInst, s.MongoRestoreBin, s.param.AdminUsername,
		s.param.AdminPassword, "admin", s.OsUser)

	srcFilePath := filepath.Join(s.param.Args.RecoverDir, s.param.Args.SrcFile[0].FileName)
	fileSize, err := util.GetFileSize(srcFilePath)
	if err != nil {
		return errors.Wrap(err, "GetFileSize")
	}

	log.Info("start untar file %s, fileSize %d", srcFilePath, fileSize)
	dstDir, err := logical.UntarFile(srcFilePath)
	if err != nil {
		return errors.Wrap(err, "UntarFile")
	}
	log.Info("end untar file %s, dstDir %s", srcFilePath, dstDir)
	dstDirWithDump := path.Join(dstDir, "dump")
	// get DbCollection from Dir
	dbColList, err := logical.GetDbCollectionFromDir(dstDirWithDump)
	if err != nil {
		return errors.Wrap(err, "GetDbCollectionFromDir")
	}

	for _, row := range dbColList {
		if row.Db == "admin" {
			continue
		}
	}

	// 导入部分表时，要删除掉不需要的库和表文件.
	s.removeNsByFilter(dbColList, dstDirWithDump)

	// 检查文件是否已存在.

	// 2. 执行恢复，并将恢复日志写入到文件中.
	restoreLog, err := helper.Restore(dstDirWithDump, dstDir, s.param.Args.Oplog)
	if err != nil {
		lines, err2 := util.GetLastLine(restoreLog, 5)
		if err2 != nil || len(lines) == 0 {
			log.Error("restore failed. get restore log failed, err: %v", err2)
		} else {
			log.Error("restore failed. try to print last %d line of restore.log...", len(lines))
			for _, line := range lines {
				log.Error("restore.log %s", line)
			}
		}
		return errors.Wrap(err, "RestoreFailed")
	}

	restoreSucc, restoreFailed, restoreErr := logical.CheckRestoreLog(restoreLog)
	log.Info("CheckRestoreLog: succ: %d, failed: %d, err: %v", restoreSucc, restoreFailed, restoreErr)
	if restoreErr != nil {
		log.Error("checkRestoreLog error: %s", restoreErr)
		return restoreErr
	} else if restoreFailed > 0 {
		log.Error("%d document restore succ, %d document restore failed", restoreSucc, restoreFailed)
		return errors.Errorf("%d document restore succ, %d document restore failed", restoreSucc, restoreFailed)
	}

	if err := os.RemoveAll(dstDirWithDump); err != nil {
		log.Error("remove %s failed %v", dstDir, err)
		return errors.Wrap(err, fmt.Sprintf("remove %s failed", dstDir))
	}
	log.Info("remove %s success", dstDir)
	return nil
}

func (s *restoreJob) removeNsByFilter(dbColList []logical.DbCollection, dstDir string) error {
	// 导入部分表时，要删除掉不需要的库和表文件.
	if !s.param.Args.IsPartial {
		return nil
	}
	filter := logical.NewNsFilter(s.param.Args.NsFilter.DbList, s.param.Args.NsFilter.IgnoreDbList,
		s.param.Args.NsFilter.ColList, s.param.Args.NsFilter.IgnoreColList)

	// todo 支持部分恢复 这里要删除掉不需要的库和表文件.
	for _, row := range dbColList {
		if row.Db == "admin" {
			continue
		}
		if !filter.IsDbMatched(row.Db) {
			os.RemoveAll(fmt.Sprintf("%s/%s", dstDir, row.Db))
			continue
		}
		matchList, notMatchList := filter.FilterTb(row.Col)
		if len(matchList) == 0 {
			os.RemoveAll(fmt.Sprintf("%s/%s", dstDir, row.Db))
			continue
		}
		for _, col := range notMatchList {
			var toDelFileList = []string{}
			toDelFileList = append(toDelFileList,
				fmt.Sprintf("%s/%s/%s.bson", dstDir, row.Db, col),
				fmt.Sprintf("%s/%s/%s.bson.gz", dstDir, row.Db, col),
				fmt.Sprintf("%s/%s/%s.metadata.json", dstDir, row.Db, col),
			)
			for _, file := range toDelFileList {
				if !util.FileExists(file) {
					continue
				}
				err := os.Remove(file)
				if err != nil {
					return errors.Wrap(err, fmt.Sprintf("Remove %s", file))
				}
			}
		}
	}
	return nil

}

// Retry 重试
func (s *restoreJob) Retry() uint {
	// do nothing
	return 2
}

// Rollback 回滚
func (s *restoreJob) Rollback() error {
	return nil
}

// Init 初始化
func (s *restoreJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.OsUser = ""

	if err := s.checkParams(); err != nil {
		s.runtime.Logger.Error(err.Error())
		return err
	}

	if util.FileExists(s.param.Args.RecoverDir) == false {
		return errors.New("recover dir is empty")
	}

	// prepare mongo client and mongodump path
	s.MongoInst = mymongo.NewMongoHost(
		s.param.IP, fmt.Sprintf("%d", s.param.Port),
		"admin", s.param.AdminUsername, s.param.AdminPassword, "", s.param.IP)

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
	s.MongoRestoreBin, err = consts.GetMongorestoreBin(version)
	if err != nil {
		return errors.Wrap(err, "get mongodump")
	}
	if !util.FileExists(s.MongoRestoreBin) {
		return errors.Errorf("mongorestore not exists, path:%s", s.MongoRestoreBin)
	}
	return nil
}

// checkParams 校验参数
func (s *restoreJob) checkParams() error {
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.param); err != nil {
		return errors.Wrap(err, "json.Unmarshal")
	}

	// 校验配置参数
	validate := validator.New()
	if err := validate.Struct(s.param); err != nil {
		return errors.Wrap(err, "validate params")
	}

	return nil
}
