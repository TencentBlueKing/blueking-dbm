package atommongodb

import (
	"context"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	dbmonconsts "dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/pitr"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"sync"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
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
	GracefulStop    *bool  `json:"gracefulStop,omitempty"`
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
		{"removeConfigDb", s.removeConfigDb},
		{"restartAsStandAlone", s.restartAsStandAlone},
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

// restartAsStandAlone TODO
func (s *pitrRecoverJob) restartAsStandAlone() error {
	op := common.NewInstanceOp(s.param.IP,
		s.param.Port,
		s.param.AdminUsername,
		s.param.AdminPassword,
		s.runtime.Logger,
	)
	err := op.DoStopWithOptions(common.StopOptions{Graceful: s.isGracefulStop()})
	if err != nil {
		return errors.New("stop config server failed")
	}
	err = op.DoStartAsStandAlone()
	if err != nil {
		return errors.New("start config server failed")
	}
	return nil
}

// isGracefulStop 是否优雅停止. 在pitrRecover中，默认不需要gracefulStop
func (s *pitrRecoverJob) isGracefulStop() bool {
	if s.param.GracefulStop == nil {
		return false
	}
	return *s.param.GracefulStop
}

// removeConfigDb 清空 configsvr 上会被回档覆盖的表，保留集合本身。
// 全量备份经常没有这些 bson。集合不存在时 applyOps 无法插入，所以缺了要先建。
func (s *pitrRecoverJob) removeConfigDb() error {
	client, err := s.MongoInst.Connect()
	if err != nil {
		return errors.Wrap(err, "Connect")
	}
	inst := common.NewInstance(s.param.IP, s.param.Port, s.param.AdminUsername, s.param.AdminPassword, "")
	isConfigsvr, err := s.isConfigsvr(inst)
	if err != nil {
		return err
	}
	if !isConfigsvr {
		s.runtime.Logger.Info("not configsvr, skip remove config")
		return nil
	}

	ctx := context.Background()
	names, err := client.Database("config").ListCollectionNames(ctx, bson.D{})
	if err != nil {
		return errors.Wrap(err, "ListCollectionNames config")
	}
	exists := map[string]struct{}{}
	for _, name := range names {
		exists[name] = struct{}{}
	}

	// 流程的前面已经在mongos上检查上库表，这里可以不再检查
	// 检查 configsvr是否为空 database 表为空 -> 表示没有库
	if _, ok := exists["databases"]; ok {
		n, err := client.Database("config").Collection("databases").CountDocuments(ctx, bson.M{})
		if err != nil {
			return errors.Wrap(err, "CountDocuments config.databases")
		}
		if n > 0 {
			return errors.Errorf("config.databases not empty, count:%d", n)
		}
	}

	// 只清文档。集合不存在就先建，后续增量 applyOps 才能写入。
	// changelog 官方是 capped、size 200MB、没有 max。不存在或被建成普通集合时按这个定义建。
	// 已经是 capped 的，drop 后沿用原来的 size/max。
	for _, col := range []string{"databases", "collections", "chunks", "changelog"} {
		if err := s.emptyConfigCollection(ctx, client, col, exists); err != nil {
			return err
		}
	}

	return nil
}

// changelogCappedBytes 对应 mongod 的 kChangeLogCollectionSizeMB，单位是字节。4.4 到 8.0 都是 200MB，没有 max。
const changelogCappedBytes int64 = 200 * 1024 * 1024

func (s *pitrRecoverJob) emptyConfigCollection(
	ctx context.Context, client *mongo.Client, col string, exists map[string]struct{},
) error {
	db := client.Database("config")
	if _, ok := exists[col]; !ok {
		if col == "changelog" {
			return s.createCappedConfigCollection(ctx, db, col, changelogCappedBytes, 0)
		}
		if err := db.CreateCollection(ctx, col); err != nil {
			return errors.Wrap(err, fmt.Sprintf("Create config.%s", col))
		}
		s.runtime.Logger.Info("Create config.%s done", col)
		return nil
	}

	capped, size, maxDocs, err := configCollectionCapped(ctx, db, col)
	if err != nil {
		return err
	}
	if col == "changelog" && !capped {
		if err := db.Collection(col).Drop(ctx); err != nil {
			return errors.Wrap(err, "Drop config.changelog")
		}
		return s.createCappedConfigCollection(ctx, db, col, changelogCappedBytes, 0)
	}
	if capped {
		if err := db.Collection(col).Drop(ctx); err != nil {
			return errors.Wrap(err, fmt.Sprintf("Drop capped config.%s", col))
		}
		if size <= 0 {
			size = changelogCappedBytes
		}
		return s.createCappedConfigCollection(ctx, db, col, size, maxDocs)
	}

	res, err := db.Collection(col).DeleteMany(ctx, bson.D{})
	if err != nil {
		return errors.Wrap(err, fmt.Sprintf("Remove config.%s", col))
	}
	s.runtime.Logger.Info("Remove config.%s done, deleted:%d", col, res.DeletedCount)
	return nil
}

func (s *pitrRecoverJob) createCappedConfigCollection(
	ctx context.Context, db *mongo.Database, col string, size, maxDocs int64,
) error {
	opts := options.CreateCollection().SetCapped(true).SetSizeInBytes(size)
	if maxDocs > 0 {
		opts.SetMaxDocuments(maxDocs)
	}
	if err := db.CreateCollection(ctx, col, opts); err != nil {
		return errors.Wrap(err, fmt.Sprintf("Create capped config.%s", col))
	}
	s.runtime.Logger.Info("Create capped config.%s done, size:%d max:%d", col, size, maxDocs)
	return nil
}

func configCollectionCapped(ctx context.Context, db *mongo.Database, name string) (bool, int64, int64, error) {
	cur, err := db.ListCollections(ctx, bson.M{"name": name})
	if err != nil {
		return false, 0, 0, errors.Wrap(err, "ListCollections "+name)
	}
	defer cur.Close(ctx)
	var docs []bson.M
	if err := cur.All(ctx, &docs); err != nil {
		return false, 0, 0, errors.Wrap(err, "ListCollections decode "+name)
	}
	if len(docs) == 0 {
		return false, 0, 0, nil
	}
	opts, _ := docs[0]["options"].(bson.M)
	if opts == nil {
		return false, 0, 0, nil
	}
	capped, _ := opts["capped"].(bool)
	return capped, bsonToInt64(opts["size"]), bsonToInt64(opts["max"]), nil
}

func bsonToInt64(v interface{}) int64 {
	switch n := v.(type) {
	case int32:
		return int64(n)
	case int64:
		return n
	case int:
		return int64(n)
	case float64:
		return int64(n)
	default:
		return 0
	}
}

// isConfigsvr 优先看副本集配置。回档重试时进程已经是 standalone，改看 mongo.conf 的 clusterRole。
func (s *pitrRecoverJob) isConfigsvr(inst *common.Instance) (bool, error) {
	conf, err := common.NewRsOp().GetRsConf(inst)
	if err == nil {
		return conf.Config.Configsvr, nil
	}
	s.runtime.Logger.Info("replSetGetConfig failed, fallback to mongo.conf: %s", err.Error())

	port := strconv.Itoa(s.param.Port)
	dataDir := dbmonconsts.GetMongoDataDir(port)
	confFile := filepath.Join(dataDir, "mongodata", port, "mongo.conf")
	yml, loadErr := common.LoadMongoDBConfFromFile(confFile)
	if loadErr != nil {
		return false, errors.Wrap(loadErr, "load mongo.conf")
	}
	if yml.Sharding != nil && yml.Sharding.ClusterRole == "configsvr" {
		return true, nil
	}
	return false, nil
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
					s.runtime.Logger.Error("%s", log.Msg)
				} else {
					s.runtime.Logger.Info("%s", log.Msg)
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
			full, incrList, s.param.recvoerTimeUnix, s.param.Dir, idx, logChan); err != nil {
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

	log.Printf("get version %v err %v", version, err)
	s.MongoRestoreBin, err = pitr.GetMongoRestoreBin(version)
	if err != nil {
		pitr.ExitFailed("get mongoRestoreBin failed, err: %v", err)
		os.Exit(1)
	}

	return nil
}

// checkParams 校验参数
func (s *pitrRecoverJob) checkParams() error {
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.param); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error("%s", tmpErr.Error())
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
