// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlprocesslist

import (
	"strings"

	"github.com/dlclark/regexp2"
	"golang.org/x/exp/slog"
)

func mysqlInject() (string, error) {
	processList, err := loadSnapShot()
	if err != nil {
		return "", err
	}

	var injects []string
	for _, p := range processList {
		pstr, err := p.JsonString()
		if err != nil {
			return "", err
		}

		slog.Debug("mysql inject check process", slog.Any("process", pstr))

		if strings.ToLower(p.User.String) == "system user" {
			continue
		}

		hasSleep, err := hasLongUserSleep(p)
		if err != nil {
			return "", err
		}
		slog.Debug("mysql inject check process", slog.Bool("has user sleep", hasSleep))

		isLongSleep := hasSleep && p.Time.Int64 > 300
		slog.Debug("mysql inject check process", slog.Bool("is long sleep", isLongSleep))

		hasComment, err := hasCommentInQuery(p)
		if err != nil {
			return "", err
		}
		slog.Debug("mysql inject check process", slog.Bool("has inline comment", hasComment))

		if isLongSleep || hasComment {
			injects = append(injects, pstr)
		}
	}
	return strings.Join(injects, ","), nil
}

func hasLongUserSleep(p *mysqlProcess) (bool, error) {
	re := regexp2.MustCompile(`User sleep`, regexp2.IgnoreCase)
	match, err := re.MatchString(p.State.String)
	if err != nil {
		slog.Error("check long user sleep", err)
		return false, err
	}

	return match, nil
}

func hasCommentInQuery(p *mysqlProcess) (bool, error) {
	re := regexp2.MustCompile(`\s+#`, regexp2.IgnoreCase)
	match, err := re.MatchString(p.Command.String)
	if err != nil {
		slog.Error("check comment in query", err)
		return false, err
	}

	return match &&
			(strings.HasPrefix(strings.ToLower(p.Command.String), "update") ||
				strings.HasPrefix(strings.ToLower(p.Command.String), "delete")),
		nil
}
