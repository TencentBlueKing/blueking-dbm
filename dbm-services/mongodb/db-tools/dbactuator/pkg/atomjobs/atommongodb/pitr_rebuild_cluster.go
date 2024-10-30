package atommongodb

import (
	"context"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"encoding/json"
	"fmt"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// pitrRebuildCluster 用于在pitr回档后，将configsvr和shardsvr的meta数据更新，组合成新的集群
// pitrRebuildCluster 参数
type pitrRebuildClusterParams struct {
	IP            string              `json:"ip"`
	Port          int                 `json:"port"`
	AdminUsername string              `json:"adminUsername"`
	AdminPassword string              `json:"adminPassword"`
	SrcCluster    common.MongoCluster `json:"src_cluster"`
	DstCluster    common.MongoCluster `json:"dst_cluster"`
	SrcShard      common.MongoSet     `json:"src_shard"`
	DstShard      common.MongoSet     `json:"dst_shard"`
}

// PitrRebuildClusterJob 结构体
type PitrRebuildClusterJob struct {
	BaseJob
	ConfParams  *pitrRebuildClusterParams
	MongoInst   *mymongo.MongoHost
	MongoClient *mongo.Client
}

// Param 获取参数
func (s *PitrRebuildClusterJob) Param() string {
	o, _ := json.MarshalIndent(backupParams{}, "", "\t")
	return string(o)
}

// NewPitrRebuildClusterJobJob 实例化结构体
func NewPitrRebuildClusterJobJob() jobruntime.JobRunner {
	return &PitrRebuildClusterJob{}
}

// Name 获取原子任务的名字
func (s *PitrRebuildClusterJob) Name() string {
	return "mongodb_pitr_rebuild"
}

// Run 运行原子任务
func (s *PitrRebuildClusterJob) Run() error {
	if s.ConfParams.DstShard.SetType == "configsvr" {
		return s.updateConfigsvr()
	} else if s.ConfParams.DstShard.SetType == "shardsvr" {
		return s.updateShardsvr()
	}
	return nil
}

// Init 初始化
// return error if failed
func (s *PitrRebuildClusterJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.OsUser = ""
	if checkIsRootUser() {
		s.runtime.Logger.Error("This job cannot be executed as root user")
		return errors.New("This job cannot be executed as root user")
	}
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error(tmpErr.Error())
		return tmpErr
	}
	return nil
}

// GetInstanceOp 封装获取实例操作
func (s *PitrRebuildClusterJob) GetInstanceOp() *common.InstanceOp {
	return common.NewInstanceOp(s.ConfParams.IP,
		s.ConfParams.Port,
		s.ConfParams.AdminUsername,
		s.ConfParams.AdminPassword,
		s.runtime.Logger,
	)
}

// updateConfigsvr 更新配置服务器
// return error if failed
func (s *PitrRebuildClusterJob) updateConfigsvr() error {
	// precheck
	if len(s.ConfParams.SrcCluster.Shards) == 0 {
		return errors.New("src shard count is 0")
	}
	if len(s.ConfParams.SrcCluster.Shards) != len(s.ConfParams.DstCluster.Shards) {
		return errors.New("src shard count not equal dst shard count")
	}

	var op = s.GetInstanceOp()
	err := op.DoStop()
	if err != nil {
		return errors.New("stop config server failed")
	}

	err = op.DoStartAsStandAlone()
	if err != nil {
		return errors.New("StartAsStandAlone failed")
	}
	op.WaitForConnectable(10, 5) // wait for config server start
	err = op.GrantRolesToUser(s.ConfParams.AdminUsername, []string{"__system"})
	if err != nil {
		return errors.Wrap(err, "grant roles to user")
	}

	cli, err := op.ConnectDirect()
	if err != nil {
		return errors.New("connect to config server failed")
	}

	// require __system to drop local db
	_, err = cli.Database("config").Collection("shards").DeleteMany(context.TODO(), bson.D{})
	// drop local db
	err = cli.Database("local").Drop(context.Background())
	if err != nil {
		return errors.Wrap(err, "drop local db")
	}

	opts := options.Update().SetUpsert(true)
	_, err = cli.Database("config").Collection("settings").UpdateOne(
		context.TODO(),
		bson.D{{"_id", "balancer"}},
		bson.D{{"$set", bson.M{"_id": "balancer", "stopped": true, "mode": "full"}}},
		opts,
	)
	if err != nil {
		return errors.Wrap(err, "update config balancer")
	}
	s.runtime.Logger.Info("update config balancer success")
	_, err = cli.Database("config").Collection("shards").DeleteMany(context.TODO(), bson.D{})
	if err != nil {
		return errors.Wrap(err, "delete config.shards")
	}
	s.runtime.Logger.Info("delete config shards success")

	// insert config.shards
	// format like { "_id" : "srcShard.SetName", "host" : "dstShard.Host", "state" : 1 }

	for i := 0; i < len(s.ConfParams.SrcCluster.Shards); i++ {
		srcShard := s.ConfParams.SrcCluster.Shards[i]
		dstShard := s.ConfParams.DstCluster.Shards[i]

		dstHost, err := dstShard.GetConfigShardHost()
		if err != nil {
			return errors.Wrap(err, "get config shard row")
		}
		_, err = cli.Database("config").Collection("shards").InsertOne(
			context.TODO(),
			bson.D{{"_id", srcShard.SetName}, {"host", dstHost}, {"state", 1}},
		)
		if err != nil {
			return errors.Wrap(err, "update config shard")
		}
		s.runtime.Logger.Info("update config shard success")
	}

	err = op.DoStop()
	if err != nil {
		return errors.New("stop failed")
	}
	if err = op.DoStart("auth"); err != nil {
		return errors.Wrap(err, "start")
	}
	err = s.reInitiate(op)
	return err
}

// updateShardsvr updateShardsvr's meta data
// drop local db
// admin.system.version {_id: "shardIdentity"}
// return error if failed
func (s *PitrRebuildClusterJob) updateShardsvr() error {
	s.runtime.Logger.Info("updateShardsvr")
	// precheck
	if len(s.ConfParams.SrcShard.Members) == 0 {
		return errors.New("src shard count is 0")
	}

	s.runtime.Logger.Info("src shardinfo %+v", s.ConfParams.SrcShard)
	s.runtime.Logger.Info("dst shardinfo %+v", s.ConfParams.DstCluster)

	var op = s.GetInstanceOp()
	err := op.DoStop()
	if err != nil {
		return errors.New("stop config server failed")
	}

	err = op.DoStartAsStandAlone()
	if err != nil {
		return errors.New("StartAsStandAlone failed")
	}
	op.WaitForConnectable(10, 5) // wait for server start
	err = op.GrantRolesToUser(s.ConfParams.AdminUsername, []string{"__system"})
	if err != nil {
		return errors.Wrap(err, "grant roles to user")
	}

	cli, err := op.ConnectDirect()
	if err != nil {
		return errors.New("connect to config server failed")
	}

	// drop local db
	err = cli.Database("local").Drop(context.Background())
	if err != nil {
		return errors.Wrap(err, "drop local db")
	}

	rows, err := fetchAll(cli, "admin", "system.version", 100)
	if err != nil {
		return errors.Wrap(err, "fetch all system.version")
	}
	s.runtime.Logger.Info("fetch all system.version success, count: %d", len(rows))
	for _, json := range rows {
		s.runtime.Logger.Info(json)
	}

	// db.system.version.deleteOne( { _id: "minOpTimeRecovery" } )
	_, err = cli.Database("admin").Collection("system.version").DeleteOne(
		context.TODO(),
		bson.D{{"_id", "minOpTimeRecovery"}}, nil)

	if err != nil {
		return errors.Wrap(err, "delete minOpTimeRecovery")
	}

	ret := cli.Database("admin").Collection("system.version").FindOne(context.TODO(),
		bson.D{{"_id", "shardIdentity"}})

	if ret.Err() != nil && !errors.Is(ret.Err(), mongo.ErrNoDocuments) {
		return errors.Wrap(ret.Err(), "find shardIdentity")
	}

	var shardIdentityRow common.ShardIdentity

	if errors.Is(ret.Err(), mongo.ErrNoDocuments) {
		// todo insert
		return errors.Wrap(ret.Err(), "shardIdentitynot found")
	} else {
		err = ret.Decode(&shardIdentityRow)
		if err != nil {
			return errors.Wrap(err, "decode shardIdentity")
		}
		shardIdentityRow.ShardName = s.ConfParams.DstShard.SetName
		configHost, err := s.ConfParams.DstCluster.Configsvr.GetConfigShardHost()
		if err != nil {
			return errors.Wrap(err, "get config host")
		}
		shardIdentityRow.ConfigsvrConnectionString = fmt.Sprintf("%s/%s", s.ConfParams.DstShard.SetName, configHost)
	}

	// update shardName in admin.system.version
	_, err = cli.Database("admin").Collection("system.version").UpdateOne(
		context.TODO(),
		bson.D{{"_id", "shardIdentity"}},
		bson.D{{"$set", bson.D{
			{"shardName", s.ConfParams.SrcShard.SetName},
		}}}, nil)

	if err != nil {
		return errors.Wrap(err, "update shardIdentity")
	}

	err = op.DoStop()
	if err != nil {
		return errors.New("stop failed")
	}
	if err = op.DoStart("auth"); err != nil {
		return errors.Wrap(err, "start")
	}

	err = s.reInitiate(op)
	return err
}

// reInitiate 重新初始化，只有一个节点
// op : instanceOp handle
// return error
func (s *PitrRebuildClusterJob) reInitiate(op *common.InstanceOp) error {
	rsInfo := common.RsConf{
		Id:        s.ConfParams.DstShard.SetName,
		Configsvr: s.ConfParams.DstShard.SetType == "configsvr",
	}
	rsInfo.Hosts = append(rsInfo.Hosts, common.RsConfMember{
		Id:   0,
		Host: fmt.Sprintf("%s:%d", s.ConfParams.IP, s.ConfParams.Port),
	})

	RsOpHandle := common.NewRsOp()
	out, err := RsOpHandle.Initiate(op.Instance, &rsInfo, 120)
	s.runtime.Logger.Info("Initiate in: %+v, out: %+v, err:%v", &rsInfo, out, err)
	if err != nil || out.Ok != 1 {
		s.runtime.Logger.Info("Initiate failed")
		return errors.New("Initiate failed")
	}
	s.runtime.Logger.Info("Initiate success")
	return nil
}

// fetchAll 获取某个ns的所有数据
// cli : mongo client
// db : 数据库
// coll : 集合
// maxRow : 最大行数
func fetchAll(cli *mongo.Client, db, coll string, maxRow int) (rows []string, err error) {
	cursor, err := cli.Database(db).Collection(coll).Find(context.TODO(), bson.D{})
	if err != nil {
		return nil, errors.Wrap(err, "Find")
	}
	defer cursor.Close(context.Background())
	for cursor.Next(context.Background()) {
		var result bson.M
		err := cursor.Decode(&result)
		if err != nil {
			return nil, errors.Wrap(err, "Decode")
		}
		json, err := json.Marshal(result)
		if err != nil {
			return nil, errors.Wrap(err, "fetch all failed")
		}
		rows = append(rows, string(json))
		if len(rows) >= maxRow {
			break
		}
	}
	return rows, nil
}
