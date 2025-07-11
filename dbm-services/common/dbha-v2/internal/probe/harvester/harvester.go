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
package harvester

import (
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/mysql"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/internal/probe/harvester/redis"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"strings"
)

// NewPlugin new plugins
func NewPlugin(cfg config.HarvesterConfig) (plugin.Plugin, error) {
	var target plugin.Plugin

	switch strings.ToLower(cfg.Name) {
	case strings.ToLower(mysql.Name):
		target = mysql.NewMySql(mysql.OptionUser(cfg.User),
			mysql.OptionHost(cfg.Host),
			mysql.OptionInstanceName(cfg.InstanceName),
			mysql.OptionPassword(cfg.Password),
			mysql.OptionReportInterval(cfg.ReportInterval),
			mysql.OptionPort(cfg.Port))

	case strings.ToLower(redis.Name):
		target = redis.NewRedis(redis.OptionReportInterval(cfg.ReportInterval))

	default:
		return nil, gerrors.Newf(gerrors.NotFound, "plugin(%s) is invalid", cfg.Name)
	}

	return target, nil
}
