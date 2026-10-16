// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

const (
	recoverSubDir = "dbbak/recover_redis"
	unpackSubDir  = "recover_redis"
)

var compressedSuffixes = []string{".zst", ".gz", ".lzo", ".tar", ".tgz"}

// resolveFiles finds inst's full backup files by their exact names. The verify node has already
// checked every planned file is there, so no other file of the source instance may stand in.
func resolveFiles(saveDir string, inst InstanceRestore) ([]string, error) {
	var found, missing []string
	for _, name := range inst.FullFiles {
		p := filepath.Join(saveDir, filepath.Base(name))
		if util.FileExists(p) {
			found = append(found, p)
			continue
		}
		missing = append(missing, filepath.Base(name))
	}
	if len(missing) > 0 {
		return nil, fmt.Errorf("backup files of %s:%d missing in %s: %v", inst.SourceIP, inst.SourcePort,
			saveDir, missing)
	}
	if len(found) == 0 {
		return nil, fmt.Errorf("no backup files planned for %s:%d", inst.SourceIP, inst.SourcePort)
	}
	return uniq(found), nil
}

func runStageCmd(cmd string) error {
	out, err := util.RunLocalCmd("bash", []string{"-c", cmd}, "", nil, 1800*time.Second)
	if err != nil {
		return fmt.Errorf("%v %s", err, out)
	}
	return nil
}

// corrupted marks an unpack failure as a broken backup, apart from restore, start or replay failures.
func corrupted(name string, err error) error {
	return fmt.Errorf("backup file corrupted (备份文件损坏): %s: %v", name, err)
}

// unpackBackup unpacks the downloaded files into workDir, which starts empty so a retry never
// picks up a previous attempt's leftovers. The downloads stay in place for retries.
func unpackBackup(files []string, workDir string) error {
	sort.Strings(files)
	first := filepath.Base(files[0])
	if err := os.RemoveAll(workDir); err != nil {
		return err
	}
	if err := os.MkdirAll(workDir, 0755); err != nil {
		return err
	}

	if err := requireTools(first); err != nil {
		return err
	}
	src := files[0]
	var err error
	switch {
	case strings.Contains(first, ".split."):
		quoted := make([]string, len(files))
		for i, f := range files {
			quoted[i] = "'" + f + "'"
		}
		err = runStageCmd(fmt.Sprintf("cat %s | tar x -C %s", strings.Join(quoted, " "), workDir))
	case strings.HasSuffix(first, ".tar.gz") || strings.HasSuffix(first, ".tgz"):
		err = runStageCmd(fmt.Sprintf("tar -xzf %s -C %s", src, workDir))
	case strings.HasSuffix(first, ".tar"):
		err = runStageCmd(fmt.Sprintf("tar -xf %s -C %s", src, workDir))
	default:
		err = decompressFile(src, filepath.Join(workDir, first))
	}
	if err != nil {
		return corrupted(first, err)
	}
	return nil
}

// decompressFile writes src decompressed to dst minus its compression suffix, keeping src.
// Uncompressed files are hard linked when on the same filesystem, otherwise copied.
func decompressFile(src, dst string) error {
	switch {
	case strings.HasSuffix(dst, ".zst"):
		if _, err := os.Stat(consts.ZstdBin); err != nil {
			return fmt.Errorf("zstd not found: %s", consts.ZstdBin)
		}
		return runStageCmd(fmt.Sprintf("%s -d -f %s -o %s", consts.ZstdBin, src, strings.TrimSuffix(dst, ".zst")))
	case strings.HasSuffix(dst, ".gz"):
		return runStageCmd(fmt.Sprintf("gzip -dc %s > %s", src, strings.TrimSuffix(dst, ".gz")))
	case strings.HasSuffix(dst, ".lzo"):
		if _, err := os.Stat(consts.LzopBin); err != nil {
			return fmt.Errorf("lzop not found: %s", consts.LzopBin)
		}
		return runStageCmd(fmt.Sprintf("%s -d -f %s -o %s", consts.LzopBin, src, strings.TrimSuffix(dst, ".lzo")))
	default:
		_ = os.Remove(dst)
		if os.Link(src, dst) != nil {
			return runStageCmd(fmt.Sprintf("cp -f %s %s", src, dst))
		}
		return nil
	}
}

// requireTools fails on a missing decompressor before unpacking, so it is not blamed on the backup.
func requireTools(name string) error {
	for suffix, bin := range map[string]string{".zst": consts.ZstdBin, ".lzo": consts.LzopBin} {
		if strings.Contains(name, suffix) {
			if _, err := os.Stat(bin); err != nil {
				return fmt.Errorf("%s not found: %s", strings.TrimPrefix(suffix, "."), bin)
			}
		}
	}
	return nil
}

func isCompressed(name string) bool {
	for _, ext := range compressedSuffixes {
		if strings.HasSuffix(name, ext) {
			return true
		}
	}
	return false
}

// sameDeviceFn is replaced in tests, which cannot mount a second filesystem.
var sameDeviceFn = sameDevice

// sameDevice compares the filesystems holding two existing paths.
func sameDevice(a, b string) (bool, error) {
	sa, err := os.Stat(a)
	if err != nil {
		return false, err
	}
	sb, err := os.Stat(b)
	if err != nil {
		return false, err
	}
	da, okA := sa.Sys().(*syscall.Stat_t)
	db, okB := sb.Sys().(*syscall.Stat_t)
	if !okA || !okB {
		return false, fmt.Errorf("no device number for %s or %s", a, b)
	}
	return uint64(da.Dev) == uint64(db.Dev), nil
}

// placeFile moves src to dst: a rename when both are on one filesystem, decided up front from
// their device numbers, otherwise a copy, which the log explains.
func placeFile(log portLog, src, dst string) error {
	same, err := sameDeviceFn(filepath.Dir(src), filepath.Dir(dst))
	if err == nil && same {
		return os.Rename(src, dst)
	}
	if err != nil {
		log.Warn("cannot compare filesystems of %s and %s (%v), copying", src, dst, err)
	} else {
		log.Warn("%s and %s are on different filesystems, copying", src, dst)
	}
	if err = runStageCmd(fmt.Sprintf("cp -f %s %s", src, dst)); err != nil {
		return err
	}
	return os.Remove(src)
}

// CleanupStaged removes a completed port's unpack directory and its downloaded full-backup files.
func CleanupStaged(saveDir, workDir string, inst InstanceRestore) error {
	if len(inst.FullFiles) == 0 {
		return nil
	}
	if saveDir == "" {
		saveDir = DefaultSaveDir()
	}
	if err := os.RemoveAll(workDir); err != nil {
		return err
	}
	for _, name := range inst.FullFiles {
		f := filepath.Join(saveDir, filepath.Base(name))
		if st, statErr := os.Stat(f); statErr == nil && !st.IsDir() {
			if err := os.Remove(f); err != nil {
				return err
			}
		}
	}
	return nil
}

func uniq(in []string) []string {
	seen := map[string]struct{}{}
	var out []string
	for _, v := range in {
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		out = append(out, v)
	}
	return out
}
