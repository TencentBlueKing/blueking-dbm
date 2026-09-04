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
	"testing"

	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// snapshotForTest captures current harvester registry state and returns a restore func.
func snapshotForTest() func() {
	registryMu.Lock()
	defer registryMu.Unlock()

	reg := make(map[string]Entry, len(registry))
	for k, v := range registry {
		reg[k] = v
	}
	order := make([]string, len(regOrder))
	copy(order, regOrder)

	return func() {
		registryMu.Lock()
		defer registryMu.Unlock()
		registry = reg
		regOrder = order
	}
}

func stubFactory() (plugin.Plugin, error) { return nil, nil }

func TestRegisterNormalizedDuplicatePanics(t *testing.T) {
	t.Cleanup(snapshotForTest())

	Register(Entry{
		BlockName: "CamelCaseBlock",
		DbType:    haprobe.DbTypeEs,
		Factory:   stubFactory,
	})
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic on normalized duplicate BlockName")
		}
	}()
	Register(Entry{
		BlockName: "camelcaseblock",
		DbType:    haprobe.DbTypeHdfs,
		Factory:   stubFactory,
	})
}
