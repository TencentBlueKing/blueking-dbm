// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ibdstatistic

import (
	"fmt"
	"io/fs"
	"log/slog"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
)

func (c *ibdStatistic) collectResult2(dataDir string) (map[string]int64, map[string]int64, error) {
	var err error
	dbSize := make(map[string]int64)
	tableSize := make(map[string]int64)

	for _, rule := range c.MergeRules {
		if rule == nil {
			continue
		} else if rule.To == "" {
			err = errors.Errorf("rule to cannot be empty for %s", rule.From)
			slog.Error("ibd-statistic", slog.String("error", err.Error()))
			continue
			//return nil, nil, errors.Errorf("rule to cannot be empty for %s", rule.From)
		}
		if reMergeRule, err := regexp.Compile(rule.From); err != nil {
			err = errors.WithMessage(err, "compile merge rule")
			slog.Error("ibd-statistic", slog.String("error", err.Error()))
			continue
			//return nil, nil, err
		} else {
			c.reMergeRulesFrom = append(c.reMergeRulesFrom, reMergeRule)
			c.reMergeRulesTo = append(c.reMergeRulesTo, rule.To)
		}
	}

	err = filepath.WalkDir(
		dataDir, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return fs.SkipDir
			}

			if !d.IsDir() && strings.ToLower(filepath.Ext(d.Name())) == ibdExt {
				dir := filepath.Dir(path)
				dbName := filepath.Base(dir)
				tableName := strings.TrimSuffix(d.Name(), ibdExt)

				if !c.DisableMergePartition {
					match := partitionPattern.FindStringSubmatch(d.Name())
					if match != nil {
						tableName = match[1]
					}
				}

				if len(c.reMergeRulesFrom) > 0 {
					oldDbTbName := fmt.Sprintf("%s.%s", dbName, tableName)
					for i, reMergeRule := range c.reMergeRulesFrom {
						if reMergeRule.MatchString(oldDbTbName) {
							newDbTbName := reMergeRule.ReplaceAllString(oldDbTbName, c.reMergeRulesTo[i])
							dbName, tableName, err = cmutil.GetDbTableName(newDbTbName)
							slog.Debug("merge rule matched", slog.String("rule_to", c.reMergeRulesTo[i]),
								slog.String("name_from", oldDbTbName), slog.String("name_to", newDbTbName))
							if err != nil {
								return errors.WithMessagef(err, "using merge rules to %s", c.reMergeRulesTo[i])
							}
							break
						}
					}
				}
				dbTableName := fmt.Sprintf("%s.%s", dbName, tableName)

				st, err := os.Stat(path)
				if err != nil {
					slog.Error("ibd-statistic collect result", slog.String("error", err.Error()))
					return err
				}
				if _, ok := dbSize[dbName]; !ok {
					dbSize[dbName] = 0
				}
				if _, ok := tableSize[dbTableName]; !ok {
					tableSize[dbTableName] = 0
				}
				dbSize[dbName] += st.Size()
				tableSize[dbTableName] += st.Size()
			}
			return nil
		},
	)

	if err != nil {
		slog.Error("ibd-statistic collect result", slog.String("error", err.Error()))
		return nil, nil, err
	}

	return tableSize, dbSize, nil
}
