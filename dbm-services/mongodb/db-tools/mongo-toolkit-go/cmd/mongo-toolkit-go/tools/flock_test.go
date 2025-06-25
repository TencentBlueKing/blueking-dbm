package tools

import (
	"testing"
)

func TestGetLockPath(t *testing.T) {
	lockHandle1, err := getLock("pit_backup", "27017")
	if err != nil {
		t.Fatalf("get lock failed, err: %v", err)
	}
	if lockHandle1 == nil {
		t.Fatalf("lockHandle1 is nil")
	}

	lockHandle2, err := getLock("pit_backup", "27017")
	if err != nil {
		t.Logf("get lock failed, err: %v", err)
	}
	if lockHandle2 != nil {
		t.Fatalf("lockHandle2 is not nil")
	}
	if lockHandle1 != nil {
		lockHandle1.Unlock()
	}
	if lockHandle2 != nil {
		lockHandle2.Unlock()
	}
}
