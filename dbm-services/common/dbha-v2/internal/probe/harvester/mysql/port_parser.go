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

package mysql

import (
	"strings"

	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/go-pubpkg/logger"
)

const (
	portDashDelimiter = "-"
)

var (
	ErrInvalidPorts = gerrors.Newf(gerrors.InvalidParameter, "invalid ports")
)

func parsePorts(ports string) ([]int, error) {
	iports := []int{}

	if !strings.Contains(ports, portDashDelimiter) {
		port, err := converter.ToInt(ports)
		if err != nil {
			logger.Warn("failed to parse the ports: %s, errmsg: %s", ports, err)
			return nil, ErrInvalidPorts
		}

		iports = append(iports, port)
		return iports, nil
	}

	eports := strings.Split(ports, portDashDelimiter)
	if len(eports) != 2 {
		logger.Warn("invalid ports format: %s", ports)
		return nil, ErrInvalidPorts
	}

	beginPort, err := converter.ToInt(eports[0])
	if err != nil {
		logger.Warn("failed to parse the ports: %s, errmsg: %s", ports, err)
		return nil, ErrInvalidPorts
	}

	endPort, err := converter.ToInt(eports[1])
	if err != nil {
		logger.Warn("failed to parse the ports: %s, errmsg: %s", ports, err)
		return nil, ErrInvalidPorts
	}

	if endPort < beginPort {
		logger.Warn("the end port is less than the begin port, endPort: %d, beginPort: %d", endPort, beginPort)
		return nil, ErrInvalidPorts
	}

	for port := beginPort; port <= endPort; port++ {
		iports = append(iports, port)
	}

	return iports, nil
}
