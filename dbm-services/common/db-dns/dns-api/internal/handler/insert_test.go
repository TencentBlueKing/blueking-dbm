package handler

import (
	"encoding/json"
	"testing"
)

func TestFlexDomainTypeUnmarshal(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want int64
	}{
		{"int 1", `{"domains":[{"domain_type":1}]}`, 1},
		{"int 0", `{"domains":[{"domain_type":0}]}`, 0},
		{"string", `{"domains":[{"domain_type":"db"}]}`, 0},
		{"numeric string", `{"domains":[{"domain_type":"1"}]}`, 0},
		{"null", `{"domains":[{"domain_type":null}]}`, 0},
		{"missing", `{"domains":[{}]}`, 0},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			var p DnsBasePutReqParam
			if err := json.Unmarshal([]byte(c.in), &p); err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got := int64(p.Domains[0].DomainType); got != c.want {
				t.Fatalf("got %d, want %d", got, c.want)
			}
		})
	}
}
