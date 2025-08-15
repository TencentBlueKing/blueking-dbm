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

package machine_test

import (
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/machine"
)

func TestSnowflake(t *testing.T) {
	id, err := machine.ID()
	if err != nil {
		t.Fatalf("failed to generate machine-id, %v", err)
	}

	idHash := machine.Hash(id, 10)

	t.Logf("machine-id:%s machine-id hash:%d", id, idHash)

	sf, err := machine.NewSnowflake(idHash, time.Now())
	if err != nil {
		t.Fatalf("failed to create snowflake, %v", err)
	}

	for i := 0; i < 10; i++ {
		id, err := sf.NextID()
		if err != nil {
			t.Fatalf("failed to create snowflake id, %v", err)
		}

		ts, mid, seq := sf.ParseID(id)
		t.Logf("id:%d timestamp:%d, machine-id:%d, seq:%d", id, ts, mid, seq)
	}
}
