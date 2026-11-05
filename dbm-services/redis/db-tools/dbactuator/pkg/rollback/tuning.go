// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

// Tuning is what an engine changes in a temp instance's redis.conf for the replay. The directives
// are written once the conf is rendered and before the instance starts, and stay for its life:
// nothing is turned back after the replay.
type Tuning interface {
	Name() string
	// Directives are the redis.conf lines to set; writeBufferMB 0 keeps the template's values.
	Directives(writeBufferMB int) map[string]string
}

// plusTuning only raises the write buffer: fewer, larger flushes cut the replay's write
// amplification. Compaction and the WAL stay on, so a failed replay can still resume from
// binlogpos and the instance needs no settling afterwards. The buffer is only read when the
// kvstores open, so it cannot be set at runtime. New plans send 128MB; each kvstore holds up to
// two buffers in memory, which PlusMemory reads back from the tuned conf for the memory window,
// as the flow's precheck counts them (plus_host_memory) before anything is downloaded.
type plusTuning struct{}

func (plusTuning) Name() string { return "tendisplus" }

func (plusTuning) Directives(writeBufferMB int) map[string]string {
	if writeBufferMB <= 0 {
		return nil
	}
	return map[string]string{"rocks.write_buffer_size": strconv.FormatInt(int64(writeBufferMB)<<20, 10)}
}

type cacheTuning struct{}

func (cacheTuning) Name() string { return "cache" }

func (cacheTuning) Directives(int) map[string]string { return nil }

// ssdTuning changes nothing yet; TendisSSD's rocksdb_* values are left to a later change.
type ssdTuning struct{}

func (ssdTuning) Name() string { return "tendisssd" }

func (ssdTuning) Directives(int) map[string]string { return nil }

// tuningText is directives as "name=value" in name order, for the summaries.
func tuningText(directives map[string]string) string {
	names := make([]string, 0, len(directives))
	for name := range directives {
		names = append(names, name)
	}
	sort.Strings(names)
	parts := make([]string, 0, len(names))
	for _, name := range names {
		parts = append(parts, name+"="+directives[name])
	}
	return strings.Join(parts, " ")
}

// applyTuning writes the tuning's directives into each port's redis.conf.
func (j Job) applyTuning(ports []int) error {
	if j.tuning == nil {
		return nil
	}
	directives := j.tuning.Directives(j.WriteBufferMB)
	if len(directives) == 0 {
		return nil
	}
	for _, port := range ports {
		conf := confFile(j.Host.InstanceDir(port))
		raw, err := os.ReadFile(conf)
		if err != nil {
			return fmt.Errorf("tune %s: %v", conf, err)
		}
		content := string(raw)
		for name, value := range directives {
			content = renderDirective(content, name, value)
		}
		// Writing over the rendered conf keeps the owner Prepare gave it.
		if err = os.WriteFile(conf, []byte(content), 0644); err != nil {
			return err
		}
	}
	return nil
}

// tuningSummary is the tuning a port runs with, empty when it keeps the template.
func (j Job) tuningSummary() string {
	if j.tuning == nil {
		return ""
	}
	return tuningText(j.tuning.Directives(j.WriteBufferMB))
}
