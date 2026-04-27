package consts

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
)

const exportMongoBinDirPrefix = "export MONGO_BIN_DIR="

// Fixed path so concurrent dbactuator processes serialize updates to /etc/profile.
const mongoBinDirEtcProfileLockPath = "/tmp/mongo-dbactuator-set-mongo-bin-dir.lock"

func withMongoBinDirEtcProfileLock(fn func() error) error {
	f, err := os.OpenFile(mongoBinDirEtcProfileLockPath, os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		return fmt.Errorf("open lock file %s: %w", mongoBinDirEtcProfileLockPath, err)
	}
	defer f.Close()
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX); err != nil {
		return fmt.Errorf("lock %s: %w", mongoBinDirEtcProfileLockPath, err)
	}
	defer func() {
		_ = syscall.Flock(int(f.Fd()), syscall.LOCK_UN)
	}()
	return fn()
}

// parseProfileMongoBinDir extracts the value after export MONGO_BIN_DIR=...
func parseProfileMongoBinDir(trimmedLine string) (string, bool) {
	if !strings.HasPrefix(trimmedLine, exportMongoBinDirPrefix) {
		return "", false
	}
	raw := strings.TrimSpace(strings.TrimPrefix(trimmedLine, exportMongoBinDirPrefix))
	if raw == "" {
		return "", false
	}
	if unq, err := strconv.Unquote(raw); err == nil {
		raw = unq
	} else if strings.HasPrefix(raw, `'`) && strings.HasSuffix(raw, `'`) && len(raw) >= 2 {
		raw = raw[1 : len(raw)-1]
	}
	return filepath.Clean(raw), true
}

func uniqueStrings(vals []string) []string {
	seen := make(map[string]struct{})
	out := make([]string, 0)
	for _, v := range vals {
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		out = append(out, v)
	}
	return out
}

// readEtcProfileMongoBinDirs collects MONGO_BIN_DIR values from matching export lines at line start (^export...).
func readEtcProfileMongoBinDirs(path string) ([]string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return nil, nil
		}
		return nil, err
	}
	var vals []string
	for _, rawLine := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(rawLine)
		if len(line) == 0 || line[0] == '#' {
			continue
		}
		v, ok := parseProfileMongoBinDir(line)
		if !ok {
			continue
		}
		vals = append(vals, v)
	}
	return vals, nil
}

// SetMongoBinDir sets MONGO_BIN_DIR and persists it to /etc/profile when running as root.
// Non-root processes only update the current process env (cannot write /etc/profile).
// Empty input keeps existing env or falls back to default /usr/local.
// This override is mainly for test environments; production normally keeps the default.
//
// For root: if /etc/profile already defines MONGO_BIN_DIR, the path must equal the desired
// value or an error is returned; if equal, no line is appended.
// MONGO_BIN_DIR 是给测试环境使用的，生产环境使用默认值 /usr/local。
func SetMongoBinDir(binDir string) error {
	if binDir == "" {
		binDir = os.Getenv("MONGO_BIN_DIR")
	}
	if binDir == "" {
		binDir = UsrLocal
	}
	binDir = strings.TrimSpace(binDir)
	if !filepath.IsAbs(binDir) {
		return fmt.Errorf("MONGO_BIN_DIR must be an absolute path, got %q", binDir)
	}

	if os.Geteuid() == 0 {
		if err := withMongoBinDirEtcProfileLock(func() error {
			vals, err := readEtcProfileMongoBinDirs("/etc/profile")
			if err != nil {
				return fmt.Errorf("SetMongoBinDir failed reading /etc/profile: %w", err)
			}
			want := filepath.Clean(binDir)
			uniques := uniqueStrings(vals)
			if len(uniques) > 1 {
				return fmt.Errorf("SetMongoBinDir failed: conflicting MONGO_BIN_DIR in /etc/profile: %v", uniques)
			}
			if len(uniques) == 1 && uniques[0] != want {
				return fmt.Errorf(
					"SetMongoBinDir failed: /etc/profile has MONGO_BIN_DIR=%q, refusing different value %q",
					uniques[0], binDir)
			}
			if len(uniques) == 1 && uniques[0] == want {
				// 已定义且一致，不再追加。
				return nil
			}
			f, err := os.OpenFile("/etc/profile", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
			if err != nil {
				return fmt.Errorf("SetMongoBinDir failed appending /etc/profile: %w", err)
			}
			line := fmt.Sprintf("%s%s\n", exportMongoBinDirPrefix, strconv.Quote(binDir))
			if _, werr := f.WriteString(line); werr != nil {
				f.Close()
				return fmt.Errorf("SetMongoBinDir failed writing /etc/profile: %w", werr)
			}
			if cerr := f.Close(); cerr != nil {
				return fmt.Errorf("SetMongoBinDir failed closing /etc/profile: %w", cerr)
			}
			return nil
		}); err != nil {
			return err
		}
	}

	os.Setenv("MONGO_BIN_DIR", binDir)
	return nil
}

// GetMongoBinDir returns env MONGO_BIN_DIR or default /usr/local.
func GetMongoBinDir() string {
	binDir := strings.TrimSpace(os.Getenv("MONGO_BIN_DIR"))
	if binDir == "" {
		return UsrLocal
	}
	return binDir
}
