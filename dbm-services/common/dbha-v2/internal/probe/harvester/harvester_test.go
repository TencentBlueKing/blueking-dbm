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

package harvester_test

import (
	"dbm-services/common/dbha-v2/internal/probe/harvester"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"encoding/json"
	"sync"
	"testing"
	"time"

	"golang.org/x/net/context"
)

func TestPlugins(t *testing.T) {
	ctx, _ := context.WithTimeout(context.Background(), 1*time.Minute)
	var wg sync.WaitGroup

	for _, p := range harvester.Plugins {
		wg.Add(1)
		go func(ctx context.Context, p plugin.Plugin) {
			defer wg.Done()
			dataC, err := p.Harvest(ctx)
			if err != nil {
				t.Errorf("harvest failed, errmsg:%v", err)
			}

			name, _ := p.Name()
			version, _ := p.Version()

			for {
				select {
				case <-ctx.Done():
					p.Close()
					return

				case data := <-dataC:
					value, err := json.Marshal(data)
					if err != nil {
						t.Errorf("failed, plugin:%s, version:%s errmsg:%v", name, version, err)
						continue
					}
					t.Log("plugin:", name, "version:", version, "data:", string(value))
				}
			}
		}(ctx, p)
	}

	wg.Wait()
	t.Log("Plugin Test Finished")
}
