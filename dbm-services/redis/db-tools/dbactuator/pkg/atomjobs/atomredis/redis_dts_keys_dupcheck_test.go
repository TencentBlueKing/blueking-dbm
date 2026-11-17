package atomredis

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"
)

func writeKeysFile(t *testing.T, dir, content string) string {
	t.Helper()
	p := filepath.Join(dir, "1.1.1.1_30000.keys")
	if err := os.WriteFile(p, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	return p
}

func noLog(string, ...interface{}) {}

func shardLeftovers(t *testing.T, dir string) []string {
	t.Helper()
	m, _ := filepath.Glob(filepath.Join(dir, "*.dupcheck.shard*.tmp"))
	return m
}

func TestCheckKeysFileDuplicatesNoDup(t *testing.T) {
	dir := t.TempDir()
	var sb strings.Builder
	for i := 0; i < 5000; i++ {
		fmt.Fprintf(&sb, "key_%d\n", i)
	}
	f := writeKeysFile(t, dir, sb.String())
	// 极小的分片大小,强制走多分片逻辑
	for _, shardBytes := range []int64{1 << 30, 1024} {
		ret, err := checkKeysFileDuplicates(f, dir, shardBytes, 16, noLog)
		if err != nil {
			t.Fatal(err)
		}
		if ret.DupKeys != 0 || ret.TotalLines != 5000 {
			t.Fatalf("shardBytes=%d unexpected ret:%+v", shardBytes, ret)
		}
		if _, err := os.Stat(ret.DupFile); !os.IsNotExist(err) {
			t.Fatalf("dup file should not exist when no dup,err:%v", err)
		}
		if l := shardLeftovers(t, dir); len(l) != 0 {
			t.Fatalf("shard files not cleaned:%v", l)
		}
	}
}

func TestCheckKeysFileDuplicatesWithDup(t *testing.T) {
	dir := t.TempDir()
	var sb strings.Builder
	for i := 0; i < 3000; i++ {
		fmt.Fprintf(&sb, "key_%d\n", i)
	}
	// key_1 共3次,key_2 共2次,含空格/中文的key各重复一次,最后一行不带换行符也重复
	sb.WriteString("key_1\nkey_1\nkey_2\nhello world\nhello world\n中文key\n中文key\nlast")
	sb.WriteString("\nlast")
	f := writeKeysFile(t, dir, sb.String())
	want := []string{"2 hello world", "3 key_1", "2 key_2", "2 last", "2 中文key"}
	sort.Strings(want)

	for _, shardBytes := range []int64{1 << 30, 512} {
		ret, err := checkKeysFileDuplicates(f, dir, shardBytes, 8, noLog)
		if err != nil {
			t.Fatal(err)
		}
		if ret.DupKeys != 5 || ret.DupLines != 6 || ret.TotalLines != 3000+9 {
			t.Fatalf("shardBytes=%d unexpected ret:%+v", shardBytes, ret)
		}
		content, err := os.ReadFile(ret.DupFile)
		if err != nil {
			t.Fatal(err)
		}
		got := strings.Split(strings.TrimSpace(string(content)), "\n")
		sort.Strings(got)
		if strings.Join(got, "|") != strings.Join(want, "|") {
			t.Fatalf("shardBytes=%d dup lines mismatch,got:%v,want:%v", shardBytes, got, want)
		}
		if len(ret.Examples) != 5 {
			t.Fatalf("examples:%v", ret.Examples)
		}
		if l := shardLeftovers(t, dir); len(l) != 0 {
			t.Fatalf("shard files not cleaned:%v", l)
		}
	}
}

func TestCheckKeysFileDuplicatesEdgeCases(t *testing.T) {
	dir := t.TempDir()
	// 空文件
	f := writeKeysFile(t, dir, "")
	ret, err := checkKeysFileDuplicates(f, dir, 1024, 4, noLog)
	if err != nil || ret.DupKeys != 0 || ret.TotalLines != 0 {
		t.Fatalf("empty file,ret:%+v,err:%v", ret, err)
	}
	// 超长行(超过读缓冲),且重复
	long := strings.Repeat("a", keysDupCheckReadBufSize*2+17)
	f = writeKeysFile(t, dir, long+"\nx\n"+long+"\n")
	for _, shardBytes := range []int64{1 << 40, 1024} {
		ret, err = checkKeysFileDuplicates(f, dir, shardBytes, 4, noLog)
		if err != nil || ret.DupKeys != 1 || ret.DupLines != 1 || ret.TotalLines != 3 {
			t.Fatalf("long line,shardBytes=%d,ret:%+v,err:%v", shardBytes, ret, err)
		}
	}
	// 文件不存在
	if _, err = checkKeysFileDuplicates(filepath.Join(dir, "nonexistent"), dir, 1024, 4, noLog); err == nil {
		t.Fatal("expect error for nonexistent file")
	}
}

func TestCalcKeysDupShards(t *testing.T) {
	cases := []struct {
		size, shard int64
		max, want   int
	}{
		{0, 100, 256, 1},
		{100, 100, 256, 1},
		{101, 100, 256, 2},
		{20 << 30, 64 << 20, 256, 256}, // 20G/64M=320,被上限截断
		{10 << 30, 64 << 20, 256, 160},
	}
	for _, c := range cases {
		if got := calcKeysDupShards(c.size, c.shard, c.max); got != c.want {
			t.Fatalf("calcKeysDupShards(%d,%d,%d)=%d,want %d", c.size, c.shard, c.max, got, c.want)
		}
	}
}
