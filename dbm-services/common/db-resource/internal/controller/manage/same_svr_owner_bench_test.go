/*
 * Benchmark for same-mother-machine count algorithm (~50k Unused resources).
 *
 * Run:
 *   go test ./internal/controller/manage/ -bench=BenchmarkSameSvrOwner -benchmem -count=1
 */
package manage

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"sort"
	"testing"

	"dbm-services/common/db-resource/internal/model"
)

func buildBenchPool(n int, avgPerMother int, seed int64) []model.TbRpDetail {
	rng := rand.New(rand.NewSource(seed))
	rsTypes := []string{model.RESOURCE_TYPE_PUBLIC, "mysql", "redis", "mongodb", "es"}
	bizs := []int{0, 1001, 1002, 1003, 2001}
	pool := make([]model.TbRpDetail, 0, n)
	mothers := n / avgPerMother
	if mothers < 1 {
		mothers = 1
	}
	for i := 0; i < n; i++ {
		mother := i % mothers
		biz := bizs[rng.Intn(len(bizs))]
		rs := rsTypes[rng.Intn(len(rsTypes))]
		var labels []string
		if biz != 0 && rng.Float64() < 0.2 {
			labels = []string{fmt.Sprintf("tag-%d", rng.Intn(20))}
			if rng.Float64() < 0.3 {
				labels = append(labels, fmt.Sprintf("tag-%d", rng.Intn(20)))
			}
		}
		asset := fmt.Sprintf("MOTHER-%05d", mother)
		if rng.Float64() < 0.02 {
			asset = ""
		}
		raw, _ := json.Marshal(labels)
		if labels == nil {
			raw = []byte("[]")
		}
		pool = append(pool, model.TbRpDetail{
			BkHostID:          i + 1,
			IP:                fmt.Sprintf("10.%d.%d.%d", (i>>16)&0xff, (i>>8)&0xff, i&0xff),
			BkSvrOwnerAssetID: asset,
			DedicatedBiz:      biz,
			RsType:            rs,
			Labels:            raw,
			Status:            model.Unused,
		})
	}
	return pool
}

const benchPoolSize = 50000

func BenchmarkSameSvrOwner_BuildIndex_50k(b *testing.B) {
	pool := buildBenchPool(benchPoolSize, 4, 42)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = GroupBySvrOwnerAsset(pool)
	}
}

func BenchmarkSameSvrOwner_Page20_Grouped_50k(b *testing.B) {
	pool := buildBenchPool(benchPoolSize, 4, 42)
	byAsset := GroupBySvrOwnerAsset(pool)
	page := append([]model.TbRpDetail(nil), pool[:20]...)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		FillSameSvrOwnerCounts(page, byAsset)
	}
}

func BenchmarkSameSvrOwner_Page20_Naive_50k(b *testing.B) {
	pool := buildBenchPool(benchPoolSize, 4, 42)
	page := pool[:20]
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		for j := range page {
			_ = SameSvrOwnerCount(page[j], pool)
		}
	}
}

func BenchmarkSameSvrOwner_SortAll_Grouped_50k(b *testing.B) {
	pool := buildBenchPool(benchPoolSize, 4, 42)
	byAsset := GroupBySvrOwnerAsset(pool)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		data := append([]model.TbRpDetail(nil), pool...)
		FillSameSvrOwnerCounts(data, byAsset)
		sort.Slice(data, func(a, c int) bool {
			return data[a].SameSvrOwnerCount > data[c].SameSvrOwnerCount
		})
		_ = data[0]
	}
}

func BenchmarkSameSvrOwner_IPApi_OneHost_50k(b *testing.B) {
	pool := buildBenchPool(benchPoolSize, 4, 42)
	byAsset := GroupBySvrOwnerAsset(pool)
	cur := pool[1234]
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = PeerIPsFromHosts(ListSameSvrOwnerPeersGrouped(cur, byAsset))
	}
}

func TestSameSvrOwnerBenchSanity_50k(t *testing.T) {
	pool := buildBenchPool(benchPoolSize, 4, 42)
	byAsset := GroupBySvrOwnerAsset(pool)
	page := append([]model.TbRpDetail(nil), pool[:100]...)
	FillSameSvrOwnerCounts(page, byAsset)
	var sum, empty int
	for i, h := range page {
		sum += h.SameSvrOwnerCount
		if h.BkSvrOwnerAssetID == "" {
			empty++
			if h.SameSvrOwnerCount != 0 {
				t.Fatalf("empty asset should count 0, got %d", h.SameSvrOwnerCount)
			}
		}
		_ = i
	}
	t.Logf("pool=%d mothers~=%d page=100 avg_count=%.2f empty_asset_in_page=%d",
		len(pool), len(byAsset), float64(sum)/float64(len(page)), empty)
	for i := 0; i < 10; i++ {
		a := SameSvrOwnerCount(page[i], pool)
		g := len(ListSameSvrOwnerPeersGrouped(page[i], byAsset))
		if a != g {
			t.Fatalf("naive=%d grouped=%d mismatch at i=%d", a, g, i)
		}
	}
}
