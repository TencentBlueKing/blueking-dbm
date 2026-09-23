package archivescenes

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func init() {
	config.MonitorConfig = &config.Config{Port: 20000}
}

// mkSnapshot 按真实命名规则造一个快照文件, 返回目录和文件路径
// 注意 mtime 故意设成 now, 用来验证清理只看名字不看 mtime
func mkSnapshot(t *testing.T, basePath string, dirName string, at time.Time) (dirPath, filePath string) {
	t.Helper()

	dirPath = filepath.Join(basePath, dirName)
	if err := os.MkdirAll(dirPath, 0755); err != nil {
		t.Fatal(err)
	}
	filePath = filepath.Join(dirPath, at.Format(fileTimeLayout)+fileNameExt)
	if err := os.WriteFile(filePath, []byte("x"), 0644); err != nil {
		t.Fatal(err)
	}

	return dirPath, filePath
}

func assertExists(t *testing.T, path string, want bool, desc string) {
	t.Helper()

	_, err := os.Stat(path)
	if want && err != nil {
		t.Errorf("%s: %s 应该存在, 但 %v", desc, path, err)
	}
	if !want && err == nil {
		t.Errorf("%s: %s 应该已被删除", desc, path)
	}
}

func TestDeleteOldByHours(t *testing.T) {
	basePath := t.TempDir()
	now := time.Now()
	// cutoff 是 3 小时前
	cutoff := now.Add(-3 * time.Hour)
	prefix := dirPrefix("processlist")

	// cutoff 当天的目录: 里面新旧文件混放, 要逐个判断
	boundaryDir := prefix + cutoff.Format(dirDateLayout)
	_, fresh := mkSnapshot(t, basePath, boundaryDir, cutoff.Add(1*time.Hour))  // 未过期
	_, stale := mkSnapshot(t, basePath, boundaryDir, cutoff.Add(-1*time.Hour)) // 已过期

	// 比 cutoff 那天更早的目录: 整个删掉
	oldDirName := prefix + cutoff.Add(-48*time.Hour).Format(dirDateLayout)
	oldDir, oldFile := mkSnapshot(t, basePath, oldDirName, cutoff.Add(-48*time.Hour))

	// 前缀不匹配(其他场景)的目录: 不能动
	otherSceneDir, otherSceneFile := mkSnapshot(
		t, basePath,
		dirPrefix("engine-innodb-status")+cutoff.Add(-48*time.Hour).Format(dirDateLayout),
		cutoff.Add(-48*time.Hour),
	)

	// 其他实例(端口不同)的目录: 不能动
	otherPortDir, otherPortFile := mkSnapshot(
		t, basePath,
		"processlist.20001."+cutoff.Add(-48*time.Hour).Format(dirDateLayout),
		cutoff.Add(-48*time.Hour),
	)

	// 名字里没有日期的目录: 不敢动
	weirdDir, weirdFile := mkSnapshot(t, basePath, prefix+"not-a-date", now)

	if err := DeleteOld("processlist", basePath, 3); err != nil {
		t.Fatal(err)
	}

	assertExists(t, fresh, true, "cutoff 之后的文件要保留")
	assertExists(t, stale, false, "cutoff 之前的文件要删除")
	assertExists(t, filepath.Join(basePath, boundaryDir), true, "目录里还有文件, 目录要保留")
	assertExists(t, oldFile, false, "更早日期的目录里的文件要删除")
	assertExists(t, oldDir, false, "更早日期的目录本身也要删除")
	assertExists(t, otherSceneFile, true, "其他场景的文件不能动")
	assertExists(t, otherSceneDir, true, "其他场景的目录不能动")
	assertExists(t, otherPortFile, true, "其他实例的文件不能动")
	assertExists(t, otherPortDir, true, "其他实例的目录不能动")
	assertExists(t, weirdFile, true, "名字解析不出日期的目录不能动")
	assertExists(t, weirdDir, true, "名字解析不出日期的目录不能动")
}

// 目录里所有文件都过期时, 空目录要被一起清掉
func TestDeleteOldRemoveEmptiedBoundaryDir(t *testing.T) {
	basePath := t.TempDir()
	cutoff := time.Now().Add(-3 * time.Hour)
	dirName := dirPrefix("processlist") + cutoff.Format(dirDateLayout)

	dirPath, filePath := mkSnapshot(t, basePath, dirName, cutoff.Add(-1*time.Hour))

	if err := DeleteOld("processlist", basePath, 3); err != nil {
		t.Fatal(err)
	}

	assertExists(t, filePath, false, "过期文件要删除")
	assertExists(t, dirPath, false, "删空后的目录要一起删掉")
}

// 清理只看文件名, 不看 mtime
func TestDeleteOldIgnoreMtime(t *testing.T) {
	basePath := t.TempDir()
	now := time.Now()
	cutoff := now.Add(-3 * time.Hour)

	// 文件名是很久以前, 但 mtime 是刚刚(比如被 touch 过)
	dirName := dirPrefix("processlist") + cutoff.Add(-48*time.Hour).Format(dirDateLayout)
	_, filePath := mkSnapshot(t, basePath, dirName, cutoff.Add(-48*time.Hour))
	if err := os.Chtimes(filePath, now, now); err != nil {
		t.Fatal(err)
	}

	if err := DeleteOld("processlist", basePath, 3); err != nil {
		t.Fatal(err)
	}

	assertExists(t, filePath, false, "按文件名判断过期, 和 mtime 无关")
}

func TestDeleteOldZeroHoursKeepAll(t *testing.T) {
	basePath := t.TempDir()
	long := time.Now().Add(-1000 * time.Hour)

	_, filePath := mkSnapshot(
		t, basePath,
		dirPrefix("processlist")+long.Format(dirDateLayout),
		long,
	)

	// hours <= 0 时不做任何清理
	if err := DeleteOld("processlist", basePath, 0); err != nil {
		t.Fatal(err)
	}
	assertExists(t, filePath, true, "hours=0 不应该删除任何文件")
}

func TestDeleteOldBasePathNotExist(t *testing.T) {
	// 目录不存在不算错误
	if err := DeleteOld("processlist", filepath.Join(t.TempDir(), "not-exist"), 1); err != nil {
		t.Fatal(err)
	}
}

// Write 落盘的名字必须能被 DeleteOld 正确解析, 防止两边命名规则漂移
func TestWriteThenDeleteOld(t *testing.T) {
	basePath := t.TempDir()

	if err := Write("processlist", basePath, []byte("hello")); err != nil {
		t.Fatal(err)
	}

	// 刚写的快照, 保留 1 小时的话不该被删
	if err := DeleteOld("processlist", basePath, 1); err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(basePath)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 {
		t.Fatalf("expect 1 dir kept, got %d", len(entries))
	}

	files, err := os.ReadDir(filepath.Join(basePath, entries[0].Name()))
	if err != nil {
		t.Fatal(err)
	}
	if len(files) != 1 {
		t.Fatalf("expect 1 file kept, got %d", len(files))
	}
}
