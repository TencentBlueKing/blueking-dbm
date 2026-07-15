/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package process

import (
	"path/filepath"
	"testing"
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
