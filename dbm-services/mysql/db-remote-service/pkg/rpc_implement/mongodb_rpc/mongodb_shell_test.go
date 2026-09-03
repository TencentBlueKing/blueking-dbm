// precheck_input_test.go
package mongodb_rpc

import (
	"reflect"
	"strings"
	"testing"
)

func TestPrecheckInput(t *testing.T) {
	endMarker := ";\nprint('" + EndOfOutput + "');\n"
	tests := []struct {
		name     string
		shellBin string
		input    []byte
		want     []byte
		wantErr  bool
	}{
		{
			name:     "Empty input mongo",
			shellBin: "mongo",
			input:    []byte(""),
			want:     []byte("\n" + endMarker),
			wantErr:  false,
		},
		{
			name:     "Input without newline mongo",
			shellBin: "mongo",
			input:    []byte("show"),
			want:     []byte("show\n" + endMarker),
			wantErr:  false,
		},
		{
			name:     "Input with newline mongo",
			shellBin: "mongo",
			input:    []byte("show\n"),
			want:     []byte("show\n" + endMarker),
			wantErr:  false,
		},
		{
			name:     "Non-show input mongo",
			shellBin: "mongo",
			input:    []byte("db.stats()"),
			want:     []byte("db.stats()\n" + endMarker),
			wantErr:  false,
		},
		{
			name:     "mongosh adds end marker",
			shellBin: "mongosh",
			input:    []byte("sh.status()"),
			want:     []byte("sh.status()\n" + endMarker),
			wantErr:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := precheckInput(tt.shellBin, tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("precheckInput() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("precheckInput() = %q, want %q", string(got), string(tt.want))
			}
		})
	}
}

func TestMongoShellMissingHint(t *testing.T) {
	mongoHint := mongoShellMissingHint("mongo", "4.2.19")
	if !strings.Contains(mongoHint, "mongo") || !strings.Contains(mongoHint, "4.2.19") {
		t.Fatalf("unexpected mongo hint: %q", mongoHint)
	}
	mongoshHint := mongoShellMissingHint("mongosh", "5.0.14")
	if !strings.Contains(mongoshHint, "mongosh") || !strings.Contains(mongoshHint, "5.0.14") {
		t.Fatalf("unexpected mongosh hint: %q", mongoshHint)
	}
}

func TestResolveMongoShellBinMissing(t *testing.T) {
	_, err := resolveMongoShellBin("mongo-shell-not-exists-xyz", "4.4.25")
	if err == nil {
		t.Fatal("expected error for missing shell binary")
	}
	if !strings.Contains(err.Error(), "未找到 MongoDB shell 命令") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestIsResponseEnd(t *testing.T) {
	if !isResponseEnd([]byte("ok\n" + EndOfOutput + "\n")) {
		t.Fatal("expected response end marker to be detected")
	}
	if isResponseEnd([]byte("partial output")) {
		t.Fatal("unexpected response end without marker")
	}
}

func TestStripMongoShellPrompt(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  string
	}{
		{
			name:  "mongosh getName",
			input: "connect to server, default db is test\n[direct: mongos] test> test\n[direct: mongos] test> \n[direct: mongos] test> \n",
			want:  "connect to server, default db is test\ntest\n",
		},
		{
			name:  "mongosh use admin",
			input: "connect to server, default db is test\n[direct: mongos] test> switched to db admin\n[direct: mongos] admin> \n",
			want:  "connect to server, default db is test\nswitched to db admin\n",
		},
		{
			name:  "mongosh array result",
			input: "\n[direct: mongos] admin> [ 'admin', 'config' ]\n[direct: mongos] admin> \n",
			want:  "\n[ 'admin', 'config' ]\n",
		},
		{
			name:  "replica set primary direct",
			input: "connect to server, default db is test\nutRs44Prompt [direct: primary] test> test\nutRs44Prompt [direct: primary] test> \n",
			want:  "connect to server, default db is test\ntest\n",
		},
		{
			name:  "replica set secondary direct",
			input: "utRs44Prompt [direct: secondary] test> test\nutRs44Prompt [direct: secondary] test> \n",
			want:  "test\n",
		},
		{
			name:  "replica set topology primary tag",
			input: "utRs44Prompt [primary] test> ok\nutRs44Prompt [primary] test> \n",
			want:  "ok\n",
		},
		{
			name:  "legacy mongo quiet output unchanged",
			input: "connect to server, default db is test\ntest\n\n",
			want:  "connect to server, default db is test\ntest\n",
		},
		{
			name:  "PRIMARY prompt",
			input: "PRIMARY> ok\nPRIMARY> \n",
			want:  "ok\n",
		},
		{
			name:  "do not strip comparison-like lines",
			input: "score> 10\ncount>0\nn> 5\nx> 1\na>b\nfilter> docs\n",
			want:  "score> 10\ncount>0\nn> 5\nx> 1\na>b\nfilter> docs\n",
		},
		{
			name:  "do not strip array or object lines",
			input: "[ 'admin', 'config' ]\n{ a: 1 }\n",
			want:  "[ 'admin', 'config' ]\n{ a: 1 }\n",
		},
		{
			name:  "do not strip direct with zero or multi spaces",
			input: "[direct:mongos] test> bad\n[direct:  mongos] test> bad\n",
			want:  "[direct:mongos] test> bad\n[direct:  mongos] test> bad\n",
		},
		{
			name:  "strip direct with exactly one space",
			input: "[direct: mongos] test> ok\n",
			want:  "ok\n",
		},
		{
			name:  "strip only first prompt group on a line",
			input: "[direct: mongos] test> [direct: mongos] test> keep\n",
			want:  "[direct: mongos] test> keep\n",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := string(stripMongoShellPrompt([]byte(tt.input)))
			if got != tt.want {
				t.Fatalf("got %q, want %q", got, tt.want)
			}
		})
	}
}

func TestIsValidInput(t *testing.T) {
	tests := []struct {
		name  string
		input []byte
		want  bool
	}{
		{name: "Valid input", input: []byte("db.stats()"), want: true},
		{name: "Invalid input", input: []byte("db.stats()\n"), want: true},
		{name: "Valid input with quote", input: []byte("db.stats('{a:1}')"), want: true},
		{name: "Invalid input with quote", input: []byte("db.stats('{a:1}'"), want: false},
		{name: "Valid input with quote", input: []byte("db.stats('{a:1}', 'b')"), want: true},
		{name: "Invalid input with quote", input: []byte("db.stats('{a:1}', 'b'"), want: false},
		{name: "Valid input with quote", input: []byte("db.stats('{a:1}', 'b')"), want: true},
		{name: "valid input no quote", input: []byte("abc;"), want: true},
		{name: "valid input no quote", input: []byte(`'"'`), want: true},
		{name: "valid input no quote", input: []byte(`'x'`), want: true},
		{name: "valid input no quote", input: []byte(`'''`), want: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, _ := isValidInput(tt.input)

			if got != tt.want {
				t.Errorf("isValidInput() = %v, want %v", got, tt.want)
			}
		})
	}
}
