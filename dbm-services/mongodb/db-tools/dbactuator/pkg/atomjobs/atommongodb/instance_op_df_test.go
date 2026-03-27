package atommongodb

import (
	"os"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestParseDfB1POutput(t *testing.T) {
	t.Parallel()
	stdout := `Filesystem     1024-blocks      Used Available Use% Mounted on
/dev/sda1       100000000000  30000000000  70000000000  30% /data`
	total, avail, err := parseDfB1POutput(stdout)
	if err != nil {
		t.Fatalf("parseDfB1POutput: %v", err)
	}
	if total != 100000000000 || avail != 70000000000 {
		t.Fatalf("got total=%d avail=%d", total, avail)
	}
}

func TestParseDfB1POutput_RejectsBadLine(t *testing.T) {
	t.Parallel()
	_, _, err := parseDfB1POutput("not df")
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestParseDfB1POutput_LocalizedHeaderStillParsesDataRow(t *testing.T) {
	t.Parallel()
	// Simulates zh_CN locale df: header is not "Filesystem"; data row still has ASCII digits.
	stdout := `文件系统       1024块         已用      可用 已用% 挂载点
/dev/sda1       100000000000  30000000000  70000000000   30% /data`
	total, avail, err := parseDfB1POutput(stdout)
	if err != nil {
		t.Fatalf("parseDfB1POutput: %v", err)
	}
	if total != 100000000000 || avail != 70000000000 {
		t.Fatalf("got total=%d avail=%d", total, avail)
	}
}

// envRunDfSmokeTest enables TestDf (real df on /). Default: skipped.
const envRunDfSmokeTest = "RUN_DF_SMOKE_TEST"

// TestDf runs df -B1 -P on / and parses output (integration smoke test).
// Set RUN_DF_SMOKE_TEST=1 to run; otherwise skipped (environment-dependent).
func TestDf(t *testing.T) {
	if os.Getenv(envRunDfSmokeTest) != "1" {
		t.Skipf("set %s=1 to run df smoke test on /", envRunDfSmokeTest)
	}
	ret, err := dfRunWithLocale("/", "-B1", "-P").Run(30 * time.Second)
	if err != nil || ret.ExitCode != 0 {
		t.Fatalf("df failed: exit=%d err=%v stderr=%q stdout=%q", ret.ExitCode, err, ret.GetStderr(), ret.GetStdout())
	}
	out := strings.TrimSpace(ret.GetStdout())
	total, avail, perr := parseDfB1POutput(out)
	if perr != nil {
		t.Fatalf("parseDfB1POutput: %v stdout=%q", perr, out)
	}
	if total == 0 {
		t.Fatal("total filesystem size is zero")
	}
	if avail > total {
		t.Fatalf("avail > total: avail=%d total=%d", avail, total)
	}
	t.Logf("df /: total_bytes=%d avail_bytes=%d", total, avail)
}

func TestDuRunWithLocaleCmdArgs(t *testing.T) {
	t.Parallel()
	path := "/data/mongodata/27017/db"
	tests := []struct {
		name     string
		duFlags  []string
		wantArgs []string
	}{
		{
			name:     "sh",
			duFlags:  []string{"-sh"},
			wantArgs: []string{"LC_ALL=C", "du", "-sh", path},
		},
		{
			name:     "sb",
			duFlags:  []string{"-sb"},
			wantArgs: []string{"LC_ALL=C", "du", "-sb", path},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			cb := duRunWithLocale(path, tt.duFlags...)
			bin, args := cb.GetCmd()
			if bin != "env" {
				t.Fatalf("bin=%q want env", bin)
			}
			if !reflect.DeepEqual(args, tt.wantArgs) {
				t.Fatalf("args=%v want %v", args, tt.wantArgs)
			}
		})
	}
}
