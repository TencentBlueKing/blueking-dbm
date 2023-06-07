// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ext3check

import (
	"bufio"
	"bytes"
	"os/exec"
	"regexp"
	"strings"

	"github.com/pkg/errors"
	"golang.org/x/exp/slices"
)

func filterDirFs(dirs []string, filterFs ...string) (ftDirs []string, err error) {
	splitR := regexp.MustCompile(`\s+`)

	for _, dir := range dirs {
		var stdout, stderr bytes.Buffer
		cmd := exec.Command("df", "-P", "-T", dir)
		cmd.Stdout = &stdout
		cmd.Stderr = &stderr
		err = cmd.Run()
		if err != nil {
			return nil, errors.Wrapf(err, "df -P %s: %s", dir, stderr.String())
		}

		var lines []string
		scanner := bufio.NewScanner(strings.NewReader(stdout.String()))
		for scanner.Scan() {
			lines = append(lines, scanner.Text())
			err := scanner.Err()
			if err != nil {
				return nil, errors.Wrap(err, "scan failed")
			}
		}

		if len(lines) != 2 {
			err = errors.Errorf("parse df result failed: %s", stdout.String())
			return nil, err
		}

		splitLine := splitR.Split(lines[1], -1)
		if len(splitLine) != 7 {
			err = errors.Errorf("unexpect df output line: %s", lines[1])
			return nil, err
		}

		if slices.Index(filterFs, splitLine[1]) >= 0 {
			ftDirs = append(ftDirs, dir)
		}
	}

	return ftDirs, nil
}
