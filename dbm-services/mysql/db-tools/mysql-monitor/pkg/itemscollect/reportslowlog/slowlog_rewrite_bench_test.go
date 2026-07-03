package reportslowlog

import (
	"bufio"
	"bytes"
	"io"
	"os"
	"path/filepath"
	"testing"
)

func processSampleForBenchmark(b *testing.B, r *SlowlogReport, inputData []byte, reformat bool) {
	reader := bytes.NewReader(inputData)
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 64*1024), 100*1024*1024)

	var segReady bool
	var inSegment bool
	for scanner.Scan() {
		rawLine := scanner.Bytes()
		line := bytes.TrimSpace(rawLine)

		if segReady && isSegmentStartLine(line) {
			if reformat {
				if err := r.ReformatSegToWriter(); err != nil {
					b.Fatal(err)
				}
			} else {
				if err := r.rewriteSeg(); err != nil {
					b.Fatal(err)
				}
			}
			r.resetSeg()
			segReady = false
			inSegment = false
		}

		if !inSegment {
			if isSkippableSlowlogHeaderLine(line) || isBlankLine(line) {
				continue
			}
		}

		if isSegmentStartLine(line) {
			inSegment = true
		}

		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, rawLine...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(rawLine)})
		r.parseLine(line)
		firstByte := firstNonSpaceByte(rawLine)
		if r.firstBodyLineIdx < 0 && firstByte != 0 && firstByte != '#' {
			r.firstBodyLineIdx = len(r.segRanges) - 1
		}
		if !isBlankLine(rawLine) {
			segReady = lineEndsWithSemicolon(rawLine)
		}
	}
	if err := scanner.Err(); err != nil {
		b.Fatal(err)
	}
	if len(r.segRanges) > 0 && segReady {
		if reformat {
			if err := r.ReformatSegToWriter(); err != nil {
				b.Fatal(err)
			}
		} else {
			if err := r.rewriteSeg(); err != nil {
				b.Fatal(err)
			}
		}
	}
	if err := r.writer.Flush(); err != nil {
		b.Fatal(err)
	}
	r.writer.Reset(io.Discard)
	r.writtenBytes = 0
	r.resetSeg()
}

func benchmarkProcessSample(b *testing.B, reformat bool) {
	inputData, err := os.ReadFile(filepath.Join(".", "slow-query-test.txt"))
	if err != nil {
		b.Fatal(err)
	}

	r := &SlowlogReport{
		writer:           bufio.NewWriterSize(io.Discard, 256*1024),
		segBuf:           make([]byte, 0, 64*1024),
		firstBodyLineIdx: -1,
	}

	b.ReportAllocs()
	b.SetBytes(int64(len(inputData)))
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		processSampleForBenchmark(b, r, inputData, reformat)
	}
}

func BenchmarkProcessSampleRewrite(b *testing.B) {
	benchmarkProcessSample(b, false)
}

func BenchmarkProcessSampleReformat(b *testing.B) {
	benchmarkProcessSample(b, true)
}

func loadBenchSegment() [][]byte {
	return [][]byte{
		[]byte("# Time: 2026-07-02T00:00:20.581596+08:00"),
		[]byte("# User@Host: user3[user3] @  [1.2.3.4]  Id: 622265227"),
		[]byte("# Schema: dbtest3  Last_errno: 0  Killed: 0"),
		[]byte("# Query_time: 17.501662  Lock_time: 0.000423  Rows_sent: 12  Rows_examined: 49798517"),
		[]byte("use dbtest3;"),
		[]byte("SET timestamp=1782921620;"),
		[]byte("select * from users where id = 1;"),
	}
}

func prepareBenchReport(lines [][]byte) *SlowlogReport {
	r := &SlowlogReport{
		writer:           bufio.NewWriterSize(io.Discard, 64*1024),
		segBuf:           make([]byte, 0, 64*1024),
		firstBodyLineIdx: -1,
	}
	for _, line := range lines {
		start := len(r.segBuf)
		r.segBuf = append(r.segBuf, line...)
		r.segRanges = append(r.segRanges, lineRange{offset: start, length: len(line)})
		r.parseLine(line)
		if r.firstBodyLineIdx < 0 && len(line) > 0 && line[0] != '#' {
			r.firstBodyLineIdx = len(r.segRanges) - 1
		}
	}
	return r
}

func BenchmarkParseLineSegment(b *testing.B) {
	lines := loadBenchSegment()
	r := &SlowlogReport{}

	b.ReportAllocs()
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		r.segF = segFields{}
		for _, line := range lines {
			r.parseLine(line)
		}
	}
}

func BenchmarkRewriteSegSingle(b *testing.B) {
	lines := loadBenchSegment()
	r := prepareBenchReport(lines)

	b.ReportAllocs()
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		if err := r.rewriteSeg(); err != nil {
			b.Fatal(err)
		}
		r.writer.Reset(io.Discard)
		r.writtenBytes = 0
	}
}

func BenchmarkReformatSegSingle(b *testing.B) {
	lines := loadBenchSegment()
	r := prepareBenchReport(lines)

	b.ReportAllocs()
	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		if _, err := r.ReformatSeg(); err != nil {
			b.Fatal(err)
		}
	}
}
