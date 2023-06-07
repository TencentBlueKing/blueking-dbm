// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlerrlog

import (
	"strings"

	"github.com/dlclark/regexp2"
	"golang.org/x/exp/slog"
)

func scanSnapShot(name string, pattern *regexp2.Regexp) (string, error) {
	slog.Debug("scan err log", slog.String("name", name), slog.String("pattern", pattern.String()))
	scanner, err := loadSnapShot()
	if err != nil {
		return "", err
	}

	var lines []string
	for scanner.Scan() {
		line := scanner.Text()
		err := scanner.Err()
		if err != nil {
			slog.Error("scan err log", err, slog.String("item", name))
			return "", err
		}
		slog.Debug("scan err log", slog.String("line", line))

		match, err := pattern.MatchString(line)
		if err != nil {
			slog.Error(
				"apply pattern", err,
				slog.String("item", name), slog.String("pattern", pattern.String()),
			)
		}
		slog.Debug("scan err log", slog.Any("match", match))

		if match {
			lines = append(lines, line)
		}
	}

	return strings.Join(lines, "\n"), nil
}
