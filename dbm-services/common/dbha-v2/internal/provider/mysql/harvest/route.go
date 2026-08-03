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

package harvest

import (
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func init() {
	dbtype.RegisterEndpointRouter(haprobe.DbTypeMySql, routeMySQLEndpoint)
}

// routeMySQLEndpoint implements TendbHA mysql-proxy dual-produce and the default
// mysql block route for other MySQL-family endpoints.
func routeMySQLEndpoint(attrs dbtype.EndpointAttrs) []dbtype.EndpointRoute {
	isProxy := attrs.AccessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		attrs.MachineType == haprobe.DbmMetadataMachineTypeProxy
	if !isProxy {
		return []dbtype.EndpointRoute{{
			BlockName: config.HarvesterBlockMySQL,
			Ports:     dbtype.PortKindAll,
		}}
	}

	if len(attrs.AdminPorts) == 0 {
		logger.Info(
			"skip mysql-proxy endpoint without admin ports, ip: %s, data_ports: %v",
			attrs.Ip, attrs.Ports,
		)
		return nil
	}

	return []dbtype.EndpointRoute{
		{BlockName: config.HarvesterBlockMySQLProxyAdmin, Ports: dbtype.PortKindAdmin},
		{BlockName: config.HarvesterBlockMySQL, Ports: dbtype.PortKindData},
	}
}
