package common

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v2"
)

func TestBuildMongosExecutorPoolOmitsUnset(t *testing.T) {
	if pool := BuildMongosExecutorPool(-1, -1, -1); pool != nil {
		t.Fatalf("all unset should be nil, got %#v", pool)
	}
	pool := BuildMongosExecutorPool(16, -1, 64)
	if pool[ParamTaskExecutorPoolSize] != 16 || pool[ParamShardingTaskExecutorPoolMaxSize] != 64 {
		t.Fatalf("unexpected pool %#v", pool)
	}
	if _, ok := pool[ParamShardingTaskExecutorPoolMinSize]; ok {
		t.Fatalf("min size -1 should be omitted, got %#v", pool)
	}

	conf := NewYamlMongoSConf()
	conf.Net.Port = 27021
	conf.SetParameter = pool
	out, err := conf.GetConfContent()
	if err != nil {
		t.Fatal(err)
	}
	text := string(out)
	if !strings.Contains(text, "taskExecutorPoolSize: 16") || !strings.Contains(text, "ShardingTaskExecutorPoolMaxSize: 64") {
		t.Fatalf("missing pool keys:\n%s", text)
	}
	if strings.Contains(text, "ShardingTaskExecutorPoolMinSize") {
		t.Fatalf("unset min size was written:\n%s", text)
	}
}

func TestValidateMongosExecutorPool(t *testing.T) {
	cases := []struct {
		name    string
		task    int
		minSize int
		maxSize int
		wantErr bool
	}{
		{name: "all unset", task: -1, minSize: -1, maxSize: -1},
		{name: "valid", task: 16, minSize: 4, maxSize: 64},
		{name: "below unset", task: -2, minSize: -1, maxSize: -1, wantErr: true},
		{name: "above maximum", task: 1025, minSize: -1, maxSize: -1, wantErr: true},
		{name: "min exceeds max", task: -1, minSize: 65, maxSize: 64, wantErr: true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			err := ValidateMongosExecutorPool(tc.task, tc.minSize, tc.maxSize)
			if (err != nil) != tc.wantErr {
				t.Fatalf("ValidateMongosExecutorPool() error = %v, wantErr %v", err, tc.wantErr)
			}
		})
	}
}

func TestPatchMongosExecutorPoolContentKeepsOtherKeys(t *testing.T) {
	in := []byte("" +
		"net:\n" +
		"  port: 27021\n" +
		"  compression:\n" +
		"    compressors: snappy\n" +
		"setParameter:\n" +
		"  taskExecutorPoolSize: 4\n" +
		"  otherFlag: 1\n")
	out, err := PatchMongosExecutorPoolContent(in, 16, -1, 64)
	if err != nil {
		t.Fatal(err)
	}
	var doc yaml.MapSlice
	if err = yaml.Unmarshal(out, &doc); err != nil {
		t.Fatal(err)
	}
	net := mapItem(t, doc, "net").(yaml.MapSlice)
	compression := mapItem(t, net, "compression").(yaml.MapSlice)
	if got := mapItem(t, compression, "compressors"); got != "snappy" {
		t.Fatalf("compressors = %#v", got)
	}
	params := mapItem(t, doc, "setParameter").(yaml.MapSlice)
	if got := mapItem(t, params, "taskExecutorPoolSize"); got != 16 {
		t.Fatalf("taskExecutorPoolSize = %#v", got)
	}
	if got := mapItem(t, params, "ShardingTaskExecutorPoolMaxSize"); got != 64 {
		t.Fatalf("max = %#v", got)
	}
	if got := mapItem(t, params, "otherFlag"); got != 1 {
		t.Fatalf("otherFlag = %#v", got)
	}
	if _, ok := lookupMapItem(params, "ShardingTaskExecutorPoolMinSize"); ok {
		t.Fatal("min size should be removed")
	}
}

func TestPatchMongosExecutorPoolContentDropsEmptySection(t *testing.T) {
	in := []byte("net:\n  port: 27021\nsetParameter:\n  taskExecutorPoolSize: 4\n")
	out, err := PatchMongosExecutorPoolContent(in, -1, -1, -1)
	if err != nil {
		t.Fatal(err)
	}
	var doc yaml.MapSlice
	if err = yaml.Unmarshal(out, &doc); err != nil {
		t.Fatal(err)
	}
	if _, ok := lookupMapItem(doc, "setParameter"); ok {
		t.Fatalf("empty setParameter should be removed:\n%s", out)
	}
	if got := mapItem(t, doc, "net").(yaml.MapSlice); mapItem(t, got, "port") != 27021 {
		t.Fatalf("net.port changed:\n%s", out)
	}
}

func TestPatchMongosExecutorPoolContentPreservesCommentsAndQuotes(t *testing.T) {
	in := "" +
		"# mongos\n" +
		"net:\n" +
		"  bindIp: \"127.0.0.1,10.0.0.1\" # listen\n" +
		"  port: 27021\n" +
		"setParameter:\n" +
		"  # pool size\n" +
		"  taskExecutorPoolSize: 4 # threads\n" +
		"  otherFlag: \"1\"\n"
	out, err := PatchMongosExecutorPoolContent([]byte(in), 16, -1, 64)
	if err != nil {
		t.Fatal(err)
	}
	text := string(out)
	for _, keep := range []string{
		"# mongos\n",
		"  bindIp: \"127.0.0.1,10.0.0.1\" # listen\n",
		"  # pool size\n",
		"  taskExecutorPoolSize: 16 # threads\n",
		"  otherFlag: \"1\"\n",
		"  ShardingTaskExecutorPoolMaxSize: 64\n",
	} {
		if !strings.Contains(text, keep) {
			t.Fatalf("missing %q in:\n%s", keep, text)
		}
	}
	if strings.Contains(text, "ShardingTaskExecutorPoolMinSize") {
		t.Fatalf("unset min size was written:\n%s", text)
	}
}

func TestPatchMongosExecutorPoolContentLeavesFileUntouched(t *testing.T) {
	in := []byte("# c\r\nnet:\r\n  bindIp: \"127.0.0.1\"\r\n")
	out, err := PatchMongosExecutorPoolContent(in, -1, -1, -1)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(in, out) {
		t.Fatalf("file changed:\n%q", out)
	}
}

func TestPatchMongosExecutorPoolFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "mongo.conf")
	raw := []byte("net:\n  port: 27021\n")
	if err := os.WriteFile(path, raw, 0600); err != nil {
		t.Fatal(err)
	}
	backup, err := PatchMongosExecutorPoolFile(path, 8, 2, -1)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(backup, path+".bak.") {
		t.Fatalf("backup path = %q", backup)
	}
	backed, err := os.ReadFile(backup)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(backed, raw) {
		t.Fatalf("backup content = %q", backed)
	}
	info, err := os.Stat(backup)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0600 {
		t.Fatalf("backup perm = %o", info.Mode().Perm())
	}
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	text := string(got)
	if !strings.Contains(text, "taskExecutorPoolSize: 8") || !strings.Contains(text, "ShardingTaskExecutorPoolMinSize: 2") {
		t.Fatalf("file not updated:\n%s", text)
	}
	if strings.Contains(text, "ShardingTaskExecutorPoolMaxSize") {
		t.Fatalf("max size should stay unset:\n%s", text)
	}
}

func TestDescribeMongosExecutorPoolChanges(t *testing.T) {
	in := []byte("setParameter:\n  taskExecutorPoolSize: 16\n  ShardingTaskExecutorPoolMinSize: \"4\"\n  otherFlag: 1\n")
	got, err := DescribeMongosExecutorPoolChanges(in, 32, -1, 100)
	if err != nil {
		t.Fatal(err)
	}
	want := "taskExecutorPoolSize 16 -> 32, ShardingTaskExecutorPoolMinSize 4 -> unset, ShardingTaskExecutorPoolMaxSize unset -> 100"
	if got != want {
		t.Fatalf("changes = %q", got)
	}
	got, err = DescribeMongosExecutorPoolChanges(in, 16, 4, -1)
	if err != nil {
		t.Fatal(err)
	}
	if got != "" {
		t.Fatalf("matching values reported as changes: %q", got)
	}
}

func TestPatchMongosExecutorPoolFileSkipsBackupWhenUnchanged(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "mongo.conf")
	raw := []byte("# c\nnet:\n  bindIp: \"127.0.0.1\"\n")
	if err := os.WriteFile(path, raw, 0644); err != nil {
		t.Fatal(err)
	}
	backup, err := PatchMongosExecutorPoolFile(path, -1, -1, -1)
	if err != nil {
		t.Fatal(err)
	}
	if backup != "" {
		t.Fatalf("unchanged file was backed up to %s", backup)
	}
	matches, err := filepath.Glob(path + ".bak.*")
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 0 {
		t.Fatalf("unexpected backups: %v", matches)
	}
}

func lookupMapItem(ms yaml.MapSlice, key string) (interface{}, bool) {
	for _, item := range ms {
		itemKey, ok := item.Key.(string)
		if ok && itemKey == key {
			return item.Value, true
		}
	}
	return nil, false
}

func mapItem(t *testing.T, ms yaml.MapSlice, key string) interface{} {
	t.Helper()
	val, ok := lookupMapItem(ms, key)
	if !ok {
		t.Fatalf("missing key %s in %#v", key, ms)
	}
	return val
}
