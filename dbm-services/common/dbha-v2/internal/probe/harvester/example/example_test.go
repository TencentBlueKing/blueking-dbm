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

package example_test

import (
	"context"
	"dbm-services/common/dbha-v2/internal/probe/harvester/example"
	"testing"
)

func TestExample(t *testing.T) {
	exp := example.NewExample(example.ExampleOptionDbType("example"), example.ExampleOptionReportInterval(10))
	ctx := context.Background()

	harvestC, err := exp.Harvest(ctx)

	if err != nil {
		t.Errorf("harvest db status failed, errmsg(%v)", err)
	}

	for {
		select {
		case <-ctx.Done():
			return

		case data := <-harvestC:
			t.Logf("data:%v", data.Data)
			return
		}
	}
}
