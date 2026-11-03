package rollback

import (
	"compress/gzip"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

// scriptBinlogTool puts a shell script in binlog_tool's place; $1 is --logfile=<path>.
func scriptBinlogTool(t *testing.T, body string) func() {
	t.Helper()
	bin := filepath.Join(t.TempDir(), "binlog_tool")
	if err := os.WriteFile(bin, []byte("#!/bin/sh\nf=\"${1#--logfile=}\"\n"+body+"\n"), 0755); err != nil {
		t.Fatal(err)
	}
	plusBinlogToolFn = func() (string, error) { return bin, nil }
	return func() { plusBinlogToolFn = plusBinlogTool }
}

func writeStreamGzip(t *testing.T, path string, content []byte, truncate bool) {
	t.Helper()
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	w := gzip.NewWriter(f)
	_, _ = w.Write(content)
	_ = w.Close()
	_ = f.Close()
	if truncate {
		st, _ := os.Stat(path)
		if err = os.Truncate(path, st.Size()/2); err != nil {
			t.Fatal(err)
		}
	}
}

func streamLines(t *testing.T, file, workDir string) ([]string, streamCPU, error) {
	t.Helper()
	var lines []string
	cpu, err := runBinlogToolStream(file, workDir, 1, 0, func(line string) error {
		lines = append(lines, line)
		return nil
	})
	return lines, cpu, err
}

func TestStreamMatchesTheDecompressedFileLineByLine(t *testing.T) {
	defer scriptBinlogTool(t, `cat "$f"`)()
	dir, workDir := t.TempDir(), t.TempDir()
	content := []byte(restoreLine(2, 101) + "\n" + restoreLine(2, 102) + "\n")
	plain := filepath.Join(dir, "binlog-a.log")
	if err := os.WriteFile(plain, content, 0644); err != nil {
		t.Fatal(err)
	}
	writeStreamGzip(t, plain+".gz", content, false)

	fromDisk, _, err := streamLines(t, plain, workDir)
	if err != nil {
		t.Fatal(err)
	}
	streamed, _, err := streamLines(t, plain+".gz", workDir)
	if err != nil || !reflect.DeepEqual(streamed, fromDisk) || len(streamed) != 2 {
		t.Fatalf("streamed %v vs %v: %v", streamed, fromDisk, err)
	}
	if entries, _ := os.ReadDir(workDir); len(entries) != 0 {
		t.Fatalf("work dir holds %v", entries)
	}
}

func TestStreamDrainsWhenBinlogToolStopsEarly(t *testing.T) {
	// binlog_tool may stop reading at end-datetime: the rest still goes through the decompressor,
	// which then exits 0 instead of failing on a closed pipe.
	defer scriptBinlogTool(t, `head -n 1 "$f"`)()
	file := filepath.Join(t.TempDir(), "binlog-a.log.gz")
	writeStreamGzip(t, file, []byte(strings.Repeat(restoreLine(2, 101)+"\n", 100000)), false)
	lines, _, err := streamLines(t, file, t.TempDir())
	if err != nil || len(lines) != 1 {
		t.Fatalf("lines=%d err=%v", len(lines), err)
	}
}

func TestStreamFailsOnATruncatedBinlog(t *testing.T) {
	// The tool takes the short input and exits 0; only the decompressor tells.
	defer scriptBinlogTool(t, `cat "$f" >/dev/null; exit 0`)()
	file := filepath.Join(t.TempDir(), "binlog-a.log.gz")
	writeStreamGzip(t, file, []byte(strings.Repeat(restoreLine(2, 101)+"\n", 10000)), true)
	_, _, err := streamLines(t, file, t.TempDir())
	if err == nil || !strings.Contains(err.Error(), "备份文件损坏") || !strings.Contains(err.Error(), "binlog-a.log.gz") {
		t.Fatalf("err=%v", err)
	}
}

func TestStreamFailsOnBinlogToolErrors(t *testing.T) {
	for name, body := range map[string]string{
		"ERR on stderr": `cat "$f" >/dev/null; echo "ERR: bad binlog" >&2`,
		"exit status":   `cat "$f" >/dev/null; exit 3`,
	} {
		reset := scriptBinlogTool(t, body)
		file := filepath.Join(t.TempDir(), "binlog-a.log.gz")
		writeStreamGzip(t, file, []byte(restoreLine(2, 101)+"\n"), false)
		workDir := t.TempDir()
		_, _, err := streamLines(t, file, workDir)
		reset()
		if err == nil || !strings.Contains(err.Error(), "binlog_tool failed") || strings.Contains(err.Error(), "备份文件损坏") {
			t.Fatalf("%s: err=%v", name, err)
		}
		if name == "ERR on stderr" && !strings.Contains(err.Error(), filepath.Join(workDir, "binlog-a.log.gz.tool.err")) {
			t.Fatalf("%s: stderr not kept: %v", name, err)
		}
	}
}

func TestStreamStopsBothOnTheFirstLineError(t *testing.T) {
	defer scriptBinlogTool(t, `cat "$f"`)()
	file := filepath.Join(t.TempDir(), "binlog-a.log.gz")
	writeStreamGzip(t, file, []byte(strings.Repeat(restoreLine(2, 101)+"\n", 100000)), false)
	stop := errors.New("apply failed")
	seen := 0
	begin := time.Now()
	_, err := runBinlogToolStream(file, t.TempDir(), 1, 0, func(string) error {
		seen++
		return stop
	})
	if !errors.Is(err, stop) || seen != 1 || time.Since(begin) > 10*time.Second {
		t.Fatalf("err=%v seen=%d after %v", err, seen, time.Since(begin))
	}
}

func TestReplayKvstoreCorruptBinlogStaysResumable(t *testing.T) {
	// A corrupted binlog fails between batches: what went in is exact, so binlogpos is kept.
	files, _, p := replayFixture(t)
	binlogToolFn = func(file, _ string, _ uint64, _ int64, onLine func(string) error) (streamCPU, error) {
		return streamCPU{}, corrupted(filepath.Base(file), fmt.Errorf("unexpected end of file"))
	}
	defer func() { binlogToolFn = runBinlogToolStream }()
	_, err := replayKvstore(portLog{}, p, &fakeReplayer{pos: 100}, 2, files, 0, t.TempDir(), nil)
	if err == nil || failedInFlight(err) || !strings.Contains(err.Error(), "备份文件损坏") {
		t.Fatalf("err=%v", err)
	}
}
