package atommongodb

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"go.mongodb.org/mongo-driver/bson"
)

func TestFilterShardedCollSpecsSkipsSystemAndNsFilter(t *testing.T) {
	specs := []shardedCollSpec{
		{NS: "config.system.sessions", Key: []shardKeyPart{{K: "_id", V: 1}}},
		{NS: "admin.system.users", Key: []shardKeyPart{{K: "_id", V: 1}}},
		{NS: "app.orders", Key: []shardKeyPart{{K: "uid", V: "hashed"}}},
		{NS: "logs.events", Key: []shardKeyPart{{K: "_id", V: 1}}},
		{NS: "app.system.profile", Key: []shardKeyPart{{K: "_id", V: 1}}},
	}
	filtered := filterShardedCollSpecs(specs, NsFilterArg{
		DbList:       []string{"app*"},
		IgnoreDbList: []string{"admin", "config", "local"},
		ColList:      []string{"*"},
	})
	if len(filtered) != 1 || filtered[0].NS != "app.orders" {
		t.Fatalf("filtered=%+v", filtered)
	}
}

func TestParseCollectionsBSONSkipsDropped(t *testing.T) {
	live, err := bson.Marshal(bson.D{
		{Key: "_id", Value: "app.orders"},
		{Key: "key", Value: bson.D{{Key: "uid", Value: "hashed"}, {Key: "ts", Value: int32(1)}}},
		{Key: "unique", Value: false},
		{Key: "dropped", Value: false},
	})
	if err != nil {
		t.Fatal(err)
	}
	dropped, err := bson.Marshal(bson.D{
		{Key: "_id", Value: "app.gone"},
		{Key: "key", Value: bson.D{{Key: "_id", Value: int32(1)}}},
		{Key: "dropped", Value: true},
	})
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "collections.bson")
	if err = os.WriteFile(path, append(live, dropped...), 0644); err != nil {
		t.Fatal(err)
	}
	specs, err := parseCollectionsBSON(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(specs) != 1 {
		t.Fatalf("specs=%+v", specs)
	}
	if specs[0].NS != "app.orders" || len(specs[0].Key) != 2 {
		t.Fatalf("spec=%+v", specs[0])
	}
	if specs[0].Key[0].K != "uid" || specs[0].Key[0].V != "hashed" {
		t.Fatalf("key0=%+v", specs[0].Key[0])
	}
	if specs[0].Key[1].K != "ts" || specs[0].Key[1].V != 1 {
		t.Fatalf("key1=%+v", specs[0].Key[1])
	}
	if jsonNumberToBSON(float64(1)) != int32(1) {
		t.Fatalf("json number=%T", jsonNumberToBSON(float64(1)))
	}
	if jsonNumberToBSON("hashed") != "hashed" {
		t.Fatal("hashed key changed")
	}
}

func TestSpecFromRawReadsDefaultCollation(t *testing.T) {
	raw, _ := bson.Marshal(bson.D{
		{Key: "_id", Value: "db1.c1"},
		{Key: "key", Value: bson.D{{Key: "a", Value: int32(1)}}},
		{Key: "defaultCollation", Value: bson.D{{Key: "locale", Value: "zh"}}},
	})
	spec, ok, err := specFromRaw(raw)
	if err != nil || !ok {
		t.Fatalf("specFromRaw failed ok=%t err=%v", ok, err)
	}
	if !strings.Contains(spec.Collation, `"zh"`) {
		t.Fatalf("expected default collation, got %q", spec.Collation)
	}
	raw, _ = bson.Marshal(bson.D{
		{Key: "_id", Value: "db1.c2"},
		{Key: "key", Value: bson.D{{Key: "a", Value: int32(1)}}},
		{Key: "defaultCollation", Value: bson.D{{Key: "locale", Value: "simple"}}},
	})
	if spec, _, _ = specFromRaw(raw); spec.Collation != "" {
		t.Fatalf("simple collation should be dropped, got %q", spec.Collation)
	}
}

func TestSameShardKey(t *testing.T) {
	a := bson.D{{Key: "a", Value: float64(1)}, {Key: "b", Value: "hashed"}}
	b := bson.D{{Key: "a", Value: int32(1)}, {Key: "b", Value: "hashed"}}
	if !sameShardKey(a, b) {
		t.Fatal("expected same shard key")
	}
	if sameShardKey(a, bson.D{{Key: "b", Value: "hashed"}, {Key: "a", Value: int32(1)}}) {
		t.Fatal("key order matters")
	}
}
