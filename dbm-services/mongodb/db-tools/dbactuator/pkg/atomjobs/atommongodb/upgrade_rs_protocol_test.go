package atommongodb

import "testing"

func TestUpgradeRsProtocolParams_targetProtocolVersion(t *testing.T) {
	t.Parallel()
	cases := []struct {
		in   int
		want int
	}{
		{0, defaultTargetRsProtocolVersion},
		{-1, defaultTargetRsProtocolVersion},
		{1, 1},
		{2, 2},
	}
	for _, tc := range cases {
		tc := tc
		t.Run("", func(t *testing.T) {
			t.Parallel()
			p := &UpgradeRsProtocolParams{TargetProtocolVersion: tc.in}
			if got := p.targetProtocolVersion(); got != tc.want {
				t.Fatalf("targetProtocolVersion() = %d, want %d", got, tc.want)
			}
		})
	}
}

func TestFcvAtLeast(t *testing.T) {
	t.Parallel()
	ok, err := fcvAtLeast("3.6", minFcvForRsProtocolUpgrade)
	if err != nil {
		t.Fatal(err)
	}
	if !ok {
		t.Fatal("expected 3.6 >= 3.6")
	}
	ok, err = fcvAtLeast("3.4", minFcvForRsProtocolUpgrade)
	if err != nil {
		t.Fatal(err)
	}
	if ok {
		t.Fatal("expected 3.4 < 3.6")
	}
	_, err = fcvAtLeast("bad", minFcvForRsProtocolUpgrade)
	if err == nil {
		t.Fatal("expected parse error")
	}
}
