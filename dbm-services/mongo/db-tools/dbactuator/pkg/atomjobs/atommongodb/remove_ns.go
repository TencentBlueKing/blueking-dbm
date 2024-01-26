package atommongodb

import (
	"context"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/toolkit/logical"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// 删除库表.
// 1. 分析参数，确定要删除的库和表
// 2. 如果是删除库，先删除库下的所有表
// 3. 检查oplog
// 4. 执行删除

// 如果在mongos中执行.
//

// removeNsParams 备份任务参数，由前端传入
type removeNsParams struct {
	IP            string `json:"ip"`
	Port          int    `json:"port"`
	AdminUsername string `json:"adminUsername"`
	AdminPassword string `json:"adminPassword"`
	Args          struct {
		DropIndex        bool        `json:"dropIndex"`        // 是否同时删除索引
		RenameCollectoin bool        `json:"renameCollection"` // 是否用renameCollection方式删除
		IsPartial        bool        `json:"isPartial"`        // 为true时，NsFilter生效
		NsFilter         NsFilterArg `json:"nsFilter"`
	} `json:"args"`
}

type removeNsJob struct {
	BaseJob
	BinDir      string
	MongoDump   string
	ConfParams  *removeNsParams
	MongoInst   *mymongo.MongoHost
	MongoClient *mongo.Client
	tmp         struct {
		NsList  []logical.DbCollection
		NsIndex map[string][]*mongo.IndexSpecification
	}
}

func (s *removeNsJob) Param() string {
	var p = removeNsParams{}
	o, _ := json.Marshal(p)
	return string(o)
}

// NewRemoveNsJob 实例化结构体
func NewRemoveNsJob() jobruntime.JobRunner {
	return &removeNsJob{}
}

// Name 获取原子任务的名字
func (s *removeNsJob) Name() string {
	return "mongo_remove_ns"
}

// Run 运行原子任务
func (s *removeNsJob) Run() error {
	// 1 Get Ns List
	// 2 Backup Index If Need
	// 3 Drop Ns
	// 4 Restore Index If Need
	type execFunc struct {
		name string
		f    func() (err error)
	}

	for _, f := range []execFunc{
		{"getNsList", s.getNsList},
		{"dropCollection", s.dropCollection},
		// {"restoreIndex", s.restoreIndex},
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

func connectPrimary(host *mymongo.MongoHost) (client *mongo.Client, err error) {
	// drop Index
	client, err = host.Connect()
	isMasterOut, err := mymongo.IsMaster(client, 10)
	if err != nil {
		err = errors.Wrap(err, "IsMaster")
		return
	}

	if isMasterOut.IsMaster {
		return
	}
	fs := strings.Split(isMasterOut.Primary, ":")
	if len(fs) != 2 {
		err = errors.Errorf("bad primary:%s", isMasterOut.Primary)
		return
	}
	masterInst := mymongo.NewMongoHost(fs[0], fs[1], "admin", host.User, host.Pass, "", fs[0])
	return masterInst.Connect()
}

func (s *removeNsJob) dropCollection() (err error) {
	err = s.backupIndex()
	if err != nil {
		return err
	}
	primaryConn, err := connectPrimary(s.MongoInst)
	if err != nil {
		return errors.Wrap(err, "connectPrimary")
	}
	defer primaryConn.Disconnect(nil)
	for _, ns := range s.tmp.NsList {
		for _, col := range ns.Col {
			err = primaryConn.Database(ns.Db).Collection(col).Drop(context.Background())
			if err != nil {
				return errors.Wrap(err, fmt.Sprintf("drop %s.%s", ns.Db, col))
			}
			s.runtime.Logger.Info("drop %s.%s", ns.Db, col)
		}
	}
	return nil
}

func (s *removeNsJob) backupIndex() (err error) {
	// first Get DbCol List
	if s.ConfParams.Args.DropIndex {
		s.runtime.Logger.Info("skip backup Index")
		return nil
	}

	client, err := s.MongoInst.Connect()
	s.tmp.NsIndex = make(map[string][]*mongo.IndexSpecification)
	for _, ns := range s.tmp.NsList {
		for _, col := range ns.Col {
			indexView := client.Database(ns.Db).Collection(col).Indexes()

			rows, err := indexView.ListSpecifications(context.TODO(), options.ListIndexes().SetMaxTime(30*time.Second))
			if err != nil {
				return errors.Wrap(err, fmt.Sprintf("ListIndexes for %s.%s", ns.Db, col))
			} else {

			}
			s.runtime.Logger.Info(fmt.Sprintf("backup index for %s.%s ", ns.Db, col))
			s.tmp.NsIndex[ns.Db+"."+col] = rows

			indexView2 := client.Database(ns.Db).Collection(col).Indexes()
			ListSpecifications(fmt.Sprintf("%s.%s", ns.Db, col),
				indexView2, context.TODO(), options.ListIndexes().SetMaxTime(30*time.Second))
		}
	}
	s.runtime.Logger.Info(fmt.Sprintf("backup index done"))
	v, _ := json.Marshal(s.tmp.NsIndex)
	s.runtime.Logger.Info(fmt.Sprintf("backupIndex: %s", v))
	return nil
}

func (s *removeNsJob) restoreIndex() (err error) {
	// first Get DbCol List
	if s.ConfParams.Args.DropIndex {
		s.runtime.Logger.Info("skip backup Index")
		return nil
	}

	primaryConn, err := connectPrimary(s.MongoInst)
	if err != nil {
		return errors.Wrap(err, "connectPrimary")
	}
	defer primaryConn.Disconnect(nil)

	for _, ns := range s.tmp.NsList {
		for _, col := range ns.Col {
			v, ok := s.tmp.NsIndex[ns.Db+"."+col]
			if !ok {
				continue
			}

			models := make([]mongo.IndexModel, 0)
			s.runtime.Logger.Info(fmt.Sprintf("restore index for %s.%s ", ns.Db, col))
			for _, spec := range v {
				models = append(models, newIndexModelFromSpec(spec))
			}
			createdIndexes, err := primaryConn.Database(ns.Db).Collection(col).
				Indexes().CreateMany(context.Background(), models)
			if err != nil {
				return errors.Wrap(err, fmt.Sprintf("CreateMany for %s.%s", ns.Db, col))
			} else {
				s.runtime.Logger.Info(fmt.Sprintf("CreateMany for %s.%s, ret:%+v", ns.Db, col, createdIndexes))
			}
		}

	}
	s.runtime.Logger.Info("restoreIndex. not implemented")
	return nil
}

func newIndexModelFromSpec(spec *mongo.IndexSpecification) (model mongo.IndexModel) {
	model = mongo.IndexModel{}
	model.Keys = spec.KeysDocument
	model.Options = &options.IndexOptions{}
	model.Options.Unique = spec.Unique
	model.Options.ExpireAfterSeconds = spec.ExpireAfterSeconds
	model.Options.Sparse = spec.Sparse
	model.Options.Name = &spec.Name
	model.Options.Unique = spec.Unique
	model.Options.Version = &spec.Version
	/*
		 TextVersion *int32 `bson:"textIndexVersion,omitempty"`
		Bits
	*/
	// model.Options.TextVersion = &spec.T

	return
}

/*
	{
		"v" : 2,
		"key" : {
			"_fts" : "text",
			"_ftsx" : 1
		},
		"name" : "MyText",
		"weights" : {
			"Content" : 1,
			"RequestURI" : 1
		},
		"default_language" : "english",
		"language_override" : "language",
		"textIndexVersion" : 3
	}
*/

type unmarshalIndexSpecification struct {
	Name               string   `bson:"name"`
	Namespace          string   `bson:"ns"`
	KeysDocument       bson.Raw `bson:"key"`
	Version            int32    `bson:"v"`
	ExpireAfterSeconds *int32   `bson:"expireAfterSeconds"`
	Sparse             *bool    `bson:"sparse"`
	Unique             *bool    `bson:"unique"`
	Clustered          *bool    `bson:"clustered"`
	Weight             bson.Raw `bson:"weights"`
	DefaultLanguage    string   `bson:"default_language"`
	LanguageOverride   string   `bson:"language_override"`
	TextVersion        *int32   `bson:"textIndexVersion,omitempty"`
}

// UnmarshalBSON implements the bson.Unmarshaler interface.
func unmarshalBSON(data []byte) error {
	var temp unmarshalIndexSpecification
	if err := bson.Unmarshal(data, &temp); err != nil {
		return err
	}
	return nil
}

// ListSpecifications executes a List command and returns a slice of returned IndexSpecifications
// TODO 需要搞清楚所有的索引类型，可能出现的组合。 要加一个test
func ListSpecifications(ns string, iv mongo.IndexView, ctx context.Context, opts ...*options.ListIndexesOptions) error {
	cursor, err := iv.List(ctx, opts...)
	if err != nil {
		return err
	}
	var results []*unmarshalIndexSpecification
	err = cursor.All(ctx, &results)
	fmt.Printf("ListSpecifications err %v \n", err)
	for _, v := range results {
		fmt.Printf("ListSpecifications results:%s %+v\n", ns, v)
	}
	return nil
}

func (s *removeNsJob) getNsList() (err error) {
	// first Get DbCol List
	if s.ConfParams.Args.IsPartial {
		partialArgs := s.ConfParams.Args.NsFilter
		filter := logical.NewNsFilter(
			partialArgs.DbList, partialArgs.IgnoreDbList,
			partialArgs.ColList, partialArgs.IgnoreColList)

		dbColList, err := logical.GetDbCollectionWithFilter(s.MongoInst.Host, s.MongoInst.Port,
			s.MongoInst.User, s.MongoInst.Pass, s.MongoInst.AuthDb, filter)
		if err != nil {
			return errors.Wrap(err, "GetDbCollectionWithFilter")
		}
		// skip sys db
		for _, v := range dbColList {
			if mymongo.IsSysDb(v.Db) {
				continue
			}
			s.tmp.NsList = append(s.tmp.NsList, v)
		}

		if len(s.tmp.NsList) == 0 {
			return errors.Errorf("no matched db and col found")
		}
		s.runtime.Logger.Info(fmt.Sprintf("getNsList:%+v", s.tmp.NsList))

		return nil
	} else {
		s.tmp.NsList, err = logical.GetDbCollection(s.MongoInst.Host, s.MongoInst.Port,
			s.MongoInst.User, s.MongoInst.Pass, s.MongoInst.AuthDb, true)
		if len(s.tmp.NsList) == 0 {
			return errors.Errorf("no db and col found")
		}
		s.runtime.Logger.Info(fmt.Sprintf("logical.GetDbCollection "+
			":%+v", s.tmp.NsList))
		return err
	}
}

// Retry 重试
func (s *removeNsJob) Retry() uint {
	// do nothing
	return 2
}

// Rollback 回滚
func (s *removeNsJob) Rollback() error {
	return nil
}

// Init 初始化
func (s *removeNsJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.OsUser = "" // 不再需要sudo，请以普通用户执行

	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		tmpErr := fmt.Errorf("get parameters of stepDown fail by json.Unmarshal, error:%s", err)
		s.runtime.Logger.Error(tmpErr.Error())
		return tmpErr
	}

	// todo Check Filter Args
	if s.ConfParams.Args.IsPartial {

	}

	s.MongoInst = mymongo.NewMongoHost(
		s.ConfParams.IP, fmt.Sprintf("%d", s.ConfParams.Port),
		"admin", s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "", s.ConfParams.IP)

	// prepare mongo client and mongodump path
	_, err := s.MongoInst.Connect()
	if err != nil {
		return errors.Wrap(err, fmt.Sprintf("Connect to %s:%d failed", s.ConfParams.IP, s.ConfParams.Port))
	}
	s.runtime.Logger.Info(fmt.Sprintf("Connect to %s:%d success", s.ConfParams.IP, s.ConfParams.Port))

	return nil
}

// checkParams 校验参数
func (s *removeNsJob) checkParams() error {
	// 校验配置参数
	validate := validator.New()
	if err := validate.Struct(s.ConfParams); err != nil {
		return fmt.Errorf("validate parameters of deleteUser fail, error:%s", err)
	}

	return nil
}
