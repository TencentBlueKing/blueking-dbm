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

package probe

import (
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
)

// pluginFactory creates a harvester plugin from the current config.
type pluginFactory func() (plugin.Plugin, error)

// pluginEntry binds a dbType name to its plugin factory.
type pluginEntry struct {
	name    string
	factory pluginFactory
}

// pluginEntries enumerates all harvester plugins to be started by Probe.
// Factories read config.Cfg lazily at call time, so package-level definition is safe.
// Each factory returns (nil, nil) when its corresponding cfg block is absent so probe
// won't start a plugin with a nil cfg (which would panic on Harvest at m.cfg.Interval).
var pluginEntries = []pluginEntry{
	{
		name: "mysql",
		factory: func() (plugin.Plugin, error) {
			if config.Cfg.Harvester.MySql == nil {
				return nil, nil
			}
			return harvester.NewPluginMySql(config.Cfg.Harvester.MySql)
		},
	},
	{
		name: "mysqlProxyAdmin",
		factory: func() (plugin.Plugin, error) {
			if config.Cfg.Harvester.MySqlProxyAdmin == nil {
				return nil, nil
			}
			return harvester.NewPluginMySqlProxyAdmin(config.Cfg.Harvester.MySqlProxyAdmin)
		},
	},
	{
		name: "redis",
		factory: func() (plugin.Plugin, error) {
			if config.Cfg.Harvester.Redis == nil {
				return nil, nil
			}
			return harvester.NewPluginRedis(config.Cfg.Harvester.Redis)
		},
	},
}
