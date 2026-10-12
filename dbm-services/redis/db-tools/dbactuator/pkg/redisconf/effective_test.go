package redisconf

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeTestFile(t *testing.T, path, data string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatalf("mkdir %s failed:%v", filepath.Dir(path), err)
	}
	if err := os.WriteFile(path, []byte(data), 0644); err != nil {
		t.Fatalf("write %s failed:%v", path, err)
	}
}

func readTestFile(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s failed:%v", path, err)
	}
	return string(data)
}

func TestExpandRedisConfIncludes(t *testing.T) {
	dir := t.TempDir()
	confFile := filepath.Join(dir, "redis.conf")
	instConf := filepath.Join(dir, "instance.conf")
	writeTestFile(t, instConf, "requirepass p1\nmaxmemory 1gb\n")
	nested := filepath.Join(dir, "nested.conf")
	writeTestFile(t, nested, "include "+instConf+"\nslaveof 1.1.1.2 30000\n")
	noNewline := filepath.Join(dir, "nonl.conf")
	writeTestFile(t, noNewline, "masterauth p1")

	cases := []struct {
		name         string
		raw          string
		want         string
		wantIncludes []string
	}{
		{
			name: "no include returns raw unchanged",
			raw:  "port 30000\n# include /nowhere.conf\n\n",
			want: "port 30000\n# include /nowhere.conf\n\n",
		},
		{
			name:         "absolute path inlined in place",
			raw:          "port 30000\ninclude " + instConf + "\nmaxmemory 2gb\n",
			want:         "port 30000\nrequirepass p1\nmaxmemory 1gb\nmaxmemory 2gb\n",
			wantIncludes: []string{instConf},
		},
		{
			name:         "relative path resolved against conf dir",
			raw:          "include instance.conf\n",
			want:         "requirepass p1\nmaxmemory 1gb\n",
			wantIncludes: []string{instConf},
		},
		{
			name:         "quoted path and upper case directive",
			raw:          "INCLUDE \"" + instConf + "\"\n",
			want:         "requirepass p1\nmaxmemory 1gb\n",
			wantIncludes: []string{instConf},
		},
		{
			name:         "nested include",
			raw:          "port 30000\ninclude " + nested + "\n",
			want:         "port 30000\nrequirepass p1\nmaxmemory 1gb\nslaveof 1.1.1.2 30000\n",
			wantIncludes: []string{nested, instConf},
		},
		{
			name:         "included file without trailing newline does not glue to next line",
			raw:          "include " + noNewline + "\nport 30000\n",
			want:         "masterauth p1\nport 30000\n",
			wantIncludes: []string{noNewline},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, includes, err := ExpandIncludes(confFile, tc.raw)
			if err != nil {
				t.Fatalf("expand err:%v", err)
			}
			if got != tc.want {
				t.Errorf("expanded =\n%q\nwant\n%q", got, tc.want)
			}
			if strings.Join(includes, ",") != strings.Join(tc.wantIncludes, ",") {
				t.Errorf("includes = %v, want %v", includes, tc.wantIncludes)
			}
		})
	}
}

func TestExpandRedisConfIncludesOverrideOrder(t *testing.T) {
	dir := t.TempDir()
	confFile := filepath.Join(dir, "redis.conf")
	instConf := filepath.Join(dir, "instance.conf")
	writeTestFile(t, instConf, "maxmemory 1gb\n")

	after, _, err := ExpandIncludes(confFile, "include "+instConf+"\nmaxmemory 2gb\n")
	if err != nil {
		t.Fatal(err)
	}
	if got := ParseDirectives(after).LastValue("maxmemory"); got != "2gb" {
		t.Errorf("directive after include should win,got %q", got)
	}
	before, _, err := ExpandIncludes(confFile, "maxmemory 2gb\ninclude "+instConf+"\n")
	if err != nil {
		t.Fatal(err)
	}
	if got := ParseDirectives(before).LastValue("maxmemory"); got != "1gb" {
		t.Errorf("included value should override the one before include,got %q", got)
	}
}

func TestExpandRedisConfIncludesErrors(t *testing.T) {
	dir := t.TempDir()
	confFile := filepath.Join(dir, "redis.conf")
	writeTestFile(t, confFile, "include "+filepath.Join(dir, "a.conf")+"\n")
	writeTestFile(t, filepath.Join(dir, "a.conf"), "include "+confFile+"\n")

	// 一条 9 层的链: deep0 -> deep1 -> ... -> deep9
	for i := 0; i < 9; i++ {
		writeTestFile(t, filepath.Join(dir, "deep"+string(rune('0'+i))+".conf"),
			"include "+filepath.Join(dir, "deep"+string(rune('0'+i+1))+".conf")+"\n")
	}
	writeTestFile(t, filepath.Join(dir, "deep9.conf"), "port 30000\n")

	cases := []struct {
		name    string
		raw     string
		wantErr string
	}{
		{"missing file", "include " + filepath.Join(dir, "instance.conf") + "\n", "instance.conf cannot be read"},
		{"cycle", "include " + filepath.Join(dir, "a.conf") + "\n", "forms a cycle"},
		{"glob", "include " + filepath.Join(dir, "*.conf") + "\n", "glob"},
		{"too deep", "include " + filepath.Join(dir, "deep0.conf") + "\n", "nested deeper than"},
		{"no path", "include\n", "without a path"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, _, err := ExpandIncludes(confFile, tc.raw)
			if err == nil || !strings.Contains(err.Error(), tc.wantErr) {
				t.Errorf("err = %v, want it to contain %q", err, tc.wantErr)
			}
		})
	}
}
