package datadirjob

import "testing"

func TestRoundTotalKB(t *testing.T) {
	cases := []struct {
		name string
		inG  float64
		outG float64
	}{
		{name: "zero", inG: 0, outG: 0},
		{name: "below_0_5g_to_0g", inG: 0.4, outG: 0},
		{name: "0_5g_to_1g", inG: 0.5, outG: 1},
		{name: "85_3g_to_85g", inG: 85.3, outG: 85},
		{name: "85_5g_to_86g", inG: 85.5, outG: 86},
		{name: "exactly_100g", inG: 100, outG: 100},
		{name: "104g_to_100g", inG: 104, outG: 100},
		{name: "105g_to_110g", inG: 105, outG: 110},
		{name: "999g_to_1000g", inG: 999, outG: 1000},
		{name: "exactly_1000g", inG: 1000, outG: 1000},
		{name: "1049g_to_1000g", inG: 1049, outG: 1000},
		{name: "1050g_to_1100g", inG: 1050, outG: 1100},
		{name: "2150g_to_2200g", inG: 2150, outG: 2200},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			inKB := c.inG * float64(kbPerG)
			gotKB := roundTotalKB(inKB)
			gotG := gotKB / float64(kbPerG)
			if gotG != c.outG {
				t.Fatalf("roundTotalKB(%.1fG)=%.1fG, want %.1fG", c.inG, gotG, c.outG)
			}
		})
	}
}
