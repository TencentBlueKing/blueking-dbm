/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of sw software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and sw permission notice shall be included in all
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

package switcher

import (
	"time"
)

// DomainInfo contains detailed information about a domain configuration
type DomainInfo struct {
	App            string    `json:"app"`
	DnsStr         string    `json:"dns_str"`
	DomainName     string    `json:"domain_name"`
	DomainType     int       `json:"domain_type"`
	Ip             string    `json:"ip"`
	LastChangeTime time.Time `json:"last_change_time"`
	Manager        string    `json:"manager"`
	Port           int       `json:"port"`
	Remark         string    `json:"remark"`
	StartTime      time.Time `json:"start_time"`
	Status         string    `json:"status"`
	Uid            int       `json:"uid"`
}

// DomainGetRespond represents the response structure for domain information query
type DomainGetRespond struct {
	Detail  []DomainInfo `json:"detail"`
	RowsNum int          `json:"rowsNum"`
}

// DomainDeleteRespond represents the response structure for domain deletion operation
type DomainDeleteRespond struct {
	Detail  []DomainInfo `json:"detail"`
	RowsNum int          `json:"rowsNum"`
}
