// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"bytes"
	"compress/gzip"
	"encoding/binary"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// ssdRecordBytes builds one record the way tendisssd's encLogVal lays it out.
func ssdRecordBytes(seq int64, logType, enc int32, ttl, ts int64, key, val, aux []byte) []byte {
	var payload bytes.Buffer
	for _, v := range []interface{}{logType, enc, ttl, ts, uint64(len(key))} {
		if err := binary.Write(&payload, binary.LittleEndian, v); err != nil {
			panic(err)
		}
	}
	payload.Write(key)
	if err := binary.Write(&payload, binary.LittleEndian, uint64(len(val))); err != nil {
		panic(err)
	}
	payload.Write(val)
	payload.Write(aux)

	var rec bytes.Buffer
	for _, v := range []interface{}{seq, uint64(payload.Len())} {
		if err := binary.Write(&rec, binary.LittleEndian, v); err != nil {
			panic(err)
		}
	}
	rec.Write(payload.Bytes())
	return rec.Bytes()
}

// ssdPlainKey is a string key: db id, type 'a', then the name.
func ssdPlainKey(name string) []byte {
	return append([]byte{0, 0, 0, 0, 'a'}, name...)
}

// ssdItemKey is a collection key: db id, type, key name length, name, item.
func ssdItemKey(typ byte, name string, item []byte) []byte {
	key := append([]byte{0, 0, 0, 0, typ, 0, 0, 0, 0}, name...)
	binary.LittleEndian.PutUint32(key[5:9], uint32(len(name)))
	return append(key, item...)
}

// ssdAsyncDelKey is a version meta key: prefix MV, db id, type, then the name.
func ssdAsyncDelKey(typ byte, name string) []byte {
	return append([]byte{1, 0, 0, 0, 0, 0, typ}, name...)
}

func TestReadSSDBinlogDecodesRecordFields(t *testing.T) {
	key := ssdItemKey('h', "hash", []byte("field"))
	val := []byte("\x00binary\xff")
	aux := []byte{7, 0, 0, 0, 0, 0, 0, 0}
	stream := ssdRecordBytes(42, logHSET, 0, 0, 1700000000000, key, val, aux)

	got, err := readSSDBinlog(bytes.NewReader(stream), 0, 1<<62, func(rec *ssdBinlogRecord) error {
		if rec.seq != 42 || rec.logType != logHSET || rec.enc != 0 || rec.ts != 1700000000000 ||
			!bytes.Equal(rec.key, key) || !bytes.Equal(rec.val, val) || !bytes.Equal(rec.aux, aux) {
			t.Fatalf("record=%+v", rec)
		}
		return nil
	})
	if err != nil || got.records != 1 || got.firstSeq != 42 || got.lastSeq != 42 {
		t.Fatalf("stats=%+v err=%v", got, err)
	}
}

func TestReadSSDBinlogSkipsWholeRecordsBeforeStart(t *testing.T) {
	var stream []byte
	stream = append(stream, ssdRecordBytes(10, logKDEL, 0, 0, 1, ssdPlainKey("a"), nil, nil)...)
	stream = append(stream, ssdRecordBytes(11, logKDEL, 0, 0, 2, ssdPlainKey("b"), nil, nil)...)
	var seqs []int64
	got, err := readSSDBinlog(bytes.NewReader(stream), 11, 1<<62, func(rec *ssdBinlogRecord) error {
		seqs = append(seqs, rec.seq)
		return nil
	})
	if err != nil || len(seqs) != 1 || seqs[0] != 11 || got.firstSeq != 11 || got.lastSeq != 11 {
		t.Fatalf("seqs=%v stats=%+v err=%v", seqs, got, err)
	}
}

func TestReadSSDBinlogStopsAtTheFirstRecordPastTheWindow(t *testing.T) {
	var stream []byte
	stream = append(stream, ssdRecordBytes(10, logKDEL, 0, 0, 1000, ssdPlainKey("a"), nil, nil)...)
	stream = append(stream, ssdRecordBytes(11, logKDEL, 0, 0, 2000, ssdPlainKey("b"), nil, nil)...)
	stream = append(stream, ssdRecordBytes(12, logKDEL, 0, 0, 2001, ssdPlainKey("c"), nil, nil)...)
	var seqs []int64
	got, err := readSSDBinlog(bytes.NewReader(stream), 0, 2000, func(rec *ssdBinlogRecord) error {
		seqs = append(seqs, rec.seq)
		return nil
	})
	if err != nil || len(seqs) != 2 || seqs[0] != 10 || seqs[1] != 11 || !got.stoppedAtEnd {
		t.Fatalf("seqs=%v stats=%+v err=%v", seqs, got, err)
	}
}

func TestReadSSDBinlogFailsOnATruncatedTailWithItsSeq(t *testing.T) {
	good := ssdRecordBytes(10, logKDEL, 0, 0, 1, ssdPlainKey("a"), nil, nil)
	full := ssdRecordBytes(11, logKDEL, 0, 0, 2, ssdPlainKey("b"), []byte("value"), nil)
	cases := map[string]struct {
		stream []byte
		want   string
	}{
		"inside body":   {append(append([]byte{}, good...), full[:len(full)-3]...), "record at seq 11: file ends inside the record"},
		"inside length": {append(append([]byte{}, good...), full[:8+5]...), "record at seq 11: truncated length"},
		"inside seq":    {append(append([]byte{}, good...), full[:5]...), "record at seq 10: truncated header"},
	}
	for name, tc := range cases {
		if _, err := readSSDBinlog(bytes.NewReader(tc.stream), 0, 1<<62, func(*ssdBinlogRecord) error {
			return nil
		}); err == nil || !strings.Contains(err.Error(), tc.want) {
			t.Fatalf("%s: err=%v, want %q", name, err, tc.want)
		}
	}
}

func TestParseSSDRecordRejectsLengthsPastTheBody(t *testing.T) {
	body := ssdRecordBytes(1, logKDEL, 0, 0, 1, ssdPlainKey("a"), nil, nil)
	payload := body[16:]
	bad := append([]byte{}, payload...)
	binary.LittleEndian.PutUint64(bad[24:32], uint64(len(bad)))
	if _, err := parseSSDRecord(1, bad); err == nil || !strings.Contains(err.Error(), "key length") {
		t.Fatalf("err=%v", err)
	}
	bad = append([]byte{}, payload...)
	valLenOffset := 32 + len(ssdPlainKey("a"))
	binary.LittleEndian.PutUint64(bad[valLenOffset:valLenOffset+8], 1<<40)
	if _, err := parseSSDRecord(1, bad); err == nil || !strings.Contains(err.Error(), "value length") {
		t.Fatalf("err=%v", err)
	}
}

// ssdCommand builds a record and translates it.
func ssdCommand(t *testing.T, logType, enc int32, ttl, ts int64, key, val, aux []byte) ([]string, bool) {
	t.Helper()
	rec := &ssdBinlogRecord{logType: logType, enc: enc, ttl: ttl, ts: ts, key: key, val: val, aux: aux}
	args, skip, err := rec.command(100000)
	if err != nil {
		t.Fatalf("type %d: %v", logType, err)
	}
	return args, skip
}

func TestSSDRecordCommandsMatchBinlog2cmd(t *testing.T) {
	now := int64(100000)
	int64Bytes := func(v int64) []byte {
		b := make([]byte, 8)
		binary.LittleEndian.PutUint64(b, uint64(v))
		return b
	}
	listItem := int64Bytes(77)
	cases := map[string]struct {
		logType, enc  int32
		ttl, ts       int64
		key, val, aux []byte
		want          []string
		skip          bool
	}{
		"set":              {logType: logKSET, key: ssdPlainKey("k"), val: []byte("v"), want: []string{"set", "k", "v"}},
		"set empty value":  {logType: logKSET, key: ssdPlainKey("k"), want: []string{"set", "k", ""}},
		"set binary":       {logType: logKSET, key: ssdPlainKey("k"), val: []byte{0, 255, '\n'}, want: []string{"set", "k", "\x00\xff\n"}},
		"setex":            {logType: logKSET, ttl: now + 900000, key: ssdPlainKey("k"), val: []byte("v"), want: []string{"setex", "k", "900", "v"}},
		"setex int":        {logType: logKSET, enc: intEncoding, ttl: now + 1000, key: ssdPlainKey("k"), val: int64Bytes(-7), want: []string{"setex", "k", "1", "-7"}},
		"del":              {logType: logKDEL, key: ssdPlainKey("k"), want: []string{"del", "k"}},
		"lpush":            {logType: logLPUSH, key: ssdItemKey('l', "l", listItem), val: []byte("v"), want: []string{"lpush", "l", "v"}},
		"rpush int":        {logType: logRPUSH, enc: intEncoding, key: ssdItemKey('l', "l", listItem), val: int64Bytes(12), want: []string{"rpush", "l", "12"}},
		"lpop":             {logType: logLPOP, key: ssdItemKey('l', "l", listItem), want: []string{"lpop", "l"}},
		"rpop":             {logType: logRPOP, key: ssdItemKey('l', "l", listItem), want: []string{"rpop", "l"}},
		"lset":             {logType: logLSET, key: ssdItemKey('l', "l", listItem), val: []byte("v"), aux: int64Bytes(-2), want: []string{"lset", "l", "-2", "v"}},
		"hset":             {logType: logHSET, key: ssdItemKey('h', "h", []byte("f")), val: []byte("v"), want: []string{"hset", "h", "f", "v"}},
		"hset binary":      {logType: logHSET, key: ssdItemKey('h', "h", []byte("f")), val: []byte{0, 255}, want: []string{"hset", "h", "f", "\x00\xff"}},
		"hdel":             {logType: logHDEL, key: ssdItemKey('h', "h", []byte("f")), want: []string{"hdel", "h", "f"}},
		"sadd":             {logType: logSADD, key: ssdItemKey('s', "s", []byte("m")), want: []string{"sadd", "s", "m"}},
		"sadd int":         {logType: logSADD, enc: intEncoding, key: ssdItemKey('s', "s", int64Bytes(42)), want: []string{"sadd", "s", "42"}},
		"srem":             {logType: logSREM, key: ssdItemKey('s', "s", []byte("m")), want: []string{"srem", "s", "m"}},
		"zadd":             {logType: logZADD, key: ssdItemKey('z', "z", []byte("m")), val: int64Bytes(5), want: []string{"zadd", "z", "5", "m"}},
		"zadd negative":    {logType: logZADD, key: ssdItemKey('z', "z", []byte("m")), val: int64Bytes(-1), want: []string{"zadd", "z", "-1", "m"}},
		"zrem":             {logType: logZREM, key: ssdItemKey('z', "z", []byte("m")), want: []string{"zrem", "z", "m"}},
		"expire":           {logType: logEXPIRE, ttl: now + 2500, key: ssdPlainKey("k"), want: []string{"expire", "k", "2"}},
		"expire past":      {logType: logEXPIRE, ttl: now - 5000, key: ssdPlainKey("k"), want: []string{"expire", "k", "-5"}},
		"cas string":       {logType: logCAS, key: ssdPlainKey("k"), val: append([]byte("value"), int64Bytes(3)...), want: []string{"cas", "k", "value", "3"}},
		"cas empty string": {logType: logCAS, key: ssdPlainKey("k"), val: int64Bytes(9), want: []string{"cas", "k", "", "9"}},
		"cas hash size":    {logType: logCAS, key: append([]byte{0, 0, 0, 0, 'H'}, "h"...), val: append(int64Bytes(2), int64Bytes(7)...), want: []string{"cas", "h", "2", "7"}},
		"cas int":          {logType: logCAS, enc: intEncoding, key: ssdPlainKey("k"), val: int64Bytes(99), want: []string{"cas", "k", "99", "99"}},
		"asyncdel set":     {logType: logAsyncDel, key: ssdAsyncDelKey('s', "bigset"), want: []string{"del", "bigset"}},
		"asyncdel zset":    {logType: logAsyncDel, key: ssdAsyncDelKey('z', "bigzset"), want: []string{"del", "bigzset"}},
		"asyncdel zscore":  {logType: logAsyncDel, key: ssdAsyncDelKey('c', "bigzset"), skip: true},
		"syncvsn":          {logType: logSyncVsn, skip: true},
		"rclvsn":           {logType: logRclVsn, skip: true},
	}
	for name, tc := range cases {
		ts := tc.ts
		if ts == 0 {
			ts = now
		}
		args, skip := ssdCommand(t, tc.logType, tc.enc, tc.ttl, ts, tc.key, tc.val, tc.aux)
		if skip != tc.skip || (skip && args != nil) {
			t.Fatalf("%s: skip=%v args=%q", name, skip, args)
		}
		if !skip && !reflect.DeepEqual(args, tc.want) {
			t.Fatalf("%s: got %q, want %q", name, args, tc.want)
		}
	}
}

func TestSSDRecordCommandRejectsUnknownTypesAndShortFields(t *testing.T) {
	cases := map[string]struct {
		logType int32
		key     []byte
		val     []byte
		want    string
	}{
		"type 14":        {14, ssdPlainKey("k"), nil, "unknown binlog type 14"},
		"type 20":        {20, ssdPlainKey("k"), nil, "unknown binlog type 20"},
		"short key":      {logKDEL, []byte{1, 2}, nil, "too short"},
		"lset no index":  {logLSET, ssdItemKey('l', "l", []byte("i")), []byte("v"), "without its list index"},
		"short name len": {logHSET, []byte{0, 0, 0, 0, 'h', 5, 0, 0, 0, 'a'}, nil, "runs past"},
	}
	for name, tc := range cases {
		rec := &ssdBinlogRecord{logType: tc.logType, key: tc.key, val: tc.val}
		if _, _, err := rec.command(0); err == nil || !strings.Contains(err.Error(), tc.want) {
			t.Fatalf("%s: err=%v, want %q", name, err, tc.want)
		}
	}
}

func TestSSDWindowHidesUnknownTypesOutsideIt(t *testing.T) {
	unknown := func(seq, ts int64) []byte {
		return ssdRecordBytes(seq, 15, 0, 0, ts, ssdPlainKey("k"), nil, nil)
	}
	decode := func(stream []byte, start uint64, endMs int64) error {
		_, err := readSSDBinlog(bytes.NewReader(stream), start, endMs, func(rec *ssdBinlogRecord) error {
			_, _, err := rec.command(100000)
			return err
		})
		return err
	}
	// Before the start seq: skipped before the type is looked at.
	if err := decode(unknown(10, 1000), 11, 1<<62); err != nil {
		t.Fatalf("before start: %v", err)
	}
	// Later than the window: the stream stops before the type is looked at.
	if err := decode(unknown(11, 2001), 0, 2000); err != nil {
		t.Fatalf("past the end: %v", err)
	}
	// Inside the window: the unknown type fails the port with its seq.
	stream := append(ssdRecordBytes(11, logKDEL, 0, 0, 2000, ssdPlainKey("a"), nil, nil), unknown(12, 2001)...)
	if err := decode(stream, 0, 3000); err == nil || !strings.Contains(err.Error(), "unknown binlog type 15") {
		t.Fatalf("inside the window: %v", err)
	}
}

// gzipSample writes records into a downloaded binlog name; gzip keeps the test independent of
// the zstd binary path the hosts use.
func gzipSample(t *testing.T, records ...[]byte) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "binlog-1.1.1.1-30000-0000010-20260101000000.log.gz")
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	w := gzip.NewWriter(f)
	for _, rec := range records {
		if _, err = w.Write(rec); err != nil {
			t.Fatal(err)
		}
	}
	if err = w.Close(); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestDecodeSSDFileStreamsTheReplaySequence(t *testing.T) {
	now := int64(100000)
	records := [][]byte{
		ssdRecordBytes(100, logKSET, 0, 0, 1000, ssdPlainKey("k1"), []byte("v1"), nil),
		ssdRecordBytes(101, logHSET, 0, 0, 1000, ssdItemKey('h', "h", []byte("f")), []byte("v"), nil),
		ssdRecordBytes(102, logZADD, 0, 0, 1000, ssdItemKey('z', "z", []byte("m")), make([]byte, 8), nil),
		// Del path: the del record comes first, the asyncdel repeats it, harmlessly.
		ssdRecordBytes(103, logKDEL, 0, 0, 1000, ssdPlainKey("bigset"), nil, nil),
		ssdRecordBytes(104, logAsyncDel, 0, 0, 1000, ssdAsyncDelKey('s', "bigset"), nil, nil),
		// Store path: an in-place store replaced the data, so the asyncdel is the only del.
		ssdRecordBytes(105, logAsyncDel, 0, 0, 1000, ssdAsyncDelKey('z', "bigzset"), nil, nil),
		// The zset version record would delete the same key a second time.
		ssdRecordBytes(106, logAsyncDel, 0, 0, 1000, ssdAsyncDelKey('c', "bigzset"), nil, nil),
		ssdRecordBytes(107, logSyncVsn, 0, 0, 1000, ssdPlainKey("k1"), nil, nil),
		ssdRecordBytes(108, logKDEL, 0, 0, 1000, ssdPlainKey("k1"), nil, nil),
	}
	var commands [][]string
	stats, _, err := decodeSSDFile(gzipSample(t, records...), 100, 2000, func(rec *ssdBinlogRecord) error {
		args, skip, err := rec.command(now)
		if err != nil {
			return err
		}
		if !skip {
			commands = append(commands, args)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	want := [][]string{{"set", "k1", "v1"}, {"hset", "h", "f", "v"}, {"zadd", "z", "0", "m"},
		{"del", "bigset"}, {"del", "bigset"}, {"del", "bigzset"}, {"del", "k1"}}
	if !reflect.DeepEqual(commands, want) {
		t.Fatalf("commands=%q, want %q", commands, want)
	}
	if stats.records != 9 || stats.firstSeq != 100 || stats.lastSeq != 108 {
		t.Fatalf("stats=%+v", stats)
	}
}

func TestDecodeSSDFileFailsOnATruncatedDownload(t *testing.T) {
	good := ssdRecordBytes(100, logKDEL, 0, 0, 1000, ssdPlainKey("k1"), nil, nil)
	bad := ssdRecordBytes(101, logKDEL, 0, 0, 1000, ssdPlainKey("k2"), nil, nil)
	if _, _, err := decodeSSDFile(gzipSample(t, good, bad[:len(bad)-2]), 0, 1<<62,
		func(*ssdBinlogRecord) error { return nil }); err == nil ||
		!strings.Contains(err.Error(), "seq 101") {
		t.Fatalf("err=%v", err)
	}
}

// useLocalZstd points the decoder at a PATH zstd when the host's dbtools copy is absent, so the
// corpus tests run off the target hosts too.
func useLocalZstd(t *testing.T) {
	t.Helper()
	if _, err := os.Stat(ssdZstdBin); err == nil {
		return
	}
	bin, err := exec.LookPath("zstd")
	if err != nil {
		t.Skipf("no zstd: %v", err)
	}
	old := ssdZstdBin
	ssdZstdBin = bin
	t.Cleanup(func() { ssdZstdBin = old })
}

// TestSSDCorpusDecodesWithoutErrors runs the decoder over a local corpus. Point
// SSD_BINLOG_CORPUS_DIR at a directory of downloaded binlogs (bench files, ticket 2571128
// samples); the files stay out of the repository.
func TestSSDCorpusDecodesWithoutErrors(t *testing.T) {
	dir := os.Getenv("SSD_BINLOG_CORPUS_DIR")
	if dir == "" {
		t.Skip("set SSD_BINLOG_CORPUS_DIR to a directory of binlogs to decode")
	}
	useLocalZstd(t)
	paths, err := filepath.Glob(filepath.Join(dir, "*.log.*"))
	if err != nil || len(paths) == 0 {
		t.Fatalf("no binlogs in %s: %v", dir, err)
	}
	for _, path := range paths {
		path := path
		t.Run(filepath.Base(path), func(t *testing.T) {
			var commands, args, skipped int
			stats, _, err := decodeSSDFile(path, 0, 1<<62, func(rec *ssdBinlogRecord) error {
				recArgs, skip, err := rec.command(time.Now().UnixMilli())
				if err != nil {
					return err
				}
				if skip {
					skipped++
				} else {
					commands++
					args += len(recArgs)
				}
				return nil
			})
			if err != nil {
				t.Fatal(err)
			}
			if stats.records == 0 || commands == 0 {
				t.Fatalf("stats=%+v commands=%d skipped=%d", stats, commands, skipped)
			}
			t.Logf("records=%d commands=%d args=%d skipped=%d seq %d..%d", stats.records, commands,
				args, skipped, stats.firstSeq, stats.lastSeq)
		})
	}
}

// TestSSDDecoderMatchesTredisbinlog compares the native decoder with tredisbinlog on a local
// corpus. Point SSD_BINLOG_CORPUS_DIR at a directory of downloaded binlogs (bench files, ticket
// 2571128 samples); the files stay out of the repository.
func TestSSDDecoderMatchesTredisbinlog(t *testing.T) {
	dir := os.Getenv("SSD_BINLOG_CORPUS_DIR")
	if dir == "" {
		t.Skip("set SSD_BINLOG_CORPUS_DIR to a directory of binlogs to compare against tredisbinlog")
	}
	if _, err := os.Stat(consts.TredisBinlogBin); err != nil {
		t.Skipf("tredisbinlog not found: %v", err)
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		if entry.IsDir() || !strings.Contains(entry.Name(), ".log") {
			continue
		}
		t.Run(entry.Name(), func(t *testing.T) {
			path := filepath.Join(dir, entry.Name())
			want := tredisbinlogCommands(t, path)
			var got [][]string
			if _, _, err := decodeSSDFile(path, 0, 1<<62, func(rec *ssdBinlogRecord) error {
				if rec.logType == logAsyncDel || rec.logType == logSyncVsn || rec.logType == logRclVsn {
					return nil
				}
				args, _, err := rec.command(time.Now().UnixMilli())
				if err != nil {
					return err
				}
				got = append(got, args)
				return nil
			}); err != nil {
				t.Fatal(err)
			}
			compareCommands(t, got, want)
		})
	}
}

// tredisbinlogCommands decompresses a binlog and returns the commands tredisbinlog prints for
// it. Lines it fails to translate are skipped; the native decoder is checked against those
// cases separately.
func tredisbinlogCommands(t *testing.T, path string) [][]string {
	t.Helper()
	s, err := openSSDStream(path)
	if err != nil {
		t.Fatal(err)
	}
	plain := filepath.Join(t.TempDir(), "binlog.log")
	out, err := os.Create(plain)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = io.Copy(out, s); err != nil {
		t.Fatal(err)
	}
	_ = out.Close()
	if _, err = s.finish(false); err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(consts.TredisBinlogBin, "--start-position=0", plain)
	cmd.Env = append(os.Environ(), ssdToolEnv()...)
	raw, err := cmd.Output()
	if err != nil {
		t.Fatal(err)
	}
	var commands [][]string
	for _, line := range strings.Split(string(raw), "\n") {
		if line == "" || strings.HasPrefix(line, "Wrong log type") || strings.HasPrefix(line, "failed") {
			continue
		}
		args, ok := splitArgs(line)
		if !ok {
			t.Fatalf("tredisbinlog printed a line redis-cli cannot split: %q", line)
		}
		commands = append(commands, args)
	}
	return commands
}

// compareCommands allows the ttl of setex and expire to drift between the two runs; every other
// argument must match exactly.
func compareCommands(t *testing.T, got, want [][]string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%d commands, tredisbinlog printed %d", len(got), len(want))
	}
	for i := range want {
		if len(got[i]) != len(want[i]) {
			t.Fatalf("command %d: %q, want %q", i, got[i], want[i])
		}
		for j := range want[i] {
			if got[i][j] == want[i][j] {
				continue
			}
			if j == 2 && (want[i][0] == "setex" || want[i][0] == "expire") && ttlClose(got[i][j], want[i][j]) {
				continue
			}
			t.Fatalf("command %d: %q, want %q", i, got[i], want[i])
		}
	}
}

func ttlClose(a, b string) bool {
	av, aerr := strconv.ParseInt(a, 10, 64)
	bv, berr := strconv.ParseInt(b, 10, 64)
	if aerr != nil || berr != nil {
		return false
	}
	const drift = 10
	return av-bv <= drift && bv-av <= drift
}
