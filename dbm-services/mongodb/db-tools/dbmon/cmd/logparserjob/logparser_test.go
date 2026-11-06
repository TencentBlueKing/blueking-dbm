package logparserjob

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"go.uber.org/zap"
)

func TestParseFileFlushesJSON(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "mongo.log")
	line := `{"t":{"$date":"2024-04-12T19:30:50.102+08:00"},"s":"I","c":"NETWORK","id":22943,"ctx":"listener","msg":"Connection accepted","attr":{"remote":"1.1.1.1:1","connectionId":1,"connectionCount":1}}`
	if err := os.WriteFile(src, []byte(line+"\n"), 0644); err != nil {
		t.Fatal(err)
	}

	outDir := filepath.Join(dir, "jsonlog")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	succ, fail, err := ParseFile(src, outDir, "mongo.log", false, ctx, context.Background(), []byte(`"meta":{"app":"test"}`), zap.NewNop())
	if err != nil {
		t.Fatalf("ParseFile: %v", err)
	}
	if succ != 1 || fail != 0 {
		t.Fatalf("succ=%d fail=%d, want 1 and 0", succ, fail)
	}

	matches, err := filepath.Glob(filepath.Join(outDir, "mongo.log.*"))
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) == 0 {
		t.Fatal("json log file was not created")
	}
	body, err := os.ReadFile(matches[0])
	if err != nil {
		t.Fatal(err)
	}
	text := strings.TrimSpace(string(body))
	if text == "" {
		t.Fatal("json log is empty; buffer was not flushed")
	}
	var got map[string]interface{}
	if err := json.Unmarshal([]byte(text), &got); err != nil {
		t.Fatalf("output is not json: %v\n%s", err, text)
	}
	if got["msg"] != "Connection accepted" {
		t.Fatalf("msg = %v", got["msg"])
	}
	meta, ok := got["meta"].(map[string]interface{})
	if !ok || meta["app"] != "test" {
		t.Fatalf("meta = %v", got["meta"])
	}
}

func TestParseFileFollowsAppend(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "mongo.log")
	first := `{"t":{"$date":"2024-04-12T19:30:50.102+08:00"},"s":"I","c":"NETWORK","id":22943,"ctx":"listener","msg":"first line","attr":{"remote":"1.1.1.1:1","connectionId":1,"connectionCount":1}}`
	if err := os.WriteFile(src, []byte(first+"\n"), 0644); err != nil {
		t.Fatal(err)
	}
	outDir := filepath.Join(dir, "jsonlog")
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan struct{})
	go func() {
		defer close(done)
		_, _, _ = ParseFile(src, outDir, "mongo.log", true, ctx, context.Background(), nil, zap.NewNop())
	}()

	if !waitJSONContains(t, outDir, "first line", 5*time.Second) {
		cancel()
		t.Fatal("initial line was not written")
	}

	second := `{"t":{"$date":"2024-04-12T19:30:51.102+08:00"},"s":"I","c":"NETWORK","id":22943,"ctx":"listener","msg":"second line","attr":{"remote":"1.1.1.1:1","connectionId":1,"connectionCount":1}}`
	f, err := os.OpenFile(src, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		cancel()
		t.Fatal(err)
	}
	if _, err = f.Write([]byte(second + "\n")); err != nil {
		f.Close()
		cancel()
		t.Fatal(err)
	}
	if err = f.Close(); err != nil {
		cancel()
		t.Fatal(err)
	}

	if !waitJSONContains(t, outDir, "second line", 5*time.Second) {
		cancel()
		t.Fatal("appended line was not followed")
	}
	cancel()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("ParseFile did not return after cancel")
	}
}

func TestParseFileFollowsAcrossSessions(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "mongo.log")
	outDir := filepath.Join(dir, "jsonlog")
	if err := os.WriteFile(src, []byte(v3Line("boot")+"\n"), 0644); err != nil {
		t.Fatal(err)
	}

	for session := 1; session <= 2; session++ {
		ctx, cancel := context.WithCancel(context.Background())
		done := make(chan struct{})
		go func() {
			defer close(done)
			_, _, _ = ParseFile(src, outDir, "mongo.log", true, ctx, context.Background(), nil, zap.NewNop())
		}()
		// 先等 tail 读到末尾并进入 follow，再追加。这样第二轮只能靠 inotify 看到新行。
		time.Sleep(300 * time.Millisecond)
		marker := fmt.Sprintf("session-%d", session)
		appendLine(t, src, v3Line(marker))
		started := time.Now()
		if !waitJSONContains(t, outDir, marker, 5*time.Second) {
			cancel()
			t.Fatalf("session %d did not follow %q", session, marker)
		}
		t.Logf("session %d saw %s after %s", session, marker, time.Since(started).Round(time.Millisecond))
		cancel()
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			t.Fatalf("session %d did not stop", session)
		}
	}
}

func v3Line(msg string) string {
	return fmt.Sprintf(`{"t":{"$date":"2024-04-12T19:30:50.102+08:00"},"s":"I","c":"NETWORK","id":22943,"ctx":"listener","msg":%q,"attr":{"remote":"1.1.1.1:1","connectionId":1,"connectionCount":1}}`, msg)
}

func appendLine(t *testing.T, path, line string) {
	t.Helper()
	f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	if _, err = f.Write([]byte(line + "\n")); err != nil {
		t.Fatal(err)
	}
}

func waitJSONContains(t *testing.T, dir, text string, timeout time.Duration) bool {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		matches, err := filepath.Glob(filepath.Join(dir, "mongo.log.*"))
		if err == nil {
			for _, name := range matches {
				body, err := os.ReadFile(name)
				if err == nil && strings.Contains(string(body), text) {
					return true
				}
			}
		}
		time.Sleep(100 * time.Millisecond)
	}
	return false
}
