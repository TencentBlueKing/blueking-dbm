package atommongodb

import (
	"context"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"encoding/json"
	"fmt"
	"sort"
	"strings"

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
	GracefulStop  *bool               `json:"gracefulStop,omitempty"`
	SrcCluster    common.MongoCluster `json:"src_cluster"`
	DstCluster    common.MongoCluster `json:"dst_cluster"`
	SrcShard      common.MongoSet     `json:"src_shard"`
	DstShard      common.MongoSet     `json:"dst_shard"`
	ShardMap      []pitrShardMapEntry `json:"shard_map"`
}

// pitrShardMapEntry flow下发的 源shard -> 目标shard 显式配对。
// 与灌备份、shardIdentity 用的是同一份配对，按set_name关联，不依赖数组下标。
type pitrShardMapEntry struct {
	SrcSetName string `json:"src_set_name"`
	DstSetName string `json:"dst_set_name"`
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
		s.runtime.Logger.Error("%s", tmpErr.Error())
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

// isGracefulStop 是否优雅停止. pitrRebuild中将节点反复以单机模式启停以重写元数据，默认不需要gracefulStop。
func (s *PitrRebuildClusterJob) isGracefulStop() bool {
	if s.ConfParams.GracefulStop == nil {
		return false
	}
	return *s.ConfParams.GracefulStop
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
	err := op.DoStopWithOptions(common.StopOptions{Graceful: s.isGracefulStop()})
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
		bson.D{{Key: "_id", Value: "balancer"}},
		bson.D{{Key: "$set", Value: bson.M{"_id": "balancer", "stopped": true, "mode": "full"}}},
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
	pairs, err := s.resolveShardPairs()
	if err != nil {
		return err
	}

	for _, pair := range pairs {
		dstHost, err := pair.dst.GetConfigShardHost()
		if err != nil {
			return errors.Wrap(err, "get config shard row")
		}
		_, err = cli.Database("config").Collection("shards").InsertOne(
			context.TODO(),
			bson.D{
				{Key: "_id", Value: pair.srcSetName},
				{Key: "host", Value: dstHost},
				{Key: "state", Value: 1},
			},
		)
		if err != nil {
			return errors.Wrap(err, "update config shard")
		}
		s.runtime.Logger.Info("update config.shards %s -> %s", pair.srcSetName, dstHost)
	}

	err = op.DoStopWithOptions(common.StopOptions{Graceful: s.isGracefulStop()})
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
	err := op.DoStopWithOptions(common.StopOptions{Graceful: s.isGracefulStop()})
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

	if err = s.dropRoutingCache(cli); err != nil {
		return err
	}

	rows, err := fetchAll(cli, "admin", "system.version", 100)
	if err != nil {
		return errors.Wrap(err, "fetch all system.version")
	}
	s.runtime.Logger.Info("fetch all system.version success, count: %d", len(rows))
	for _, json := range rows {
		s.runtime.Logger.Info("%s", json)
	}

	// db.system.version.deleteOne( { _id: "minOpTimeRecovery" } )
	_, err = cli.Database("admin").Collection("system.version").DeleteOne(
		context.TODO(),
		bson.D{{Key: "_id", Value: "minOpTimeRecovery"}}, nil)

	if err != nil {
		return errors.Wrap(err, "delete minOpTimeRecovery")
	}

	ret := cli.Database("admin").Collection("system.version").FindOne(context.TODO(),
		bson.D{{Key: "_id", Value: "shardIdentity"}})

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
		bson.D{{Key: "_id", Value: "shardIdentity"}},
		bson.D{{Key: "$set", Value: bson.D{
			{Key: "shardName", Value: s.ConfParams.SrcShard.SetName},
		}}}, nil)

	if err != nil {
		return errors.Wrap(err, "update shardIdentity")
	}

	err = op.DoStopWithOptions(common.StopOptions{Graceful: s.isGracefulStop()})
	if err != nil {
		return errors.New("stop failed")
	}
	if err = op.DoStart("auth"); err != nil {
		return errors.Wrap(err, "start")
	}

	err = s.reInitiate(op)
	return err
}

// dropRoutingCache 删除shardsvr本地持久化的路由缓存 config.cache.*
// 回档会把源集群的 config.cache.* 一并导入，其中的 collection version 可能高于目标configsvr。
// 同一epoch下shard的路由缓存只能单调前进，残留的高版本会让mongos的setShardVersion被拒绝并无限重试。
// 只能在standalone下执行：以shardsvr角色运行时这些表由CatalogCacheLoader持有，drop后会被重新写回。
// cli : 以standalone方式直连的mongo client
// return error if failed
func (s *PitrRebuildClusterJob) dropRoutingCache(cli *mongo.Client) error {
	configDb := cli.Database("config")
	names, err := configDb.ListCollectionNames(context.TODO(), bson.D{})
	if err != nil {
		return errors.Wrap(err, "list config collections")
	}
	for _, name := range names {
		// cache.collections, cache.databases, cache.chunks.<ns|uuid>
		if !strings.HasPrefix(name, "cache.") {
			continue
		}
		if err = configDb.Collection(name).Drop(context.TODO()); err != nil {
			return errors.Wrap(err, "drop config."+name)
		}
		s.runtime.Logger.Info("drop config.%s success", name)
	}
	return nil
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

// shardPair 一条 config.shards 记录：以源shard名为_id，指向目标shard的host
type shardPair struct {
	srcSetName string
	dst        common.MongoSet
}

// resolveShardPairs 确定写入config.shards的配对。
// 优先使用flow下发的shard_map，它与灌备份、shardIdentity 是同一份配对；
// 老版本flow的payload没有这个字段，回退到按set_name数字后缀排序（与flow的排序规则一致）。
func (s *PitrRebuildClusterJob) resolveShardPairs() ([]shardPair, error) {
	srcShards, dstShards := s.ConfParams.SrcCluster.Shards, s.ConfParams.DstCluster.Shards

	if len(s.ConfParams.ShardMap) == 0 {
		s.runtime.Logger.Info("shard_map absent in payload, fallback to set_name order pairing")
		return pairShardsBySetName(srcShards, dstShards)
	}

	if len(s.ConfParams.ShardMap) != len(srcShards) {
		return nil, errors.Errorf("shard_map size %d not equal src shard count %d",
			len(s.ConfParams.ShardMap), len(srcShards))
	}

	dstBySetName := make(map[string]common.MongoSet, len(dstShards))
	for _, one := range dstShards {
		dstBySetName[one.SetName] = one
	}

	pairs := make([]shardPair, 0, len(s.ConfParams.ShardMap))
	seenSrc := make(map[string]struct{}, len(s.ConfParams.ShardMap))
	seenDst := make(map[string]struct{}, len(s.ConfParams.ShardMap))
	for _, entry := range s.ConfParams.ShardMap {
		if entry.SrcSetName == "" || entry.DstSetName == "" {
			return nil, errors.Errorf("bad shard_map entry %+v", entry)
		}
		if _, dup := seenSrc[entry.SrcSetName]; dup {
			return nil, errors.Errorf("duplicated src set_name %s in shard_map", entry.SrcSetName)
		}
		if _, dup := seenDst[entry.DstSetName]; dup {
			return nil, errors.Errorf("duplicated dst set_name %s in shard_map", entry.DstSetName)
		}
		dstShard, ok := dstBySetName[entry.DstSetName]
		if !ok {
			return nil, errors.Errorf("dst set_name %s in shard_map not found in dst_cluster", entry.DstSetName)
		}
		seenSrc[entry.SrcSetName] = struct{}{}
		seenDst[entry.DstSetName] = struct{}{}
		pairs = append(pairs, shardPair{srcSetName: entry.SrcSetName, dst: dstShard})
	}

	return pairs, nil
}

// shardSetNameNumericSuffix 取 set_name 末尾连续数字并去掉前导0。
// 现网存在不带编号的set_name，此时返回"0"，与 Python __get_shard_idx 的默认值一致。
func shardSetNameNumericSuffix(setName string) string {
	end := len(setName)
	start := end
	for start > 0 {
		c := setName[start-1]
		if c < '0' || c > '9' {
			break
		}
		start--
	}

	digits := strings.TrimLeft(setName[start:end], "0")
	if digits == "" {
		return "0"
	}
	return digits
}

// compareShardSetName 复刻 Python get_shards(sort_by_set_name=True) 的排序键 (编号, set_name)。
// 编号按数值比较，但用「位数+字典序」而不是转int，避免超长数字后缀溢出。
// 编号相同（含两个都不带编号）时按名字比较，保证与Python一样不依赖CMDB行序。
func compareShardSetName(left, right string) int {
	lDigits, rDigits := shardSetNameNumericSuffix(left), shardSetNameNumericSuffix(right)
	if len(lDigits) != len(rDigits) {
		if len(lDigits) < len(rDigits) {
			return -1
		}
		return 1
	}
	if lDigits != rDigits {
		return strings.Compare(lDigits, rDigits)
	}
	return strings.Compare(left, right)
}

func sortMongoSetsBySetName(sets []common.MongoSet) []common.MongoSet {
	out := make([]common.MongoSet, len(sets))
	copy(out, sets)
	sort.SliceStable(out, func(i, j int) bool {
		return compareShardSetName(out[i].SetName, out[j].SetName) < 0
	})
	return out
}

// pairShardsBySetName 按 set_name 数字后缀排序后按下标配对源/目标 shard。
// 仅用于兼容没有下发shard_map的老payload。直接用CMDB列表下标配对会在源集群扩容后错位
// （源 s20,s50,s24,s3 vs 临时 s1,s2,s3,s4）。
func pairShardsBySetName(src, dst []common.MongoSet) ([]shardPair, error) {
	if len(src) != len(dst) {
		return nil, errors.Errorf("src shard count %d not equal dst shard count %d", len(src), len(dst))
	}
	srcSorted := sortMongoSetsBySetName(src)
	dstSorted := sortMongoSetsBySetName(dst)
	pairs := make([]shardPair, len(srcSorted))
	for i := range srcSorted {
		pairs[i] = shardPair{srcSetName: srcSorted[i].SetName, dst: dstSorted[i]}
	}
	return pairs, nil
}
