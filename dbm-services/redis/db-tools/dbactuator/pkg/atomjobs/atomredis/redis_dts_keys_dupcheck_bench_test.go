package atomredis

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"testing"
	"time"
)

// 大文件压测,默认跳过: DUPCHECK_BENCH=1 go test -vet=off -run TestDupCheckLarge -v
func TestDupCheckLarge(t *testing.T) {
	if os.Getenv("DUPCHECK_BENCH") == "" {
		t.Skip("set DUPCHECK_BENCH=1 to run")
	}
	dir := t.TempDir()
	f := filepath.Join(dir, "big.keys")
	const lines = 20_000_000
	fh, _ := os.Create(f)
	w := bufio.NewWriterSize(fh, 1<<20)
	for i := 0; i < lines; i++ {
		fmt.Fprintf(w, "dts:test:key:%012d:suffix_abcdefghij\n", i)
	}
	// 在文件头尾各制造一个重复行
	fmt.Fprintf(w, "dts:test:key:%012d:suffix_abcdefghij\n", 0)
	fmt.Fprintf(w, "dts:test:key:%012d:suffix_abcdefghij\n", lines-1)
	w.Flush()
	fh.Close()
	st, _ := os.Stat(f)
	t.Logf("file size:%dMB", st.Size()>>20)

	var peak uint64
	stop := make(chan struct{})
	go func() {
		var m runtime.MemStats
		for {
			select {
			case <-stop:
				return
			case <-time.After(100 * time.Millisecond):
				runtime.ReadMemStats(&m)
				if m.HeapAlloc > peak {
					peak = m.HeapAlloc
				}
			}
		}
	}()
	start := time.Now()
	ret, err := checkKeysFileDuplicates(f, dir, keysDupCheckShardBytes, keysDupCheckMaxShards, noLog)
	close(stop)
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("cost:%v,peakHeap:%dMB,ret:%+v", time.Since(start), peak>>20, ret)
	if ret.DupKeys != 2 || ret.DupLines != 2 || ret.TotalLines != lines+2 {
		t.Fatalf("unexpected:%+v", ret)
	}
}
