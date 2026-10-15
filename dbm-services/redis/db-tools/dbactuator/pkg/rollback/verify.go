// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"crypto/md5"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

// manifestNoMD5 stands for an unknown md5; the backup system reports none yet.
const manifestNoMD5 = "-"

// verifyListLimit caps the files named per problem kind, so thousands of binlogs stay readable.
const verifyListLimit = 20

var manifestHeaderReg = regexp.MustCompile(`^# redis rollback manifest plan=\S+ files=(\d+) sha256=([0-9a-f]{64})$`)

// ManifestEntry is one planned file: "<file_name> <size> <md5|->".
type ManifestEntry struct {
	Name string
	Size int64
	MD5  string
}

// ParseManifest reads the manifest the flow pushes next to the downloads. The header's line
// count and sha256 over the lines catch a truncated or foreign file.
func ParseManifest(content []byte) ([]ManifestEntry, string, error) {
	lines := strings.Split(string(content), "\n")
	header := manifestHeaderReg.FindStringSubmatch(strings.TrimSpace(lines[0]))
	if header == nil {
		return nil, "", fmt.Errorf("bad manifest header %q", lines[0])
	}
	var body strings.Builder
	var entries []ManifestEntry
	for i, line := range lines[1:] {
		if line == "" {
			continue
		}
		body.WriteString(line)
		body.WriteString("\n")
		fields := strings.Fields(line)
		if len(fields) != 3 {
			return nil, "", fmt.Errorf("bad manifest line %d: %q", i+2, line)
		}
		size, err := strconv.ParseInt(fields[1], 10, 64)
		if err != nil {
			return nil, "", fmt.Errorf("bad size on manifest line %d: %q", i+2, line)
		}
		entries = append(entries, ManifestEntry{Name: fields[0], Size: size, MD5: fields[2]})
	}
	sum := sha256.Sum256([]byte(body.String()))
	fingerprint := hex.EncodeToString(sum[:])
	if want, _ := strconv.Atoi(header[1]); want != len(entries) || header[2] != fingerprint {
		return nil, "", fmt.Errorf("manifest damaged: header says %s files sha256=%s, got %d files sha256=%s",
			header[1], header[2], len(entries), fingerprint)
	}
	return entries, fingerprint, nil
}

// VerifyDownloads checks every file of the manifest is in saveDir under its exact name with the
// planned size, and the planned md5 when there is one. Contents are not unpacked: a damaged
// file shows when it is unpacked for the restore.
func VerifyDownloads(saveDir, manifestFile, fingerprint string) error {
	raw, err := os.ReadFile(filepath.Join(saveDir, manifestFile))
	if err != nil {
		return fmt.Errorf("read manifest: %v", err)
	}
	entries, got, err := ParseManifest(raw)
	if err != nil {
		return err
	}
	if fingerprint != "" && got != fingerprint {
		return fmt.Errorf("manifest %s is not the one of this plan: sha256=%s, want %s", manifestFile, got, fingerprint)
	}

	var missing, mismatched []string
	var total int64
	for _, e := range entries {
		path := filepath.Join(saveDir, e.Name)
		st, err := os.Stat(path)
		switch {
		case err != nil || st.IsDir():
			missing = append(missing, e.Name)
			continue
		case st.Size() != e.Size:
			mismatched = append(mismatched, fmt.Sprintf("%s(size want %d got %d)", e.Name, e.Size, st.Size()))
			continue
		}
		if e.MD5 != "" && e.MD5 != manifestNoMD5 {
			sum, err := fileMD5(path)
			if err != nil {
				return err
			}
			if !strings.EqualFold(sum, e.MD5) {
				mismatched = append(mismatched, fmt.Sprintf("%s(md5 want %s got %s)", e.Name, e.MD5, sum))
				continue
			}
		}
		total += e.Size
	}
	if len(missing) > 0 || len(mismatched) > 0 {
		return fmt.Errorf("downloaded backups differ from the plan in %s: %d of %d files missing %v, "+
			"%d mismatched %v", saveDir, len(missing), len(entries), head(missing), len(mismatched), head(mismatched))
	}
	mylog.Logger.Info("verified %d downloaded files (%s) in %s against %s", len(entries), humanBytes(total),
		saveDir, manifestFile)
	return nil
}

func head(names []string) []string {
	if len(names) <= verifyListLimit {
		return names
	}
	return append(names[:verifyListLimit:verifyListLimit], fmt.Sprintf("...(+%d)", len(names)-verifyListLimit))
}

func fileMD5(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := md5.New()
	if _, err = io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
