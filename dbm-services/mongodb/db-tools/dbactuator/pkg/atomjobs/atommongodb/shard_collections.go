package atommongodb

import (
	"compress/gzip"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/toolkit/logical"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

const (
	shardCollOpExport = "export"
	shardCollOpApply  = "apply"
)

// shardCollectionsParam 从源集群或 configsvr 逻辑备份解析分片表，再在目标 mongos 上 shardCollection。
// 不恢复 configsvr。
type shardCollectionsParam struct {
	IP            string `json:"ip"`
	Port          int    `json:"port"`
	AdminUsername string `json:"adminUsername"`
	AdminPassword string `json:"adminPassword"`
	Op            string `json:"op"`
	// CollectionsFile 是分片表清单。export 写这个文件，apply 读这个文件。
	CollectionsFile string `json:"collectionsFile"`
	// BackupFile 是 configsvr 的逻辑备份包。apply 时若设置，则从包里的 config.collections 解析，不读取 CollectionsFile。
	BackupFile string `json:"backupFile"`
	// NsFilter 按库表白/黑名单过滤；空则只跳过系统命名空间。
	NsFilter NsFilterArg `json:"nsFilter"`
}

type shardKeyPart struct {
	K string      `json:"k"`
	V interface{} `json:"v"`
}

type shardedCollSpec struct {
	NS        string         `json:"ns"`
	Unique    bool           `json:"unique"`
	Key       []shardKeyPart `json:"key"`
	Collation string         `json:"collation,omitempty"`
}

type shardCollectionsJob struct {
	BaseJob
	param       *shardCollectionsParam
	mongoInst   *mymongo.MongoHost
	mongoClient *mongo.Client
}

// NewShardCollectionsJob 实例化
func NewShardCollectionsJob() jobruntime.JobRunner {
	return &shardCollectionsJob{}
}

func (s *shardCollectionsJob) Name() string {
	return "mongodb_shard_collections"
}

func (s *shardCollectionsJob) Param() string {
	raw, _ := json.MarshalIndent(shardCollectionsParam{}, "", "\t")
	return string(raw)
}

func (s *shardCollectionsJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	s.runtime = runtime
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.param); err != nil {
		return errors.Wrap(err, "payload json.Unmarshal failed")
	}
	if s.param.Op != shardCollOpExport && s.param.Op != shardCollOpApply {
		return errors.Errorf("op must be export or apply, got %s", s.param.Op)
	}
	if s.param.CollectionsFile == "" && s.param.BackupFile == "" {
		return errors.New("collectionsFile or backupFile is required")
	}
	s.mongoInst = mymongo.NewMongoHost(
		s.param.IP, fmt.Sprintf("%d", s.param.Port),
		"admin", s.param.AdminUsername, s.param.AdminPassword, "", s.param.IP)
	client, err := s.mongoInst.Connect()
	if err != nil {
		return errors.Wrap(err, "Connect")
	}
	s.mongoClient = client
	return nil
}

func (s *shardCollectionsJob) Run() error {
	switch s.param.Op {
	case shardCollOpExport:
		specs, err := listShardedCollections(s.mongoClient)
		if err != nil {
			return err
		}
		specs = filterShardedCollSpecs(specs, s.param.NsFilter)
		return writeShardedCollSpecs(s.param.CollectionsFile, specs)
	case shardCollOpApply:
		specs, err := s.loadSpecs()
		if err != nil {
			return err
		}
		specs = filterShardedCollSpecs(specs, s.param.NsFilter)
		return applyShardCollections(s.mongoClient, specs, s.runtime.Logger)
	default:
		return errors.Errorf("unknown op %s", s.param.Op)
	}
}

func (s *shardCollectionsJob) loadSpecs() ([]shardedCollSpec, error) {
	if s.param.BackupFile != "" {
		specs, err := specsFromConfigBackup(s.param.BackupFile)
		if err != nil {
			return nil, err
		}
		if s.param.CollectionsFile != "" {
			if err = writeShardedCollSpecs(s.param.CollectionsFile, specs); err != nil {
				return nil, err
			}
		}
		return specs, nil
	}
	return readShardedCollSpecs(s.param.CollectionsFile)
}

func listShardedCollections(client *mongo.Client) ([]shardedCollSpec, error) {
	ctx := context.Background()
	cursor, err := client.Database("config").Collection("collections").Find(ctx, bson.D{})
	if err != nil {
		return nil, errors.Wrap(err, "find config.collections")
	}
	defer cursor.Close(ctx)
	var specs []shardedCollSpec
	for cursor.Next(ctx) {
		var raw bson.Raw
		if err = cursor.Decode(&raw); err != nil {
			return nil, errors.Wrap(err, "decode config.collections")
		}
		spec, ok, err := specFromRaw(raw)
		if err != nil {
			return nil, err
		}
		if ok {
			specs = append(specs, spec)
		}
	}
	if err = cursor.Err(); err != nil {
		return nil, errors.Wrap(err, "cursor config.collections")
	}
	return specs, nil
}

func specsFromConfigBackup(backupFile string) ([]shardedCollSpec, error) {
	dstDir, err := logical.UntarFile(backupFile)
	if err != nil {
		return nil, errors.Wrap(err, "untar config backup")
	}
	defer os.RemoveAll(dstDir)
	bsonPath, err := findCollectionsBSON(configDumpDir(dstDir))
	if err != nil {
		return nil, err
	}
	return parseCollectionsBSON(bsonPath)
}

func configDumpDir(extracted string) string {
	withDump := filepath.Join(extracted, "dump", "config")
	if _, err := os.Stat(withDump); err == nil {
		return withDump
	}
	return filepath.Join(extracted, "config")
}

func findCollectionsBSON(dir string) (string, error) {
	for _, name := range []string{"collections.bson", "collections.bson.gz"} {
		path := filepath.Join(dir, name)
		if _, err := os.Stat(path); err == nil {
			return path, nil
		}
	}
	return "", errors.Errorf("config/collections.bson not found under %s", dir)
}

func parseCollectionsBSON(path string) ([]shardedCollSpec, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, errors.Wrap(err, "open collections.bson")
	}
	defer file.Close()
	var reader io.Reader = file
	if strings.HasSuffix(path, ".gz") {
		gz, err := gzip.NewReader(file)
		if err != nil {
			return nil, errors.Wrap(err, "gzip collections.bson")
		}
		defer gz.Close()
		reader = gz
	}
	data, err := io.ReadAll(reader)
	if err != nil {
		return nil, errors.Wrap(err, "read collections.bson")
	}
	var specs []shardedCollSpec
	for len(data) > 0 {
		raw := bson.Raw(data)
		if err = raw.Validate(); err != nil {
			return nil, errors.Wrap(err, "invalid bson in collections.bson")
		}
		size := int(raw[0]) | int(raw[1])<<8 | int(raw[2])<<16 | int(raw[3])<<24
		if size <= 0 || size > len(data) {
			return nil, errors.Errorf("bad bson document size %d", size)
		}
		spec, ok, err := specFromRaw(raw[:size])
		if err != nil {
			return nil, err
		}
		if ok {
			specs = append(specs, spec)
		}
		data = data[size:]
	}
	return specs, nil
}

func isSystemShardedNS(ns string) bool {
	dbName, coll, ok := strings.Cut(ns, ".")
	if !ok {
		return true
	}
	if mymongo.IsSysDb(dbName) {
		return true
	}
	if strings.HasPrefix(coll, "system.") {
		return true
	}
	return false
}

func filterShardedCollSpecs(specs []shardedCollSpec, nsFilter NsFilterArg) []shardedCollSpec {
	filter := logical.NewNsFilter(nsFilter.DbList, nsFilter.IgnoreDbList, nsFilter.ColList, nsFilter.IgnoreColList)
	out := make([]shardedCollSpec, 0, len(specs))
	for _, spec := range specs {
		if isSystemShardedNS(spec.NS) {
			continue
		}
		dbName, coll, ok := strings.Cut(spec.NS, ".")
		if !ok {
			continue
		}
		if !filter.IsDbMatched(dbName) {
			continue
		}
		matched, _ := filter.FilterTbV2(dbName, []string{coll})
		if len(matched) == 0 {
			continue
		}
		out = append(out, spec)
	}
	return out
}

func specFromRaw(raw bson.Raw) (shardedCollSpec, bool, error) {
	var doc struct {
		ID        string   `bson:"_id"`
		Key       bson.D   `bson:"key"`
		Unique    bool     `bson:"unique"`
		Dropped   bool     `bson:"dropped"`
		Collation bson.Raw `bson:"collation"`
	}
	if err := bson.Unmarshal(raw, &doc); err != nil {
		return shardedCollSpec{}, false, errors.Wrap(err, "unmarshal config.collections")
	}
	if doc.Dropped || !strings.Contains(doc.ID, ".") || len(doc.Key) == 0 {
		return shardedCollSpec{}, false, nil
	}
	if isSystemShardedNS(doc.ID) {
		return shardedCollSpec{}, false, nil
	}
	spec := shardedCollSpec{NS: doc.ID, Unique: doc.Unique}
	for _, elem := range doc.Key {
		spec.Key = append(spec.Key, shardKeyPart{K: elem.Key, V: normalizeKeyValue(elem.Value)})
	}
	if len(doc.Collation) > 0 {
		ext, err := bson.MarshalExtJSON(doc.Collation, false, false)
		if err != nil {
			return shardedCollSpec{}, false, errors.Wrap(err, "marshal collation")
		}
		spec.Collation = string(ext)
	}
	return spec, true, nil
}

func normalizeKeyValue(v interface{}) interface{} {
	switch n := v.(type) {
	case int32:
		return int(n)
	case int64:
		return int(n)
	case float64:
		return int(n)
	default:
		return v
	}
}

func writeShardedCollSpecs(path string, specs []shardedCollSpec) error {
	if specs == nil {
		specs = []shardedCollSpec{}
	}
	raw, err := json.MarshalIndent(specs, "", "  ")
	if err != nil {
		return errors.Wrap(err, "marshal sharded collections")
	}
	if err = os.MkdirAll(filepath.Dir(path), 0750); err != nil {
		return errors.Wrap(err, "mkdir collections file dir")
	}
	return os.WriteFile(path, raw, 0644)
}

func readShardedCollSpecs(path string) ([]shardedCollSpec, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, errors.Wrap(err, "read sharded collections")
	}
	var specs []shardedCollSpec
	if err = json.Unmarshal(raw, &specs); err != nil {
		return nil, errors.Wrap(err, "unmarshal sharded collections")
	}
	return specs, nil
}

type shardCollLogger interface {
	Info(format string, args ...interface{})
}

func applyShardCollections(client *mongo.Client, specs []shardedCollSpec, log shardCollLogger) error {
	enabled := map[string]bool{}
	for _, spec := range specs {
		dbName := spec.NS[:strings.Index(spec.NS, ".")]
		if !enabled[dbName] {
			if err := enableSharding(client, dbName); err != nil {
				return errors.Wrapf(err, "enableSharding %s", dbName)
			}
			enabled[dbName] = true
			log.Info("enableSharding %s", dbName)
		}
		if err := shardCollection(client, spec); err != nil {
			return errors.Wrapf(err, "shardCollection %s", spec.NS)
		}
		log.Info("shardCollection %s key=%v", spec.NS, spec.Key)
	}
	log.Info("shardCollection done, count=%d", len(specs))
	return nil
}

func enableSharding(client *mongo.Client, dbName string) error {
	var out bson.M
	err := mymongo.RunAdminCommandD(client, bson.D{{Key: "enableSharding", Value: dbName}}, 120, &out)
	if err == nil {
		return nil
	}
	msg := err.Error()
	if strings.Contains(msg, "already enabled") {
		return nil
	}
	return err
}

func shardCollection(client *mongo.Client, spec shardedCollSpec) error {
	key := bson.D{}
	for _, part := range spec.Key {
		key = append(key, bson.E{Key: part.K, Value: jsonNumberToBSON(part.V)})
	}
	cmd := bson.D{
		{Key: "shardCollection", Value: spec.NS},
		{Key: "key", Value: key},
		{Key: "unique", Value: spec.Unique},
	}
	if spec.Collation != "" {
		var collation bson.Raw
		if err := bson.UnmarshalExtJSON([]byte(spec.Collation), false, &collation); err != nil {
			return errors.Wrap(err, "unmarshal collation")
		}
		cmd = append(cmd, bson.E{Key: "collation", Value: collation})
	}
	var out bson.M
	return mymongo.RunAdminCommandD(client, cmd, 600, &out)
}

func jsonNumberToBSON(v interface{}) interface{} {
	switch n := v.(type) {
	case float64:
		if n == float64(int32(n)) {
			return int32(n)
		}
		return n
	case int:
		return int32(n)
	default:
		return v
	}
}
