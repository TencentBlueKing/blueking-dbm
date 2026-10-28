package atommongodb

import (
	"encoding/json"
	"testing"
)

func TestJSONIntUnmarshal(t *testing.T) {
	cases := []struct {
		name    string
		raw     string
		want    int
		wantSet bool
	}{
		{name: "number", raw: `16`, want: 16, wantSet: true},
		{name: "string", raw: `"-1"`, want: -1, wantSet: true},
		{name: "null", raw: `null`, want: 0, wantSet: false},
		{name: "empty string", raw: `""`, want: 0, wantSet: false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var got JSONInt
			if err := json.Unmarshal([]byte(tc.raw), &got); err != nil {
				t.Fatal(err)
			}
			if got.Set != tc.wantSet || got.Value != tc.want {
				t.Fatalf("got set=%v value=%d", got.Set, got.Value)
			}
		})
	}

	var missing struct {
		Task JSONInt `json:"taskExecutorPoolSize"`
	}
	if err := json.Unmarshal([]byte(`{}`), &missing); err != nil {
		t.Fatal(err)
	}
	if missing.Task.OrUnset() != -1 {
		t.Fatalf("missing field OrUnset=%d", missing.Task.OrUnset())
	}
}
