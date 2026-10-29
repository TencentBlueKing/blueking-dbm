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
	"bytes"
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// A tendisssd binlog file is a sequence of records, each written by encLogVal as
// seq int64 | loglen uint64 | payload, where payload holds the fields tendisssd's initBinLog
// reads in order: logtype int32 | enc int32 | ttl int64 | ts int64 | keylen uint64 | key |
// vallen uint64 | val | aux. Reading the records natively replaces tredisbinlog, whose
// sdscatrepr output spent about 75% of its CPU formatting bytes one at a time.
const (
	maxSSDBinlogRecord = 1 << 30
	// rawKeyOffset skips the db id, an optional version injected over it, and the type byte.
	rawKeyOffset = 4 + 1
	// itemKeySize is the int32 key name length in front of a collection key's name.
	itemKeySize = 4
	// asyncDelKeyOffset skips the version meta key's prefix, db id and type.
	asyncDelKeyOffset = 4 + 2 + 1
	// intEncoding is REDIS_ENCODING_INT: the value is stored as a long instead of bytes.
	intEncoding = 1
)

// tendisssd binlog types, from its sync.h enum LogType.
const (
	logKSET int32 = iota
	logKDEL
	logLPUSH
	logRPUSH
	logLPOP
	logRPOP
	logLSET
	logHSET
	logHDEL
	logSADD
	logSREM
	logZADD
	logZREM
	logEXPIRE
	// 14 and 15 are not assigned.
	logCAS      int32 = 16
	logAsyncDel int32 = 17
	logSyncVsn  int32 = 18
	logRclVsn   int32 = 19
)

// ssdBinlogRecord is one decoded record; its slices point into the record buffer.
type ssdBinlogRecord struct {
	seq     int64
	logType int32
	enc     int32
	ttl     int64
	ts      int64
	key     []byte
	val     []byte
	aux     []byte
}

// ssdDecodeStats is what one stream held.
type ssdDecodeStats struct {
	records      int
	firstSeq     int64
	lastSeq      int64
	readTime     time.Duration
	stoppedAtEnd bool
}

// readSSDBinlog streams records from r and hands each one in the replay window to onRecord.
// Records before startSeq are skipped, and the first record later than endMs ends the stream.
// Both checks come before a record's type is looked at, so unknown types outside the window
// never fail a port.
func readSSDBinlog(r io.Reader, startSeq uint64, endMs int64, onRecord func(*ssdBinlogRecord) error) (
	ssdDecodeStats, error) {
	var st ssdDecodeStats
	timer := &readTimer{r: r}
	br := bufio.NewReaderSize(timer, 1<<20)
	var lastSeq int64
	for {
		var seq int64
		if err := binary.Read(br, binary.LittleEndian, &seq); err != nil {
			if err == io.EOF {
				st.readTime = timer.d
				return st, nil
			}
			return st, fmt.Errorf("record at seq %d: truncated header: %v", lastSeq, err)
		}
		lastSeq = seq
		var length uint64
		if err := binary.Read(br, binary.LittleEndian, &length); err != nil {
			return st, fmt.Errorf("record at seq %d: truncated length: %v", seq, err)
		}
		if length > maxSSDBinlogRecord {
			return st, fmt.Errorf("record at seq %d: implausible length %d", seq, length)
		}
		buf := make([]byte, length)
		if n, err := io.ReadFull(br, buf); err != nil {
			return st, fmt.Errorf("record at seq %d: file ends inside the record, %d of %d bytes",
				seq, n, length)
		}
		rec, err := parseSSDRecord(seq, buf)
		if err != nil {
			return st, fmt.Errorf("record at seq %d: %v", seq, err)
		}
		if seq < int64(startSeq) {
			continue
		}
		if rec.ts > endMs {
			st.stoppedAtEnd = true
			st.readTime = timer.d
			return st, nil
		}
		if st.records == 0 {
			st.firstSeq = seq
		}
		st.lastSeq = seq
		st.records++
		if err = onRecord(rec); err != nil {
			st.readTime = timer.d
			return st, err
		}
	}
}

// readTimer accumulates the time spent blocked on the decompressor.
type readTimer struct {
	r io.Reader
	d time.Duration
}

func (t *readTimer) Read(p []byte) (int, error) {
	start := time.Now()
	n, err := t.r.Read(p)
	t.d += time.Since(start)
	return n, err
}

// command turns a record into the command tredisbinlog prints for it, one argument at a time.
// skip is true for version metadata, which carries no write. nowMs is when the command is
// built: tendisssd stores an absolute expiry and binlog2cmd rebases it to the replay time.
func (rec *ssdBinlogRecord) command(nowMs int64) (args []string, skip bool, err error) {
	switch rec.logType {
	case logKSET:
		name, err := rec.plainName()
		if err != nil {
			return nil, false, err
		}
		val, err := rec.value()
		if err != nil {
			return nil, false, err
		}
		if rec.ttl == 0 {
			return []string{"set", string(name), val}, false, nil
		}
		return []string{"setex", string(name), strconv.FormatInt(rec.ttlSeconds(nowMs), 10), val}, false, nil
	case logKDEL:
		name, err := rec.plainName()
		if err != nil {
			return nil, false, err
		}
		return []string{"del", string(name)}, false, nil
	case logLPUSH, logRPUSH:
		name, _, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		val, err := rec.value()
		if err != nil {
			return nil, false, err
		}
		cmd := "lpush"
		if rec.logType == logRPUSH {
			cmd = "rpush"
		}
		return []string{cmd, string(name), val}, false, nil
	case logLPOP, logRPOP:
		name, _, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		cmd := "lpop"
		if rec.logType == logRPOP {
			cmd = "rpop"
		}
		return []string{cmd, string(name)}, false, nil
	case logLSET:
		name, _, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		if len(rec.aux) < 8 {
			return nil, false, fmt.Errorf("lset without its list index")
		}
		val, err := rec.value()
		if err != nil {
			return nil, false, err
		}
		index := int64(binary.LittleEndian.Uint64(rec.aux[:8]))
		return []string{"lset", string(name), strconv.FormatInt(index, 10), val}, false, nil
	case logHSET:
		name, field, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		val, err := rec.value()
		if err != nil {
			return nil, false, err
		}
		return []string{"hset", string(name), string(field), val}, false, nil
	case logHDEL:
		name, field, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		return []string{"hdel", string(name), string(field)}, false, nil
	case logSADD, logSREM:
		name, member, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		arg := string(member)
		if rec.enc == intEncoding {
			// An intset member is written in the key as a long instead of bytes.
			if len(member) < 8 {
				return nil, false, fmt.Errorf("integer set member of %d bytes", len(member))
			}
			arg = strconv.FormatInt(int64(binary.LittleEndian.Uint64(member[:8])), 10)
		}
		cmd := "sadd"
		if rec.logType == logSREM {
			cmd = "srem"
		}
		return []string{cmd, string(name), arg}, false, nil
	case logZADD:
		name, member, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		if len(rec.val) < 8 {
			return nil, false, fmt.Errorf("zadd without its score")
		}
		score := int64(binary.LittleEndian.Uint64(rec.val[:8]))
		return []string{"zadd", string(name), strconv.FormatInt(score, 10), string(member)}, false, nil
	case logZREM:
		name, member, err := rec.itemName()
		if err != nil {
			return nil, false, err
		}
		return []string{"zrem", string(name), string(member)}, false, nil
	case logEXPIRE:
		name, err := rec.plainName()
		if err != nil {
			return nil, false, err
		}
		return []string{"expire", string(name), strconv.FormatInt(rec.ttlSeconds(nowMs), 10)}, false, nil
	case logCAS:
		args, err := rec.casCommand()
		return args, false, err
	case logAsyncDel:
		// The key is a version meta key; deleting it removes every element of the key.
		if len(rec.key) < asyncDelKeyOffset {
			return nil, false, fmt.Errorf("async del key of %d bytes is too short", len(rec.key))
		}
		if rec.key[6] == 'c' {
			// The matching zset record already sends the del.
			return nil, true, nil
		}
		return []string{"del", string(rec.key[asyncDelKeyOffset:])}, false, nil
	case logSyncVsn, logRclVsn:
		return nil, true, nil
	default:
		return nil, false, fmt.Errorf("unknown binlog type %d", rec.logType)
	}
}

// casCommand mirrors binlog2cmd's cas, whose value depends on the key type: a string carries the
// value, a hash size carries its element count, and both end with the version.
func (rec *ssdBinlogRecord) casCommand() ([]string, error) {
	name, err := rec.plainName()
	if err != nil {
		return nil, err
	}
	args := []string{"cas", string(name)}
	keyType := byte(0)
	if len(rec.key) > 4 {
		keyType = rec.key[4]
	}
	switch {
	case rec.enc == intEncoding:
		val, err := rec.intValue()
		if err != nil {
			return nil, err
		}
		args = append(args, strconv.FormatInt(val, 10))
	case keyType == 'H':
		if len(rec.val) < 8 {
			return nil, fmt.Errorf("hash cas without its size")
		}
		args = append(args, strconv.FormatInt(int64(binary.LittleEndian.Uint64(rec.val[:8])), 10))
	case keyType == 'a':
		if len(rec.val) < 8 {
			return nil, fmt.Errorf("string cas without its version")
		}
		args = append(args, string(rec.val[:len(rec.val)-8]))
	}
	if len(rec.val) < 8 {
		return nil, fmt.Errorf("cas value of %d bytes has no version", len(rec.val))
	}
	vsn := int64(binary.LittleEndian.Uint64(rec.val[len(rec.val)-8:]))
	return append(args, strconv.FormatInt(vsn, 10)), nil
}

// plainName is the key name of a string key, or of a cas key.
func (rec *ssdBinlogRecord) plainName() ([]byte, error) {
	if len(rec.key) < rawKeyOffset {
		return nil, fmt.Errorf("key of %d bytes is too short", len(rec.key))
	}
	return rec.key[rawKeyOffset:], nil
}

// itemName splits a collection key into its name and the member stored after it.
func (rec *ssdBinlogRecord) itemName() (name, item []byte, err error) {
	if len(rec.key) < rawKeyOffset+itemKeySize {
		return nil, nil, fmt.Errorf("collection key of %d bytes is too short", len(rec.key))
	}
	n := int32(binary.LittleEndian.Uint32(rec.key[rawKeyOffset : rawKeyOffset+itemKeySize]))
	start := rawKeyOffset + itemKeySize
	if n < 0 || int(n) > len(rec.key)-start {
		return nil, nil, fmt.Errorf("key name length %d runs past the %d-byte key", n, len(rec.key))
	}
	return rec.key[start : start+int(n)], rec.key[start+int(n):], nil
}

// value is the record's value as a command argument. Integer-encoded values are stored as a long.
func (rec *ssdBinlogRecord) value() (string, error) {
	if rec.enc != intEncoding {
		return string(rec.val), nil
	}
	v, err := rec.intValue()
	if err != nil {
		return "", err
	}
	return strconv.FormatInt(v, 10), nil
}

func (rec *ssdBinlogRecord) intValue() (int64, error) {
	if len(rec.val) == 0 {
		return 0, nil
	}
	if len(rec.val) < 8 {
		return 0, fmt.Errorf("integer value of %d bytes", len(rec.val))
	}
	return int64(binary.LittleEndian.Uint64(rec.val[:8])), nil
}

// ttlSeconds is a stored absolute expiry rebased to the replay time and truncated to seconds,
// as tredisbinlog does before printing setex and expire.
func (rec *ssdBinlogRecord) ttlSeconds(nowMs int64) int64 {
	ttl := rec.ttl
	if ttl != -1 && ttl != 0 {
		ttl -= nowMs
	}
	return ttl / 1000
}

// parseSSDRecord splits one record body into its fields.
func parseSSDRecord(seq int64, buf []byte) (*ssdBinlogRecord, error) {
	const header = 4 + 4 + 8 + 8 + 8 // logtype, enc, ttl, ts, keylen
	if len(buf) < header {
		return nil, fmt.Errorf("body of %d bytes is shorter than the %d-byte header", len(buf), header)
	}
	rec := &ssdBinlogRecord{
		seq:     seq,
		logType: int32(binary.LittleEndian.Uint32(buf[0:4])),
		enc:     int32(binary.LittleEndian.Uint32(buf[4:8])),
		ttl:     int64(binary.LittleEndian.Uint64(buf[8:16])),
		ts:      int64(binary.LittleEndian.Uint64(buf[16:24])),
	}
	keyLen := binary.LittleEndian.Uint64(buf[24:32])
	pos := header
	if keyLen > uint64(len(buf)-pos) {
		return nil, fmt.Errorf("key length %d runs past the %d-byte body", keyLen, len(buf))
	}
	rec.key = buf[pos : pos+int(keyLen)]
	pos += int(keyLen)
	if len(buf)-pos < 8 {
		return nil, fmt.Errorf("no value length after the key")
	}
	valLen := binary.LittleEndian.Uint64(buf[pos : pos+8])
	pos += 8
	if valLen > uint64(len(buf)-pos) {
		return nil, fmt.Errorf("value length %d runs past the %d-byte body", valLen, len(buf))
	}
	if valLen > 0 {
		rec.val = buf[pos : pos+int(valLen)]
		pos += int(valLen)
	}
	rec.aux = buf[pos:]
	return rec, nil
}

// ssdStream is a decompressed binlog stream and the decompressor feeding it.
type ssdStream struct {
	io.ReadCloser
	cmd    *exec.Cmd
	cancel context.CancelFunc
	stderr bytes.Buffer
}

// ssdZstdBin and ssdLzopBin are the dbtools decompressors; tests point them at local copies.
var (
	ssdZstdBin = consts.ZstdBin
	ssdLzopBin = consts.LzopBin
)

// openSSDStream opens a downloaded binlog for streaming. Modern downloads are zstd; the legacy
// suffixes the download path accepts open too.
func openSSDStream(path string) (*ssdStream, error) {
	var bin string
	switch {
	case strings.HasSuffix(path, ".zst"):
		bin = ssdZstdBin
	case strings.HasSuffix(path, ".gz"):
		bin = "gzip"
	case strings.HasSuffix(path, ".lzo"):
		bin = ssdLzopBin
	default:
		f, err := os.Open(path)
		if err != nil {
			return nil, err
		}
		return &ssdStream{ReadCloser: f}, nil
	}
	if filepath.IsAbs(bin) {
		if _, err := os.Stat(bin); err != nil {
			return nil, fmt.Errorf("%s not found: %s", filepath.Base(bin), bin)
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), ssdCmdTimeout)
	cmd := exec.CommandContext(ctx, bin, "-dc", path)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		cancel()
		return nil, err
	}
	s := &ssdStream{ReadCloser: stdout, cmd: cmd, cancel: cancel}
	cmd.Stderr = &s.stderr
	if err = cmd.Start(); err != nil {
		cancel()
		return nil, err
	}
	return s, nil
}

// finish closes the stream and waits for the decompressor. stoppedShort means the reader did
// not consume the whole stream, so a killed decompressor is expected. It returns the CPU time
// the decompressor used.
func (s *ssdStream) finish(stoppedShort bool) (time.Duration, error) {
	if s.cmd == nil {
		return 0, s.ReadCloser.Close()
	}
	_ = s.ReadCloser.Close()
	if stoppedShort {
		// The reader has what it needs; kill the decompressor instead of draining it.
		s.cancel()
	}
	err := s.cmd.Wait()
	s.cancel()
	cpu := cpuTime(s.cmd)
	if stoppedShort {
		return cpu, nil
	}
	if err != nil {
		return cpu, fmt.Errorf("%s failed: %v %s", filepath.Base(s.cmd.Path), err,
			strings.TrimSpace(s.stderr.String()))
	}
	return cpu, nil
}

// decodeSSDFile streams one downloaded binlog and returns what it held. The CPU time is the
// decompressor's, separate from the time the Go side spent decoding.
func decodeSSDFile(path string, startSeq uint64, endMs int64, onRecord func(*ssdBinlogRecord) error) (
	ssdDecodeStats, time.Duration, error) {
	s, err := openSSDStream(path)
	if err != nil {
		return ssdDecodeStats{}, 0, err
	}
	stats, readErr := readSSDBinlog(s, startSeq, endMs, onRecord)
	cpu, closeErr := s.finish(stats.stoppedAtEnd || readErr != nil)
	if readErr != nil {
		if closeErr != nil {
			readErr = fmt.Errorf("%v (%v)", readErr, closeErr)
		}
		return stats, cpu, readErr
	}
	if closeErr != nil {
		return stats, cpu, closeErr
	}
	return stats, cpu, nil
}
