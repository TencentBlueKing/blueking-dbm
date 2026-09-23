package atommongodb

import (
	"io"
	"testing"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
)

// srcShardsAfterScaleOut 源集群扩容后常见的CMDB主键序
func srcShardsAfterScaleOut() []common.MongoSet {
	return []common.MongoSet{
		{SetName: "cluster-s20"},
		{SetName: "cluster-s50"},
		{SetName: "cluster-s24"},
		{SetName: "cluster-s3"},
	}
}

// dstShardsFreshDeploy 临时集群一次部署的连续编号
func dstShardsFreshDeploy() []common.MongoSet {
	return []common.MongoSet{
		{SetName: "cluster-tmp-s1"},
		{SetName: "cluster-tmp-s2"},
		{SetName: "cluster-tmp-s3"},
		{SetName: "cluster-tmp-s4"},
	}
}

func newRebuildJob(t *testing.T, params *pitrRebuildClusterParams) *PitrRebuildClusterJob {
	t.Helper()
	return &PitrRebuildClusterJob{
		BaseJob: BaseJob{
			runtime: &jobruntime.JobGenericRuntime{
				Logger: logger.New(io.Discard, false, logger.InfoLevel),
			},
		},
		ConfParams: params,
	}
}

func assertPairs(t *testing.T, pairs []shardPair, want [][2]string) {
	t.Helper()
	if len(pairs) != len(want) {
		t.Fatalf("got %d pairs, want %d", len(pairs), len(want))
	}
	for i, p := range pairs {
		if p.srcSetName != want[i][0] || p.dst.SetName != want[i][1] {
			t.Errorf("pair[%d]=%s->%s want %s->%s", i, p.srcSetName, p.dst.SetName, want[i][0], want[i][1])
		}
	}
}

func TestShardSetNameNumericSuffix(t *testing.T) {
	cases := []struct {
		name string
		want string
	}{
		{"cluster-s1", "1"},
		{"cluster-s20", "20"},
		{"cluster-s50", "50"},
		{"s3", "3"},
		// 现网存在的不带编号名字，与Python __get_shard_idx 的默认值0一致
		{"noshard", "0"},
		{"cluster-shard-a", "0"},
		{"", "0"},
		// 前导0归一化，s007 与 s7 编号相同
		{"cluster-s007", "7"},
		{"cluster-s0", "0"},
	}
	for _, tc := range cases {
		if got := shardSetNameNumericSuffix(tc.name); got != tc.want {
			t.Errorf("shardSetNameNumericSuffix(%q)=%q want %q", tc.name, got, tc.want)
		}
	}
}

// 排序键必须与 Python sorted(key=(__get_shard_idx(set_name), set_name)) 完全一致
func TestSortMongoSetsBySetName(t *testing.T) {
	cases := []struct {
		name string
		in   []string
		want []string
	}{
		{
			name: "numeric suffix sorts by value not lexicographically",
			in:   []string{"c-s20", "c-s50", "c-s24", "c-s3"},
			want: []string{"c-s3", "c-s20", "c-s24", "c-s50"},
		},
		{
			name: "unnumbered names all rank 0 and fall back to name order",
			in:   []string{"c-shard-c", "c-shard-a", "c-shard-b"},
			want: []string{"c-shard-a", "c-shard-b", "c-shard-c"},
		},
		{
			name: "mixed numbered and unnumbered",
			in:   []string{"c-s2", "c-backup", "c-s1", "c-archive"},
			want: []string{"c-archive", "c-backup", "c-s1", "c-s2"},
		},
		{
			name: "huge numeric suffix does not overflow",
			in:   []string{"c-s99999999999999999999", "c-s2", "c-s1"},
			want: []string{"c-s1", "c-s2", "c-s99999999999999999999"},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			sets := make([]common.MongoSet, 0, len(tc.in))
			for _, n := range tc.in {
				sets = append(sets, common.MongoSet{SetName: n})
			}
			got := sortMongoSetsBySetName(sets)
			for i := range got {
				if got[i].SetName != tc.want[i] {
					t.Errorf("sorted[%d]=%s want %s (got %v)", i, got[i].SetName, tc.want[i], got)
					break
				}
			}
			// 不能就地修改入参
			if sets[0].SetName != tc.in[0] {
				t.Errorf("input mutated: %s", sets[0].SetName)
			}
		})
	}
}

// 不带编号的shard也要能走shard_map，配对纯粹按名字，不受排序影响
func TestResolveShardPairsWithUnnumberedShardNames(t *testing.T) {
	src := []common.MongoSet{
		{SetName: "src-shard-b"},
		{SetName: "src-shard-a"},
	}
	dst := []common.MongoSet{
		{SetName: "tmp-s1"},
		{SetName: "tmp-s2"},
	}
	job := newRebuildJob(t, &pitrRebuildClusterParams{
		SrcCluster: common.MongoCluster{Shards: src},
		DstCluster: common.MongoCluster{Shards: dst},
		ShardMap: []pitrShardMapEntry{
			{SrcSetName: "src-shard-a", DstSetName: "tmp-s1"},
			{SrcSetName: "src-shard-b", DstSetName: "tmp-s2"},
		},
	})

	pairs, err := job.resolveShardPairs()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	assertPairs(t, pairs, [][2]string{
		{"src-shard-a", "tmp-s1"},
		{"src-shard-b", "tmp-s2"},
	})
}

// 老payload没有shard_map且shard名不带编号时，回退排序必须与flow一致（按名字）
func TestResolveShardPairsFallbackWithUnnumberedShardNames(t *testing.T) {
	job := newRebuildJob(t, &pitrRebuildClusterParams{
		SrcCluster: common.MongoCluster{Shards: []common.MongoSet{
			{SetName: "src-shard-b"},
			{SetName: "src-shard-a"},
		}},
		DstCluster: common.MongoCluster{Shards: []common.MongoSet{
			{SetName: "tmp-s2"},
			{SetName: "tmp-s1"},
		}},
	})

	pairs, err := job.resolveShardPairs()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	assertPairs(t, pairs, [][2]string{
		{"src-shard-a", "tmp-s1"},
		{"src-shard-b", "tmp-s2"},
	})
}

// flow下发shard_map时，配对完全按名字走，与两边数组顺序无关
func TestResolveShardPairsUsesShardMap(t *testing.T) {
	job := newRebuildJob(t, &pitrRebuildClusterParams{
		SrcCluster: common.MongoCluster{Shards: srcShardsAfterScaleOut()},
		DstCluster: common.MongoCluster{Shards: dstShardsFreshDeploy()},
		ShardMap: []pitrShardMapEntry{
			{SrcSetName: "cluster-s3", DstSetName: "cluster-tmp-s1"},
			{SrcSetName: "cluster-s20", DstSetName: "cluster-tmp-s2"},
			{SrcSetName: "cluster-s24", DstSetName: "cluster-tmp-s3"},
			{SrcSetName: "cluster-s50", DstSetName: "cluster-tmp-s4"},
		},
	})

	pairs, err := job.resolveShardPairs()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	assertPairs(t, pairs, [][2]string{
		{"cluster-s3", "cluster-tmp-s1"},
		{"cluster-s20", "cluster-tmp-s2"},
		{"cluster-s24", "cluster-tmp-s3"},
		{"cluster-s50", "cluster-tmp-s4"},
	})
}

// 老payload没有shard_map时回退到set_name排序，结果应与flow的排序配对一致
func TestResolveShardPairsFallbackToSetNameOrder(t *testing.T) {
	job := newRebuildJob(t, &pitrRebuildClusterParams{
		SrcCluster: common.MongoCluster{Shards: srcShardsAfterScaleOut()},
		DstCluster: common.MongoCluster{Shards: dstShardsFreshDeploy()},
	})

	pairs, err := job.resolveShardPairs()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	assertPairs(t, pairs, [][2]string{
		{"cluster-s3", "cluster-tmp-s1"},
		{"cluster-s20", "cluster-tmp-s2"},
		{"cluster-s24", "cluster-tmp-s3"},
		{"cluster-s50", "cluster-tmp-s4"},
	})

	// 下标zip会把CMDB第一个源名s20绑到临时s1，排序后应是编号最小的s3
	if pairs[0].srcSetName == srcShardsAfterScaleOut()[0].SetName {
		t.Fatal("fallback pairing should not keep CMDB insertion order")
	}
}

func TestResolveShardPairsRejectsBadShardMap(t *testing.T) {
	cases := []struct {
		name     string
		shardMap []pitrShardMapEntry
	}{
		{
			name: "size mismatch",
			shardMap: []pitrShardMapEntry{
				{SrcSetName: "cluster-s3", DstSetName: "cluster-tmp-s1"},
			},
		},
		{
			name: "unknown dst set_name",
			shardMap: []pitrShardMapEntry{
				{SrcSetName: "cluster-s3", DstSetName: "cluster-tmp-s1"},
				{SrcSetName: "cluster-s20", DstSetName: "cluster-tmp-s2"},
				{SrcSetName: "cluster-s24", DstSetName: "cluster-tmp-s3"},
				{SrcSetName: "cluster-s50", DstSetName: "cluster-tmp-s9"},
			},
		},
		{
			name: "duplicated dst set_name",
			shardMap: []pitrShardMapEntry{
				{SrcSetName: "cluster-s3", DstSetName: "cluster-tmp-s1"},
				{SrcSetName: "cluster-s20", DstSetName: "cluster-tmp-s1"},
				{SrcSetName: "cluster-s24", DstSetName: "cluster-tmp-s3"},
				{SrcSetName: "cluster-s50", DstSetName: "cluster-tmp-s4"},
			},
		},
		{
			name: "duplicated src set_name",
			shardMap: []pitrShardMapEntry{
				{SrcSetName: "cluster-s3", DstSetName: "cluster-tmp-s1"},
				{SrcSetName: "cluster-s3", DstSetName: "cluster-tmp-s2"},
				{SrcSetName: "cluster-s24", DstSetName: "cluster-tmp-s3"},
				{SrcSetName: "cluster-s50", DstSetName: "cluster-tmp-s4"},
			},
		},
		{
			name: "empty set_name",
			shardMap: []pitrShardMapEntry{
				{SrcSetName: "cluster-s3", DstSetName: "cluster-tmp-s1"},
				{SrcSetName: "", DstSetName: "cluster-tmp-s2"},
				{SrcSetName: "cluster-s24", DstSetName: "cluster-tmp-s3"},
				{SrcSetName: "cluster-s50", DstSetName: "cluster-tmp-s4"},
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			job := newRebuildJob(t, &pitrRebuildClusterParams{
				SrcCluster: common.MongoCluster{Shards: srcShardsAfterScaleOut()},
				DstCluster: common.MongoCluster{Shards: dstShardsFreshDeploy()},
				ShardMap:   tc.shardMap,
			})
			if _, err := job.resolveShardPairs(); err == nil {
				t.Fatal("expected error")
			}
		})
	}
}

func TestPairShardsBySetNameCountMismatch(t *testing.T) {
	_, err := pairShardsBySetName(
		[]common.MongoSet{{SetName: "s1"}},
		[]common.MongoSet{{SetName: "s1"}, {SetName: "s2"}},
	)
	if err == nil {
		t.Fatal("expected count mismatch error")
	}
}
