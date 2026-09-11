/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// Package mysqlswitch registers the MySQL switcher, alarm event names, special strategy
// matchers, and DNS single-address guards.
package mysqlswitch

import (
	"dbm-services/common/dbha-v2/internal/analysis/failure"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func init() {
	switcher.Register(haprobe.DbTypeMySql, func() switcher.Switcher {
		return &Mysql{}
	})
	dbtype.RegisterSwitchAlarmEvents(haprobe.DbTypeMySql, dbtype.SwitchAlarmEvents{
		Success: haprobe.DbEventNameMysqlSwitchSuccessV1,
		Failure: haprobe.DbEventNameMysqlSwitchFailureV1,
	})
	failure.RegisterSpecialMatch(
		haprobe.DbEventNameTendbhaProxyBackendFailure,
		MatchProxyBackendSimultaneous,
	)
	failure.RegisterSpecialMatch(
		haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
		MatchSpiderRemoteMasterSimultaneous,
	)
	dbtype.RegisterDnsSingleAddressGuard(
		haprobe.DbmMetadataMachineTypeProxy,
		haprobe.DbmMetadataMachineTypeSpider,
	)
}
