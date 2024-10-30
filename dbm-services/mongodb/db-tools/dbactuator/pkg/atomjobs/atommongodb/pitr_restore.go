package atommongodb

import (
	"context"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/pitr"
	"encoding/json"
	"fmt"
	"os"
	"sync"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

// 备份
// 1. 分析参数，确定要备份的库和表
// 2. 执行备份
// 3. 上报备份记录
// 4. 上报到备份系统，等待备份系统完成

// restoreParam 备份任务参数，由前端传入
type pitrRecoverParam struct {
	IP              string `json:"ip"`
	Port            int    `json:"port"`
	AdminUsername   string `json:"adminUsername"`
	AdminPassword   string `json:"adminPassword"`
	SrcAddr         string `json:"srcAddr"`        // ip:port
	RecoverTimeStr  string `json:"recoverTimeStr"` // recoverTime yyyy-mm-ddTHH:MM:SS
	DryRun          bool   `json:"dryRun"`         // 测试模式
	Dir             string `json:"dir"`            // 备份文件存放目录.
	recvoerTimeUnix uint32 `json:"-"`
	//	InstanceType    string `json:"instanceType"`
}

type pitrRecoverJob struct {
	BaseJob
	param           *pitrRecoverParam
	BinDir          string
	MongoRestoreBin string
	MongoInst       *mymongo.MongoHost
	MongoClient     *mongo.Client
}

func (s *pitrRecoverJob) Param() string {
	o, _ := json.MarshalIndent(pitrRecoverParam{}, "", "\t")
	return string(o)
}

// NewPitrRecoverJob 实例化结构体
func NewPitrRecoverJob() jobruntime.JobRunner {
	return &pitrRecoverJob{}
}

// Name 获取原子任务的名字
func (s *pitrRecoverJob) Name() string {
	return "mongodb_pitr_restore"
}

// Run 运行原子任务
func (s *pitrRecoverJob) Run() error {
	type execFunc struct {
		name string
		f    func() error
	}

	for _, f := range []execFunc{
		{"checkDstMongo", s.checkDstMongo},
		//	{"checkSrcFileReady", s.checkSrcFileReady},
		{"dropConfigDb", s.dropConfigDb},
		{"doPitrRecover", s.doPitrRecover},
	} {
		s.runtime.Logger.Info("Run %s start", f.name)
		if err := f.f(); err != nil {
			s.runtime.Logger.Error("Run %s failed. err %s", f.name, err.Error())
			return errors.Wrap(err, f.name)
		}
		s.runtime.Logger.Info("Run %s done", f.name)
	}
	return nil
}

func (s *pitrRecoverJob) dropConfigDb() error {
	client, err := s.MongoInst.Connect()
	if err != nil {
		return errors.Wrap(err, "Connect")
	}
	inst := common.NewInstance(s.param.IP, s.param.Port, s.param.AdminUsername, s.param.AdminPassword, "")
	rsOp := common.NewRsOp()
	conf, err := rsOp.GetRsConf(inst)
	if err != nil {
		return errors.Wrap(err, "GetRsConf")
	}

	if !conf.Config.Configsvr {
		s.runtime.Logger.Info("not configsvr, skip drop config")
		return nil
	}

	// 流程的前面已经在mongos上检查上库表，这里可以不再检查
	// 检查 configsvr是否为空 database 表为空 -> 表示没有库
	n, err := client.Database("config").Collection("databases").CountDocuments(context.Background(), bson.M{})
	if err != nil {
		return errors.Wrap(err, "CountDocuments config.databases")
	}
	if n > 0 {
		return errors.Errorf("config.databases not empty, count:%d", n)
	}

	// 也许还有其他表，这里只删除几个常见的表.
	for _, col := range []string{"databases", "collections", "chunks", "changelog"} {
		if err := client.Database("config").Collection(col).Drop(context.Background()); err != nil {
			return errors.Wrap(err, fmt.Sprintf("Drop config.%s", col))
		} else {
			s.runtime.Logger.Info("Drop config.%s done", col)
		}
	}

	return nil
}

// checkDstMongo 目标必须为空.
func (s *pitrRecoverJob) checkDstMongo() error {
	client, err := s.MongoInst.Connect()
	if err != nil {
		return errors.Wrap(err, "Connect")
	}
	// 对版本没有要求
	dbList, err := client.ListDatabaseNames(context.TODO(), bson.M{})
	if err != nil {
		return errors.Wrap(err, "ListDatabaseNames")
	}
	var notEmptyDb []string
	for _, db := range dbList {
		if mymongo.IsSysDb(db) {
			continue
		}
		// test 是监控脚本使用的库，也可以略.
		if db == "test" {
			continue
		} else {
			notEmptyDb = append(notEmptyDb, db)
		}
	}
	if len(notEmptyDb) > 0 {
		return errors.Errorf("dst mongo not empty, db:%v", notEmptyDb)
	}
	return nil
}

// receiveLogBg 接收mongorestore过程中的日志
func (s *pitrRecoverJob) receiveLogBg() (*sync.WaitGroup, chan *pitr.ProcessLog) {
	logChan := make(chan *pitr.ProcessLog, 1)
	wg := &sync.WaitGroup{}
	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			select {
			case log, ok := <-logChan:
				if !ok {
					return
				}
				if log.IsErr {
					s.runtime.Logger.Error(log.Msg)
				} else {
					s.runtime.Logger.Info(log.Msg)
				}
			}
		}
	}()
	return wg, logChan
}

// doPitrRecover do Restore From a File
func (s *pitrRecoverJob) doPitrRecover() error {
	full, incrList, err := pitr.ParseSrcFileDir(s.param.SrcAddr, s.param.Dir, s.param.recvoerTimeUnix)
	if err != nil {
		return errors.Wrap(err, "ParseSrcFileDir")
	}

	wd, _ := os.Getwd()
	s.runtime.Logger.Info("current work dir:%s", wd)

	wg, logChan := s.receiveLogBg()
	if _, err = pitr.DoMongoRestoreFULL(s.MongoRestoreBin, s.MongoInst, full, s.param.Dir, logChan); err != nil {
		goto end
	}

	for idx, file := range incrList {
		os.Chdir(wd)
		pitr.SendProcessLog(logChan, fmt.Sprintf("start to restore incr file %s ", file.FileName))
		if err = pitr.DoMongoRestoreINCR(s.MongoRestoreBin, s.MongoInst,
			full, incrList, s.param.recvoerTimeUnix, s.param.Dir, idx); err != nil {
			err = errors.Wrap(err, fmt.Sprintf("DoMongoRestoreINCR %s", file.FileName))
			goto end
		}
		pitr.SendProcessLog(logChan, fmt.Sprintf("restore incr file %s done", file.FileName))
	}
end:
	close(logChan)
	wg.Wait()
	return err
}

// Retry 重试
func (s *pitrRecoverJob) Retry() uint {
	// do nothing
	return 2
}

// Rollback 回滚
func (s *pitrRecoverJob) Rollback() error {
	return nil
}

// Init 初始化
func (s *pitrRecoverJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	runtime.Logger.Info("Init start")
	s.runtime = runtime
	s.OsUser = ""

	type checkFunc struct {
		name string
		f    func() error
	}

	for _, f := range []checkFunc{
		{"checkParams", s.checkParams},
		{"checkDtsMongoVersion", s.checkVersion},
	} {

		if err := f.f(); err != nil {
			s.runtime.Logger.Error("%s failed. err %s", f.name, err.Error())
			return errors.Wrap(err, f.name)
		}
		s.runtime.Logger.Info("%s ok", f.name)
	}

	return nil
}

// checkVersion TODO
// checkParams 校验参数
func (s *pitrRecoverJob) checkVersion() error {
	s.MongoInst = mymongo.NewMongoHost(
		s.param.IP, fmt.Sprintf("%d", s.param.Port),
		"admin", s.param.AdminUsername, s.param.AdminPassword, "", s.param.IP)

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
func (s *pitrRecoverJob) checkParams() error {
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.param); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error(tmpErr.Error())
		return tmpErr
	}

	// 校验配置参数
	validate := validator.New()
	if err := validate.Struct(s.param); err != nil {
		return errors.Wrap(err, "validate params")
	}

	t, err := pitr.ParseTimeStr(s.param.RecoverTimeStr)
	if err != nil {
		return errors.Wrap(err, "ParseTimeStr")
	} else {
		s.param.recvoerTimeUnix = t
	}

	return nil
}
