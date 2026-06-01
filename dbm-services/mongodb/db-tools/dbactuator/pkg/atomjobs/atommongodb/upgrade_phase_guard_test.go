package atommongodb

import (
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

// setupGuardTestDir 把决策文件根目录指向独立 temp dir，并预创建 mongodata/<port>/。
// upgradePhaseDecisionFile 通过 consts.GetMongoDataDir() → MONGO_DATA_DIR 环境变量定位文件，
// 这里用 t.Setenv 隔离避免污染实际 /data1。
func setupGuardTestDir(t *testing.T, port int) {
	t.Helper()
	root := t.TempDir()
	t.Setenv("MONGO_DATA_DIR", root)
	if err := os.MkdirAll(filepath.Join(root, "mongodata", strconv.Itoa(port)), 0755); err != nil {
		t.Fatalf("mkdir mongodata/%d failed: %v", port, err)
	}
}

func TestUpgradePhase_WriteAndReadRoundTrip(t *testing.T) {
	const port = 27001
	setupGuardTestDir(t, port)

	if err := writeUpgradePhaseDecision(port, UpgradePhaseSecondary, "mongodb-3.6.23", true); err != nil {
		t.Fatalf("write skip=true failed: %v", err)
	}
	skip, err := upgradePhaseShouldSkip(port, UpgradePhaseSecondary, "mongodb-3.6.23")
	if err != nil {
		t.Fatalf("read after write skip=true err: %v", err)
	}
	if !skip {
		t.Fatalf("expect skip=true, got false")
	}

	// 覆盖写：skip=false 应被原样读出。
	if err := writeUpgradePhaseDecision(port, UpgradePhaseSecondary, "mongodb-3.6.23", false); err != nil {
		t.Fatalf("overwrite skip=false failed: %v", err)
	}
	skip, err = upgradePhaseShouldSkip(port, UpgradePhaseSecondary, "mongodb-3.6.23")
	if err != nil {
		t.Fatalf("read after overwrite err: %v", err)
	}
	if skip {
		t.Fatalf("expect skip=false after overwrite, got true")
	}
}

func TestUpgradePhase_FileNotExist(t *testing.T) {
	const port = 27002
	setupGuardTestDir(t, port)
	// 不写入，文件不存在。
	skip, err := upgradePhaseShouldSkip(port, UpgradePhaseSecondary, "mongodb-3.6.23")
	if err != nil {
		t.Fatalf("missing file should not error, got: %v", err)
	}
	if skip {
		t.Fatalf("missing file must fail-open (skip=false), got true")
	}
}

func TestUpgradePhase_CorruptedJSON(t *testing.T) {
	const port = 27003
	setupGuardTestDir(t, port)
	// 写入坏字节模拟进程被 kill 残留半截文件（虽然修复后此场景不该出现，仍要兜底为不跳过）。
	if err := os.WriteFile(upgradePhaseDecisionFile(port), []byte("{not-json"), 0644); err != nil {
		t.Fatalf("seed corrupted file failed: %v", err)
	}
	skip, err := upgradePhaseShouldSkip(port, UpgradePhaseSecondary, "mongodb-3.6.23")
	if err != nil {
		t.Fatalf("corrupted file should not error, got: %v", err)
	}
	if skip {
		t.Fatalf("corrupted file must fail-open (skip=false), got true")
	}
}

func TestUpgradePhase_PhaseMismatch(t *testing.T) {
	const port = 27004
	setupGuardTestDir(t, port)
	if err := writeUpgradePhaseDecision(port, UpgradePhaseSecondary, "mongodb-3.6.23", true); err != nil {
		t.Fatalf("write failed: %v", err)
	}
	// 同 destVersion，不同 phase：旧标签应被忽略。
	skip, err := upgradePhaseShouldSkip(port, UpgradePhasePrimary, "mongodb-3.6.23")
	if err != nil {
		t.Fatalf("phase mismatch read err: %v", err)
	}
	if skip {
		t.Fatalf("phase mismatch must return skip=false, got true")
	}
}

func TestUpgradePhase_DestVersionMismatch(t *testing.T) {
	const port = 27005
	setupGuardTestDir(t, port)
	if err := writeUpgradePhaseDecision(port, UpgradePhaseSecondary, "mongodb-3.6.23", true); err != nil {
		t.Fatalf("write failed: %v", err)
	}
	// 同 phase，不同 destVersion：跨 hop 残留旧标签应被忽略，避免下一阶段误跳过。
	skip, err := upgradePhaseShouldSkip(port, UpgradePhaseSecondary, "mongodb-4.0.26")
	if err != nil {
		t.Fatalf("destVersion mismatch read err: %v", err)
	}
	if skip {
		t.Fatalf("destVersion mismatch must return skip=false, got true")
	}
}

func TestUpgradePhase_EmptyPhaseShortCircuit(t *testing.T) {
	const port = 27006
	setupGuardTestDir(t, port)
	// 即使文件存在 skip=true，调用方传入空 phase 也必须立刻返回 false（非升级链路不启用守卫）。
	if err := writeUpgradePhaseDecision(port, UpgradePhaseSecondary, "mongodb-3.6.23", true); err != nil {
		t.Fatalf("write failed: %v", err)
	}
	skip, err := upgradePhaseShouldSkip(port, "", "mongodb-3.6.23")
	if err != nil {
		t.Fatalf("empty phase read err: %v", err)
	}
	if skip {
		t.Fatalf("empty phase must short-circuit to skip=false, got true")
	}
}

func TestUpgradePhase_AtomicWriteNoTmpLeak(t *testing.T) {
	const port = 27007
	setupGuardTestDir(t, port)
	if err := writeUpgradePhaseDecision(port, UpgradePhaseSecondary, "mongodb-3.6.23", true); err != nil {
		t.Fatalf("write failed: %v", err)
	}
	tmp := upgradePhaseDecisionFile(port) + ".tmp"
	if _, err := os.Stat(tmp); !os.IsNotExist(err) {
		t.Fatalf(".tmp must be renamed away after successful write, stat err=%v", err)
	}
	final := upgradePhaseDecisionFile(port)
	if _, err := os.Stat(final); err != nil {
		t.Fatalf("final file must exist after write, err=%v", err)
	}
}
