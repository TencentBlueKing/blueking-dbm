package atommongodb

import (
	"sort"
	"testing"
)

func TestShardSetIDLess(t *testing.T) {
	keys := []string{"app-s10", "app-s2", "app-s1", "plain"}
	want := []string{"app-s1", "app-s2", "app-s10", "plain"}
	sort.Slice(keys, func(i, j int) bool {
		return shardSetIDLess(keys[i], keys[j])
	})
	for i := range want {
		if keys[i] != want[i] {
			t.Fatalf("sorted=%v, want %v", keys, want)
		}
	}
}

func TestMakeConfContentOrdersShardsByIndex(t *testing.T) {
	job := &AddShardToCluster{
		ConfParams: &AddConfParams{
			Shards: map[string]string{
				"cluster-s10": "127.0.0.10:27017",
				"cluster-s2":  "127.0.0.2:27017",
				"cluster-s1":  "127.0.0.1:27017",
			},
		},
		runtime: smokeRuntime(t, map[string]any{}, "add_shard_to_cluster"),
	}
	if err := job.makeConfContent(); err != nil {
		t.Fatal(err)
	}
	want := "sh.addShard(\"cluster-s1/127.0.0.1:27017\")\n" +
		"sh.addShard(\"cluster-s2/127.0.0.2:27017\")\n" +
		"sh.addShard(\"cluster-s10/127.0.0.10:27017\")\n"
	if job.ConfFileContent != want {
		t.Fatalf("script=\n%s\nwant=\n%s", job.ConfFileContent, want)
	}
}
