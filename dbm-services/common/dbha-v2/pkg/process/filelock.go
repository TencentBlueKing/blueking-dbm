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
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// DefaultFileLockTimeout is the deadline applied by AcquireFileLock and
// WriteFileWithLock when the caller passes a non-positive timeout.
const DefaultFileLockTimeout = 10 * time.Second

const (
	fileLockRetryInterval = 50 * time.Millisecond
	fileLockSuffix        = ".lock"
	tempFileInfix         = ".tmp-"
	renameRetryTimes      = 3
	renameRetryInterval   = 100 * time.Millisecond
)

// AcquireFileLock keeps retrying TryFileLock on path until the exclusive lock is
// held or timeout elapses. A non-positive timeout falls back to
// DefaultFileLockTimeout. It returns a gerrors.Timeout error when the lock stays
// busy for the whole window, and propagates the underlying error when the lock
// file itself cannot be opened. The caller owns the returned lock and must Unlock.
func AcquireFileLock(path string, timeout time.Duration) (*FileLock, error) {
	if timeout <= 0 {
		timeout = DefaultFileLockTimeout
	}
	deadline := time.Now().Add(timeout)

	// Attempt first, check the deadline afterwards, so a very small timeout still
	// gets one real attempt instead of failing without trying.
	for {
		fl, held, err := TryFileLock(path)
		if err != nil {
			return nil, err
		}
		if held {
			return fl, nil
		}

		if time.Now().After(deadline) {
			return nil, gerrors.Newf(gerrors.Timeout,
				"acquire file lock timeout, lock_path: %s, timeout: %s", path, timeout)
		}
		time.Sleep(fileLockRetryInterval)
	}
}

// WriteFileWithLock replaces the content of path with data while holding an
// exclusive lock on the sidecar lock file "<path>.lock", so concurrent writers are
// serialized. Symlinks in path are resolved first, so the real file is locked and
// replaced instead of the link. The replacement goes through a temporary file that
// is synced and then renamed, which keeps concurrent readers on a complete old or
// new version and leaves the original intact when the write fails midway. Mode and
// ownership of an existing target are preserved.
//
// A non-positive timeout falls back to DefaultFileLockTimeout. When the current
// content already equals data, the file is left untouched and (false, nil) is
// returned; a successful replacement returns (true, nil).
func WriteFileWithLock(path string, data []byte, timeout time.Duration) (bool, error) {
	target, err := resolveWriteTarget(path)
	if err != nil {
		return false, err
	}

	// The lock lives beside the target: renaming over the target would swap its
	// inode, and a lock taken on that inode would stop excluding later writers.
	fl, err := AcquireFileLock(target+fileLockSuffix, timeout)
	if err != nil {
		return false, err
	}
	defer func() { _ = fl.Unlock() }()

	return writeResolvedTarget(target, data)
}

// LockPathFor returns the lock file guarding path, resolving path the same way the write
// helpers do so the caller takes exactly the lock they would take. Use it together with
// AcquireFileLock and WriteFileLocked to hold one lock across a read-modify-write sequence.
func LockPathFor(path string) (string, error) {
	target, err := resolveWriteTarget(path)
	if err != nil {
		return "", err
	}
	return target + fileLockSuffix, nil
}

// WriteFileLocked is WriteFileWithLock for callers that already hold the file lock. It exists
// so a read-modify-write sequence (read current content, derive new content, write it back) can
// run as one atomic step against other writers, instead of leaving a window between the read
// and the write in which another process can slip in.
//
// The caller must hold the lock for LockPathFor(path). Do NOT call WriteFileWithLock while
// holding it: TryFileLock opens a fresh descriptor on every attempt and flock excludes
// different descriptors even within the same process, so the nested acquisition would simply
// block until it times out.
func WriteFileLocked(path string, data []byte) (bool, error) {
	target, err := resolveWriteTarget(path)
	if err != nil {
		return false, err
	}

	return writeResolvedTarget(target, data)
}

// writeResolvedTarget performs the replacement itself and assumes the target lock is held.
func writeResolvedTarget(target string, data []byte) (bool, error) {
	dir := filepath.Dir(target)

	cleanupStaleTempFiles(dir, filepath.Base(target))

	if isSameContent(target, data) {
		return false, nil
	}

	info, err := os.Stat(target)
	if err != nil {
		if !os.IsNotExist(err) {
			return false, gerrors.NewE(gerrors.Failure, err)
		}
		info = nil
	}

	tmpPath, err := writeTempFile(target, data, info)
	if err != nil {
		return false, err
	}
	if err := renameWithRetry(tmpPath, target); err != nil {
		return false, err
	}

	// The new content is already on disk, but the directory entry that points at it
	// is not: a crash here would roll the file back to the previous version. Losing
	// that guarantee is not worth failing a write that otherwise succeeded.
	if err := syncDir(dir); err != nil {
		logger.Warn("sync target directory failed, path: %s, errmsg: %s", dir, err)
	}

	return true, nil
}

// resolveWriteTarget creates the parent directory of path and resolves symlinks so
// callers lock and replace the real file. It falls back to path itself when the
// target does not exist yet and its directory cannot be resolved either.
func resolveWriteTarget(path string) (string, error) {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, constant.DirModePermission); err != nil {
		return "", gerrors.NewE(gerrors.Failure, err)
	}

	if resolved, err := filepath.EvalSymlinks(path); err == nil {
		return resolved, nil
	}

	resolvedDir, err := filepath.EvalSymlinks(dir)
	if err != nil {
		return path, nil
	}

	return filepath.Join(resolvedDir, filepath.Base(path)), nil
}

// isSameContent reports whether target already holds exactly data. Any read error
// (missing file, no permission, target is a directory) counts as different, so the
// caller falls through to the regular replacement path.
func isSameContent(target string, data []byte) bool {
	current, err := os.ReadFile(target)
	if err != nil {
		return false
	}

	return bytes.Equal(current, data)
}

// cleanupStaleTempFiles removes temporary files left in dir by a writer that was
// killed between writing and renaming. It must run while holding the lock, since
// other writers are excluded then and every match is guaranteed to be a leftover.
// Prefix matching is used on purpose: glob metacharacters in base would make
// filepath.Glob miss or mismatch entries.
func cleanupStaleTempFiles(dir, base string) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return
	}

	prefix := base + tempFileInfix
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasPrefix(entry.Name(), prefix) {
			continue
		}

		stalePath := filepath.Join(dir, entry.Name())
		if err := os.Remove(stalePath); err != nil {
			logger.Warn("remove stale temp file failed, path: %s, errmsg: %s", stalePath, err)
		}
	}
}

// writeTempFile writes data into a temporary file next to target and returns its
// path, ready to be renamed onto target. info describes the existing target and may
// be nil, in which case constant.FileModePermission is used and ownership is left
// to the caller's identity. The temporary file is removed on any failure.
func writeTempFile(target string, data []byte, info os.FileInfo) (string, error) {
	f, err := os.CreateTemp(filepath.Dir(target), filepath.Base(target)+tempFileInfix+"*")
	if err != nil {
		return "", gerrors.NewE(gerrors.Failure, err)
	}
	tmpPath := f.Name()

	if err := writeAndSync(f, data); err != nil {
		_ = os.Remove(tmpPath)
		return "", err
	}

	mode := os.FileMode(constant.FileModePermission)
	if info != nil {
		mode = info.Mode().Perm()
	}
	if err := os.Chmod(tmpPath, mode); err != nil {
		_ = os.Remove(tmpPath)
		return "", gerrors.NewE(gerrors.Failure, err)
	}

	// Losing the original owner is better than refusing to write: an unprivileged
	// user cannot chown, while the plain overwrite this replaced would have worked.
	if err := preserveOwner(tmpPath, info); err != nil {
		logger.Warn("preserve file owner failed, path: %s, errmsg: %s", target, err)
	}

	return tmpPath, nil
}

// writeAndSync writes data to f, flushes it to disk and closes f in every path.
func writeAndSync(f *os.File, data []byte) error {
	if _, err := f.Write(data); err != nil {
		_ = f.Close()
		return gerrors.NewE(gerrors.Failure, err)
	}

	if err := f.Sync(); err != nil {
		_ = f.Close()
		return gerrors.NewE(gerrors.Failure, err)
	}

	if err := f.Close(); err != nil {
		return gerrors.NewE(gerrors.Failure, err)
	}

	return nil
}

// renameWithRetry moves tmpPath onto target, retrying a few times to ride out the
// sharing violation Windows raises while a reader still has target open. The lock
// is held throughout, so no other writer can slip in between attempts. The
// temporary file is removed when all attempts fail.
func renameWithRetry(tmpPath, target string) error {
	var lastErr error
	for i := 0; i < renameRetryTimes; i++ {
		if i > 0 {
			time.Sleep(renameRetryInterval)
		}

		lastErr = os.Rename(tmpPath, target)
		if lastErr == nil {
			return nil
		}
	}

	_ = os.Remove(tmpPath)

	return gerrors.Newf(gerrors.Failure,
		"rename temp file onto target failed, path: %s, errmsg: %s", target, lastErr)
}
