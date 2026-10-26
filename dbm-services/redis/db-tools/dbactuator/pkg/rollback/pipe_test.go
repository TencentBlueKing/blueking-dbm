// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"math/rand"
	"net"
	"reflect"
	"strconv"
	"strings"
	"testing"

	"github.com/go-redis/redis/v8"
)

// fakeExec records batches and answers each command through reply.
type fakeExec struct {
	batches [][][]string
	reply   func(args []string) error
	fail    error
}

func (f *fakeExec) execBatch(cmds [][]string) ([]error, error) {
	f.batches = append(f.batches, cmds)
	if f.fail != nil {
		return nil, f.fail
	}
	replies := make([]error, len(cmds))
	if f.reply != nil {
		for i, args := range cmds {
			replies[i] = f.reply(args)
		}
	}
	return replies, nil
}

func TestSplitArgsLikeRedisCli(t *testing.T) {
	cases := map[string][]string{
		`"set" "k" "v"`:                        {"set", "k", "v"},
		`"setex" "k" 100 "v"` + "\n":           {"setex", "k", "100", "v"},
		`"set" "a\"b\\c" "\x00\xff\n\r\t\a\b"`: {"set", `a"b\c`, "\x00\xff\n\r\t\a\b"},
		`"set" "" "v"`:                         {"set", "", "v"},
		"  set   k\tv \r\n":                    {"set", "k", "v"},
		`ab"cd"`:                               {"abcd"},
		`'it\'s' 'a"b'`:                        {"it's", `a"b`},
		`"\q" "\x4" "\xZZ"`:                    {"q", "x4", "xZZ"},
		"a\vb":                                 {"a\vb"},
	}
	for line, want := range cases {
		got, ok := splitArgs(line)
		if !ok || !reflect.DeepEqual(got, want) {
			t.Fatalf("%q: got %q ok=%v, want %q", line, got, ok, want)
		}
	}
	for _, line := range []string{"", "  \r\n"} {
		if got, ok := splitArgs(line); !ok || len(got) != 0 {
			t.Fatalf("%q: got %q ok=%v", line, got, ok)
		}
	}
	for _, line := range []string{`"set" "abc`, `"a"b`, `'a'b`, `"abc\`, `'abc`} {
		if got, ok := splitArgs(line); ok {
			t.Fatalf("%q: want invalid, got %q", line, got)
		}
	}
}

// sdscatrepr quotes s the way tredisbinlog writes every key and value.
func sdscatrepr(s string) string {
	var b strings.Builder
	b.WriteByte('"')
	for i := 0; i < len(s); i++ {
		switch c := s[i]; c {
		case '\\', '"':
			b.WriteByte('\\')
			b.WriteByte(c)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		case '\a':
			b.WriteString(`\a`)
		case '\b':
			b.WriteString(`\b`)
		default:
			if c >= 0x20 && c < 0x7f {
				b.WriteByte(c)
			} else {
				fmt.Fprintf(&b, `\x%02x`, c)
			}
		}
	}
	b.WriteByte('"')
	return b.String()
}

func TestSplitArgsUndoesSdscatrepr(t *testing.T) {
	rnd := rand.New(rand.NewSource(1))
	for n := 0; n < 2000; n++ {
		args := []string{"hset"}
		for j := rnd.Intn(4); j >= 0; j-- {
			buf := make([]byte, rnd.Intn(40))
			rnd.Read(buf)
			args = append(args, string(buf))
		}
		quoted := make([]string, len(args))
		for i, arg := range args {
			quoted[i] = sdscatrepr(arg)
		}
		line := strings.Join(quoted, " ") + "\n"
		if got, ok := splitArgs(line); !ok || !reflect.DeepEqual(got, args) {
			t.Fatalf("%q: got %q ok=%v, want %q", line, got, ok, args)
		}
	}
}

func TestCommandPipeBatchesInOrder(t *testing.T) {
	exec := &fakeExec{}
	var seen []string
	pipe := &commandPipe{exec: exec, onReply: func(args []string, _ error) error {
		seen = append(seen, args[1])
		return nil
	}}
	n := 2*pipeBatchCmds + 500
	for i := 0; i < n; i++ {
		if err := pipe.add([]string{"set", strconv.Itoa(i), "v"}); err != nil {
			t.Fatal(err)
		}
	}
	if err := pipe.flush(); err != nil {
		t.Fatal(err)
	}
	var sizes []int
	for _, b := range exec.batches {
		sizes = append(sizes, len(b))
	}
	if !reflect.DeepEqual(sizes, []int{pipeBatchCmds, pipeBatchCmds, 500}) || len(seen) != n {
		t.Fatalf("sizes=%v seen=%d", sizes, len(seen))
	}
	for i, key := range seen {
		if key != strconv.Itoa(i) {
			t.Fatalf("reply %d is for %s", i, key)
		}
	}
	if err := pipe.flush(); err != nil || len(exec.batches) != 3 {
		t.Fatalf("empty flush sent a batch: %v", err)
	}
}

func TestCommandPipeFlushesLargeValuesEarly(t *testing.T) {
	exec := &fakeExec{}
	pipe := &commandPipe{exec: exec, onReply: func([]string, error) error { return nil }}
	big := strings.Repeat("x", pipeBatchBytes/3+1)
	for i := 0; i < 3; i++ {
		if err := pipe.add([]string{"set", "k", big}); err != nil {
			t.Fatal(err)
		}
	}
	if len(exec.batches) != 1 || len(exec.batches[0]) != 3 {
		t.Fatalf("batches=%d", len(exec.batches))
	}
}

func TestCommandPipeFailuresAreInFlight(t *testing.T) {
	pipe := &commandPipe{exec: &fakeExec{fail: io.ErrUnexpectedEOF},
		onReply: func([]string, error) error { return nil }}
	_ = pipe.add([]string{"set", "k", "v"})
	err := pipe.flush()
	if !failedInFlight(err) || !strings.Contains(err.Error(), "broke off") {
		t.Fatalf("err=%v", err)
	}

	stop := errors.New("ERR apply failed")
	pipe = &commandPipe{exec: &fakeExec{reply: func([]string) error { return stop }},
		onReply: func(_ []string, reply error) error { return reply }}
	_ = pipe.add([]string{"set", "k", "v"})
	err = fmt.Errorf("kvstore 1: %w", pipe.flush())
	if !failedInFlight(err) || !errors.Is(err, stop) {
		t.Fatalf("err=%v", err)
	}
	if failedInFlight(errors.New("binlog_tool failed")) {
		t.Fatal("a plain error is not in flight")
	}
}

// respServer answers commands until it reads one named "QUIT", then drops the connection.
func respServer(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = ln.Close() })
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			go serveResp(conn)
		}
	}()
	return ln.Addr().String()
}

func serveResp(conn net.Conn) {
	defer conn.Close()
	r := bufio.NewReader(conn)
	for {
		args, err := readRespArray(r)
		if err != nil {
			return
		}
		var reply string
		switch strings.ToUpper(args[0]) {
		case "QUIT":
			return
		case "ERRME":
			reply = "-ERR boom\r\n"
		case "NILME":
			reply = "$-1\r\n"
		default:
			reply = "+OK\r\n"
		}
		if _, err = conn.Write([]byte(reply)); err != nil {
			return
		}
	}
}

func readRespArray(r *bufio.Reader) ([]string, error) {
	line, err := r.ReadString('\n')
	if err != nil || !strings.HasPrefix(line, "*") {
		return nil, fmt.Errorf("bad request %q: %v", line, err)
	}
	n, _ := strconv.Atoi(strings.TrimSpace(line[1:]))
	args := make([]string, n)
	for i := range args {
		if line, err = r.ReadString('\n'); err != nil {
			return nil, err
		}
		size, _ := strconv.Atoi(strings.TrimSpace(line[1:]))
		buf := make([]byte, size+2)
		if _, err = io.ReadFull(r, buf); err != nil {
			return nil, err
		}
		args[i] = string(buf[:size])
	}
	return args, nil
}

func TestRedisPipeSplitsErrorRepliesFromBrokenBatches(t *testing.T) {
	cli := redis.NewClient(&redis.Options{Addr: respServer(t), MaxRetries: -1})
	defer cli.Close()
	replies, err := redisPipe{cli: cli}.execBatch([][]string{{"set", "k", "v"}, {"errme"}, {"nilme"}, {"set", "a", ""}})
	if err != nil || len(replies) != 4 || replies[0] != nil || replies[2] != nil || replies[3] != nil ||
		replies[1] == nil || replies[1].Error() != "ERR boom" {
		t.Fatalf("replies=%v err=%v", replies, err)
	}
	if _, err = (redisPipe{cli: cli}).execBatch([][]string{{"set", "k", "v"}, {"quit"}, {"set", "b", "v"}}); err == nil {
		t.Fatal("want an error for a batch whose connection dropped")
	}
}
