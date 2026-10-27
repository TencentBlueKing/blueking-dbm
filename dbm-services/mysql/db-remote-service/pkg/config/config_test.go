package config

import (
	"reflect"
	"testing"
)

func TestParsePorts(t *testing.T) {
	def := map[int]struct{}{DefaultMySQLDTSMasterPort: {}}
	cases := []struct {
		name string
		raw  string
		want map[int]struct{}
	}{
		{"single", "18301", def},
		{"multi", "18301,18302", map[int]struct{}{18301: {}, 18302: {}}},
		{"spaces and duplicates", " 18301 , 18302,18301 ", map[int]struct{}{18301: {}, 18302: {}}},
		{"skip invalid item", "18302,abc", map[int]struct{}{18302: {}}},
		{"skip empty item", "18302,,", map[int]struct{}{18302: {}}},
		{"empty fallback", "", def},
		{"all invalid fallback", "0,70000,-1,abc", def},
		{"full width digit fallback", "1830２", def},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := parsePorts(tc.raw); !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("parsePorts(%q) = %v, want %v", tc.raw, got, tc.want)
			}
		})
	}
}
