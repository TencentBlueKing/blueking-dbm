/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package process

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestTryFileLock_Contention(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "probe.ensure.lock")

	fl1, held, err := TryFileLock(path)
	if err != nil {
		t.Fatalf("first lock: %v", err)
	}
	if !held {
		t.Fatal("expected first lock held")
	}
	defer fl1.Unlock()

	fl2, held2, err := TryFileLock(path)
	if err != nil {
		t.Fatalf("second lock: %v", err)
	}
	if held2 {
		_ = fl2.Unlock()
		t.Fatal("expected second lock to fail (contention)")
	}
}

func TestAcquireFileLock_TimeoutAndRelease(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "probe.acquire.lock")

	held, err := AcquireFileLock(path, time.Second)
	if err != nil {
		t.Fatalf("first acquire: %v", err)
	}

	if _, err := AcquireFileLock(path, 200*time.Millisecond); err == nil {
		t.Fatal("expected timeout while the lock is held")
	}

	// Releasing must let the next waiter in well within its own timeout.
	go func() {
		time.Sleep(100 * time.Millisecond)
		_ = held.Unlock()
	}()

	second, err := AcquireFileLock(path, 3*time.Second)
	if err != nil {
		t.Fatalf("acquire after release: %v", err)
	}
	_ = second.Unlock()
}

// TestWriteFileLocked_UnderCallerHeldLock covers the read-modify-write pattern the periodic
// config sync relies on: take the lock once, read the current content, derive the next one and
// write it back, with no window for another writer in between.
func TestWriteFileLocked_UnderCallerHeldLock(t *testing.T) {
	path := filepath.Join(t.TempDir(), "probe.yaml")
	if err := os.WriteFile(path, []byte("old\n"), 0o644); err != nil {
		t.Fatalf("seed file failed, errmsg: %s", err)
	}

	lockPath, err := LockPathFor(path)
	if err != nil {
		t.Fatalf("resolve lock path failed, errmsg: %s", err)
	}
	fl, err := AcquireFileLock(lockPath, time.Second)
	if err != nil {
		t.Fatalf("acquire lock failed, errmsg: %s", err)
	}

	current, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read current failed, errmsg: %s", err)
	}
	changed, err := WriteFileLocked(path, append(current, []byte("new\n")...))
	if err != nil {
		t.Fatalf("write under held lock failed, errmsg: %s", err)
	}
	if !changed {
		t.Fatal("expected content change to be reported")
	}
	if err := fl.Unlock(); err != nil {
		t.Fatalf("unlock failed, errmsg: %s", err)
	}

	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read back failed, errmsg: %s", err)
	}
	if string(got) != "old\nnew\n" {
		t.Fatalf("unexpected content: %q", string(got))
	}

	// Unchanged content must still be reported as such on this path.
	again, err := WriteFileLocked(path, []byte("old\nnew\n"))
	if err != nil {
		t.Fatalf("second write failed, errmsg: %s", err)
	}
	if again {
		t.Fatal("expected identical content to be skipped")
	}
}

// TestWriteFileWithLock_NestedCallTimesOut pins the constraint documented on WriteFileLocked:
// flock excludes different descriptors even inside one process, so calling the locking variant
// while already holding the lock deadlocks until the timeout rather than succeeding.
func TestWriteFileWithLock_NestedCallTimesOut(t *testing.T) {
	path := filepath.Join(t.TempDir(), "probe.yaml")

	lockPath, err := LockPathFor(path)
	if err != nil {
		t.Fatalf("resolve lock path failed, errmsg: %s", err)
	}
	fl, err := AcquireFileLock(lockPath, time.Second)
	if err != nil {
		t.Fatalf("acquire lock failed, errmsg: %s", err)
	}
	defer func() { _ = fl.Unlock() }()

	if _, err := WriteFileWithLock(path, []byte("data\n"), 100*time.Millisecond); err == nil {
		t.Fatal("expected nested WriteFileWithLock to fail while the lock is held")
	}
}

// TestLockPathFor_MatchesSymlinkTarget makes sure a caller-held lock guards the same file the
// write path locks, which would not hold if one side locked the link and the other the target.
func TestLockPathFor_MatchesSymlinkTarget(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink creation needs privileges on windows")
	}

	dir := t.TempDir()
	target := filepath.Join(dir, "real.yaml")
	link := filepath.Join(dir, "link.yaml")
	if err := os.WriteFile(target, []byte("x\n"), 0o644); err != nil {
		t.Fatalf("seed target failed, errmsg: %s", err)
	}
	if err := os.Symlink(target, link); err != nil {
		t.Fatalf("symlink failed, errmsg: %s", err)
	}

	viaLink, err := LockPathFor(link)
	if err != nil {
		t.Fatalf("resolve via link failed, errmsg: %s", err)
	}
	viaTarget, err := LockPathFor(target)
	if err != nil {
		t.Fatalf("resolve via target failed, errmsg: %s", err)
	}
	if viaLink != viaTarget {
		t.Fatalf("lock path differs through symlink, link: %s, target: %s", viaLink, viaTarget)
	}
}

func TestWriteFileWithLock_ConcurrentWritersKeepFileIntact(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, "probe.yaml")

	const writers = 8
	payloads := make([][]byte, writers)
	for i := range payloads {
		payloads[i] = []byte(strings.Repeat(fmt.Sprintf("writer-%d\n", i), 2048))
	}

	var wg sync.WaitGroup
	errs := make([]error, writers)
	for i := 0; i < writers; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			_, errs[idx] = WriteFileWithLock(target, payloads[idx], 10*time.Second)
		}(i)
	}
	wg.Wait()

	// Every call must succeed: a failure here means the stale-temp cleanup of one
	// writer wiped the temp file another writer was still using.
	for i, err := range errs {
		if err != nil {
			t.Fatalf("writer %d failed: %v", i, err)
		}
	}

	got, err := os.ReadFile(target)
	if err != nil {
		t.Fatalf("read target: %v", err)
	}
	for _, payload := range payloads {
		if bytes.Equal(got, payload) {
			return
		}
	}
	t.Fatalf("target content matches no single writer payload, size: %d", len(got))
}

func TestWriteFileWithLock_ReaderAlwaysSeesCompleteFile(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("windows rename hits sharing violations against a busy reader")
	}

	dir := t.TempDir()
	target := filepath.Join(dir, "probe.yaml")

	oldContent := []byte(strings.Repeat("old\n", 4096))
	newContent := []byte(strings.Repeat("new\n", 8192))
	if _, err := WriteFileWithLock(target, oldContent, time.Second); err != nil {
		t.Fatalf("seed target: %v", err)
	}

	done := make(chan struct{})
	var readErr error
	go func() {
		defer close(done)
		for i := 0; i < 200; i++ {
			got, err := os.ReadFile(target)
			if err != nil {
				readErr = fmt.Errorf("read target: %w", err)
				return
			}
			if !bytes.Equal(got, oldContent) && !bytes.Equal(got, newContent) {
				readErr = fmt.Errorf("reader saw a partial file, size: %d", len(got))
				return
			}
		}
	}()

	for i := 0; i < 20; i++ {
		content := oldContent
		if i%2 == 1 {
			content = newContent
		}
		if _, err := WriteFileWithLock(target, content, 10*time.Second); err != nil {
			t.Fatalf("write round %d: %v", i, err)
		}
	}
	<-done

	if readErr != nil {
		t.Fatal(readErr)
	}
}

func TestWriteFileWithLock_SkipsWriteWhenContentUnchanged(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, "probe.yaml")
	content := []byte("name: probe\nversion: v2.0.0\n")

	changed, err := WriteFileWithLock(target, content, time.Second)
	if err != nil {
		t.Fatalf("first write: %v", err)
	}
	if !changed {
		t.Fatal("expected the first write to report a change")
	}

	changed, err = WriteFileWithLock(target, content, time.Second)
	if err != nil {
		t.Fatalf("second write: %v", err)
	}
	if changed {
		t.Fatal("expected identical content to be skipped")
	}
	assertFileContent(t, target, content)

	updated := []byte("name: probe\nversion: v2.0.1\n")
	changed, err = WriteFileWithLock(target, updated, time.Second)
	if err != nil {
		t.Fatalf("third write: %v", err)
	}
	if !changed {
		t.Fatal("expected changed content to be written")
	}
	assertFileContent(t, target, updated)
}

func TestWriteFileWithLock_RenameFailureKeepsNoTempFile(t *testing.T) {
	dir := t.TempDir()
	// A directory as target makes rename fail deterministically, unlike a read-only
	// parent directory which root would simply ignore.
	target := filepath.Join(dir, "probe.yaml")
	if err := os.Mkdir(target, 0o755); err != nil {
		t.Fatalf("prepare directory target: %v", err)
	}

	if _, err := WriteFileWithLock(target, []byte("data"), time.Second); err == nil {
		t.Fatal("expected rename onto a directory to fail")
	}

	if info, err := os.Stat(target); err != nil || !info.IsDir() {
		t.Fatalf("target directory should survive, err: %v", err)
	}
	assertNoTempFileLeft(t, dir, "probe.yaml")
}

func TestWriteFileWithLock_RemovesStaleTempFile(t *testing.T) {
	dir := t.TempDir()
	target := filepath.Join(dir, "probe.yaml")

	stale := filepath.Join(dir, "probe.yaml.tmp-123456")
	if err := os.WriteFile(stale, []byte("leftover"), 0o644); err != nil {
		t.Fatalf("prepare stale temp file: %v", err)
	}

	if _, err := WriteFileWithLock(target, []byte("data"), time.Second); err != nil {
		t.Fatalf("write: %v", err)
	}

	if _, err := os.Stat(stale); !os.IsNotExist(err) {
		t.Fatalf("stale temp file should be removed, err: %v", err)
	}
	assertNoTempFileLeft(t, dir, "probe.yaml")
}

func TestWriteFileWithLock_KeepsExistingFileMode(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("windows only models the read-only bit through chmod")
	}

	dir := t.TempDir()
	target := filepath.Join(dir, "probe.yaml")
	if err := os.WriteFile(target, []byte("old"), 0o600); err != nil {
		t.Fatalf("prepare target: %v", err)
	}

	if _, err := WriteFileWithLock(target, []byte("new"), time.Second); err != nil {
		t.Fatalf("write: %v", err)
	}

	info, err := os.Stat(target)
	if err != nil {
		t.Fatalf("stat target: %v", err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("expected mode 0600, got: %o", info.Mode().Perm())
	}
}

func TestWriteFileWithLock_WritesThroughSymlink(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("creating symlinks on windows requires elevated privileges")
	}

	dir := t.TempDir()
	realPath := filepath.Join(dir, "real.yaml")
	link := filepath.Join(dir, "link.yaml")
	if err := os.WriteFile(realPath, []byte("old"), 0o644); err != nil {
		t.Fatalf("prepare real file: %v", err)
	}
	if err := os.Symlink(realPath, link); err != nil {
		t.Fatalf("prepare symlink: %v", err)
	}

	if _, err := WriteFileWithLock(link, []byte("new"), time.Second); err != nil {
		t.Fatalf("write through symlink: %v", err)
	}

	assertFileContent(t, realPath, []byte("new"))

	info, err := os.Lstat(link)
	if err != nil {
		t.Fatalf("lstat link: %v", err)
	}
	if info.Mode()&os.ModeSymlink == 0 {
		t.Fatal("symlink should not be replaced by a regular file")
	}
}

// TestWriteAndSync_ReportsWriteFailure covers the error path of the temp-file write.
// Swallowing it would let a truncated file be renamed onto the config, which is
// exactly the corruption the atomic replacement is meant to prevent. A closed handle
// is the portable way to make the write fail without touching the filesystem state.
func TestWriteAndSync_ReportsWriteFailure(t *testing.T) {
	f, err := os.CreateTemp(t.TempDir(), "probe.yaml.tmp-*")
	if err != nil {
		t.Fatalf("create temp: %v", err)
	}
	if err := f.Close(); err != nil {
		t.Fatalf("close temp: %v", err)
	}

	if err := writeAndSync(f, []byte("data")); err == nil {
		t.Fatal("expected a write error on a closed file")
	}
}

// TestWriteAndSync_ClosesFileOnSuccess guards the other half of the contract: the
// handle must not leak, otherwise a long-running probe would exhaust its descriptors.
func TestWriteAndSync_ClosesFileOnSuccess(t *testing.T) {
	dir := t.TempDir()
	f, err := os.CreateTemp(dir, "probe.yaml.tmp-*")
	if err != nil {
		t.Fatalf("create temp: %v", err)
	}

	if err := writeAndSync(f, []byte("data")); err != nil {
		t.Fatalf("write and sync: %v", err)
	}
	if err := f.Close(); err == nil {
		t.Fatal("expected the file to be closed already")
	}

	assertFileContent(t, f.Name(), []byte("data"))
}

// TestSyncDir_FlushesExistingAndReportsMissing covers the step that makes a rename
// durable. A silent failure here would leave the warning callers rely on unprinted,
// so the missing-directory case must surface an error on unix; Windows has no such
// flush and must stay a no-op.
func TestSyncDir_FlushesExistingAndReportsMissing(t *testing.T) {
	dir := t.TempDir()

	if err := syncDir(dir); err != nil {
		t.Fatalf("sync existing dir: %v", err)
	}

	err := syncDir(filepath.Join(dir, "no-such-dir"))
	if runtime.GOOS == "windows" {
		if err != nil {
			t.Fatalf("windows syncDir must stay a no-op, got: %v", err)
		}
		return
	}
	if err == nil {
		t.Fatal("expected an error for a missing directory")
	}
}

func assertFileContent(t *testing.T, path string, want []byte) {
	t.Helper()

	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	if !bytes.Equal(got, want) {
		t.Fatalf("unexpected content in %s, got: %q, want: %q", path, got, want)
	}
}

func assertNoTempFileLeft(t *testing.T, dir, base string) {
	t.Helper()

	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("read dir %s: %v", dir, err)
	}
	for _, entry := range entries {
		if strings.HasPrefix(entry.Name(), base+".tmp-") {
			t.Fatalf("temp file left behind: %s", entry.Name())
		}
	}
}
