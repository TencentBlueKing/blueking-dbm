package pitr

import (
	"bytes"
	"strings"
	"testing"

	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
)

func TestParseTs(t *testing.T) {
	var input1 = `2019-12-17T18:01:40.883+0800	firstTS=(1576576891 1)
2019-12-17T18:01:40.883+0800	lastTS=(1576576892 234)
lastTS(1576576893 2345)
`
	var buf = bytes.NewBuffer([]byte(input1))
	first, last, err := ParseTs(buf)
	if err != nil {
		t.Errorf("first %+v second %+v err %v", first, last, err)
	}
	if first.Sec != 1576576891 || first.I != 1 ||
		last.Sec != 1576576892 || last.I != 234 {
		t.Errorf("first %+v second %+v err %v", first, last, err)
	}
	t.Logf("first %+v second %+v err %v", first, last, err)
}

func TestBuildDumpIncrCmdWithBinArchiveUsesRawOplogOutput(t *testing.T) {
	connInfo := &mymongo.MongoHost{
		Host:   "127.0.0.1",
		Port:   "27017",
		AuthDb: "admin",
		User:   "backup",
		Pass:   "secret",
	}
	lastBackup := &BackupFileName{LastTs: TS{Sec: 100, I: 1}}
	maxTs := &TS{Sec: 200, I: 2}

	cmd := buildDumpIncrCmdWithBin("mongodump.100.7", connInfo, true, true, lastBackup, maxTs)
	cmdLine := cmd.GetCmdLine("", false)

	for _, unexpected := range []string{"--archive=-", "--gzip"} {
		if strings.Contains(cmdLine, unexpected) {
			t.Fatalf("archive incremental dump must keep raw oplog output, got unexpected %s in %s", unexpected, cmdLine)
		}
	}
	for _, expected := range []string{"mongodump.100.7", "-d local", "-c oplog.rs", `"ts":{"$gte":`, `"ts":{"$gte":{"$timestamp":{"t":100,"i":1}},"$lte":{"$timestamp":{"t":200,"i":2}}}`} {
		if !strings.Contains(cmdLine, expected) {
			t.Fatalf("expected %s in command line: %s", expected, cmdLine)
		}
	}
}

func TestBuildDumpIncrCmdWithBinNonArchiveKeepsGzip(t *testing.T) {
	connInfo := &mymongo.MongoHost{
		Host:   "127.0.0.1",
		Port:   "27017",
		AuthDb: "admin",
	}
	lastBackup := &BackupFileName{LastTs: TS{Sec: 100, I: 1}}
	maxTs := &TS{Sec: 200, I: 2}

	cmd := buildDumpIncrCmdWithBin("mongodump.4.2", connInfo, true, false, lastBackup, maxTs)
	cmdLine := cmd.GetCmdLine("", false)

	if !strings.Contains(cmdLine, "--gzip") {
		t.Fatalf("expected non-archive zip incremental dump to keep --gzip: %s", cmdLine)
	}
	if strings.Contains(cmdLine, "--archive=-") {
		t.Fatalf("non-archive incremental dump should not use archive: %s", cmdLine)
	}
}
