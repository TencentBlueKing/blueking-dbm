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

// Package harvester wires concrete plugin constructors (mysql / mysqlProxyAdmin / redis)
// under one importable surface so probe.loadPlugins doesn't depend on individual
// harvester subpackages directly.
package harvester

import (
	"dbm-services/common/dbha-v2/internal/probe/harvester/mysql"
	"dbm-services/common/dbha-v2/internal/probe/harvester/redis"
)

var (
	// NewPluginMySql To avoid potential ambiguity caused by directly using 'mysql',
	// the method for creating the mysql plugin has been renamed here.
	NewPluginMySql = mysql.NewMySql
	// NewPluginMySqlProxyAdmin creates a MySQL plugin instance dedicated to TendbHA mysql-proxy
	// admin ports; the instance name is "mysqlProxyAdmin" so logs distinguish it from NewPluginMySql.
	NewPluginMySqlProxyAdmin = mysql.NewMySqlProxyAdmin
	NewPluginRedis           = redis.NewRedis
)
