package atommongodb

import "testing"

func TestParseBalancerBoolRejectsMongoshDocument(t *testing.T) {
	if _, err := parseBalancerBool(`{ mode: "full", inBalancerRound: true, ok: 1 }`); err == nil {
		t.Fatal("mongosh document must not silently parse as false")
	}
	for _, value := range []string{"true", "false"} {
		if _, err := parseBalancerBool(value); err != nil {
			t.Fatalf("parseBalancerBool(%q): %v", value, err)
		}
	}
}

func TestChunkDistributionUnbalanced(t *testing.T) {
	cases := []struct {
		name   string
		result string
		want   bool
	}{
		{name: "balanced", result: `[{"_id":"s1","count":10},{"_id":"s2","count":14}]`, want: false},
		{name: "unbalanced", result: `[{"_id":"s1","count":3},{"_id":"s2","count":9}]`, want: true},
		{name: "no chunks", result: `[]`, want: false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := chunkDistributionUnbalanced(tc.result)
			if err != nil {
				t.Fatalf("chunkDistributionUnbalanced: %v", err)
			}
			if got != tc.want {
				t.Fatalf("got %t, want %t", got, tc.want)
			}
		})
	}
	if _, err := chunkDistributionUnbalanced(`{ _id: "s1", count: 1 }`); err == nil {
		t.Fatal("non-JSON mongosh pretty output must fail")
	}
}
