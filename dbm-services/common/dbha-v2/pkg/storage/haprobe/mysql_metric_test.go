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

package haprobe_test

import (
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"encoding/json"
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestMySQLMetric(t *testing.T) {

	msqlMetric := &haprobe.MySQLMetric{}

	msqlMetric.SequenceID = 0
	msqlMetric.ServiceID = uuid.New().String()
	msqlMetric.MessageID = uuid.New().String()
	msqlMetric.MachineID = uuid.New().String()
	msqlMetric.ReportTimestamp = uint64(time.Now().Unix())

	msqlMetric.Host = &haprobe.HostMetric{}
	msqlMetric.Databases = make([]*haprobe.DatabaseMetric, 1)
	msqlMetric.Databases = append(msqlMetric.Databases, &haprobe.DatabaseMetric{
		ListenPort: 3306,
	})

	data, err := json.Marshal(&msqlMetric)
	if err != nil {
		t.Fatalf("marshal failed, %v", err)
	}

	t.Logf("generated data:%s", string(data))
}
