/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package ghost

import (
	"fmt"
	"strings"
)

type backendMigrationFailure struct {
	serverName string
	host       string
	port       int
	dbName     string
	err        error
}

func (f backendMigrationFailure) format() string {
	return fmt.Sprintf("%s(%s:%d) db=%s err=%v", f.serverName, f.host, f.port, f.dbName, f.err)
}

func (f backendMigrationFailure) wrappedError() error {
	return fmt.Errorf("%s(%s:%d) db=%s: %w", f.serverName, f.host, f.port, f.dbName, f.err)
}

type onlineDDLSummaryError struct {
	summary  string
	failures []backendMigrationFailure
}

func (e *onlineDDLSummaryError) Error() string {
	return e.summary
}

func (e *onlineDDLSummaryError) Unwrap() []error {
	errs := make([]error, 0, len(e.failures))
	for _, failure := range e.failures {
		errs = append(errs, failure.wrappedError())
	}
	return errs
}

func formatOnlineDDLSummary(total int, dbName, tableName string, failures []backendMigrationFailure) string {
	var summary strings.Builder
	fmt.Fprintf(
		&summary,
		"online ddl summary: total=%d success=%d failed=%d db=%s table=%s",
		total,
		total-len(failures),
		len(failures),
		dbName,
		tableName,
	)
	for _, failure := range failures {
		fmt.Fprintf(&summary, "\n  FAILED: %s", failure.format())
	}
	return summary.String()
}

func newOnlineDDLSummaryError(
	total int,
	dbName, tableName string,
	failures []backendMigrationFailure,
) error {
	if len(failures) == 0 {
		return nil
	}
	return &onlineDDLSummaryError{
		summary:  formatOnlineDDLSummary(total, dbName, tableName, failures),
		failures: failures,
	}
}
