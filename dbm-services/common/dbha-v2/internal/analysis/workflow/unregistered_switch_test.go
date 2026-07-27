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

package workflow

import (
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Unregistered DbTypes must be skipped (warn + return) without panicking.
func TestTriggerSwitching_UnregisteredDbTypeSkipped(t *testing.T) {
	prev := config.Cfg.Workflow.EnableSwitching
	config.Cfg.Workflow.EnableSwitching = true
	t.Cleanup(func() { config.Cfg.Workflow.EnableSwitching = prev })

	e := &SwitchExecutor{
		switchers:   map[haprobe.DbType]switcher.Switcher{}, // empty: nothing registered
		myServiceID: "test-service",
	}
	req := &switcher.Request{DbType: haprobe.DbTypeKafka, SwitchID: "sw-unregistered"}

	// Must not panic; unregistered type is a no-op skip.
	e.TriggerSwitching(haprobe.DbTypeKafka, req, nil)
}
