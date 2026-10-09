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
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

const recoverSubDir = "dbbak/recover_redis"

var compressedSuffixes = []string{".zst", ".gz", ".lzo", ".tar", ".tgz"}

func resolveFiles(saveDir string, inst InstanceRestore) ([]string, error) {
	if len(inst.FullFiles) > 0 {
		var found []string
		for _, name := range inst.FullFiles {
			base := filepath.Base(name)
			p := filepath.Join(saveDir, base)
			if util.FileExists(p) {
				found = append(found, p)
				continue
			}
			matches, _ := filepath.Glob(filepath.Join(saveDir, "*"+base+"*"))
			found = append(found, matches...)
		}
		if len(found) == 0 {
			return nil, fmt.Errorf("no backup files for %s:%d in %s", inst.SourceIP, inst.SourcePort, saveDir)
		}
		return uniq(found), nil
	}
	pattern := fmt.Sprintf("*%s-%d*", inst.SourceIP, inst.SourcePort)
	matches, err := filepath.Glob(filepath.Join(saveDir, pattern))
	if err != nil || len(matches) == 0 {
		return nil, fmt.Errorf("scan backup dir %s for %s:%d failed: %v", saveDir, inst.SourceIP, inst.SourcePort, err)
	}
	return matches, nil
}

// stageWorkDir names the per-backup unpack directory from the first (sorted) backup file.
func stageWorkDir(saveDir, first string) string {
	if strings.Contains(first, ".split.") {
		return filepath.Join(saveDir, strings.Split(first, ".split")[0])
	}
	prefix := first
	for _, ext := range compressedSuffixes {
		prefix = strings.TrimSuffix(prefix, ext)
	}
	if prefix == first {
		prefix = strings.TrimSuffix(first, filepath.Ext(first))
	}
	return filepath.Join(saveDir, prefix)
}

func runStageCmd(cmd string) error {
	_, err := util.RunLocalCmd("bash", []string{"-c", cmd}, "", nil, 1800*time.Second)
	return err
}

// unpackBackup unpacks straight from the downloaded files into their work dir. The download is
// never copied, and stays in place so a retry can stage it again.
func unpackBackup(saveDir string, files []string) (workDir string, err error) {
	sort.Strings(files)
	first := filepath.Base(files[0])
	workDir = stageWorkDir(saveDir, first)
	if err = os.MkdirAll(workDir, 0755); err != nil {
		return
	}

	src := files[0]
	switch {
	case strings.Contains(first, ".split."):
		prefix := strings.Split(first, ".split")[0]
		err = runStageCmd(fmt.Sprintf("cd %s && cat %s.split.* | tar x -C %s", saveDir, prefix, workDir))
	case strings.HasSuffix(first, ".tar.gz") || strings.HasSuffix(first, ".tgz"):
		err = runStageCmd(fmt.Sprintf("tar -xzf %s -C %s", src, workDir))
	case strings.HasSuffix(first, ".tar"):
		err = runStageCmd(fmt.Sprintf("tar -xf %s -C %s", src, workDir))
	default:
		err = decompressFile(src, filepath.Join(workDir, first))
	}
	return
}

// decompressFile writes src decompressed to dst minus its compression suffix, keeping src.
// Uncompressed files are hard linked so a later mv out of the work dir keeps the download.
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

func isCompressed(name string) bool {
	for _, ext := range compressedSuffixes {
		if strings.HasSuffix(name, ext) {
			return true
		}
	}
	return false
}

// CleanupStaged removes a completed port's unpack directory and its downloaded full-backup files.
func CleanupStaged(saveDir string, inst InstanceRestore) error {
	if len(inst.FullFiles) == 0 {
		return nil
	}
	if saveDir == "" {
		saveDir = DefaultSaveDir()
	}
	files, err := resolveFiles(saveDir, inst)
	if err != nil {
		return err
	}
	sort.Strings(files)
	if err = os.RemoveAll(stageWorkDir(saveDir, filepath.Base(files[0]))); err != nil {
		return err
	}
	for _, f := range files {
		if st, statErr := os.Stat(f); statErr == nil && !st.IsDir() {
			if err = os.Remove(f); err != nil {
				return err
			}
		}
	}
	mylog.Logger.Info("cleaned staged backup for dest_port=%d", inst.DestPort)
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
