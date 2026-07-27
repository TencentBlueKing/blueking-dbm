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

package parser

import (
	"encoding/json"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type stubProcesser struct{}

func (stubProcesser) Process(json.RawMessage) (*haprobe.DbEvent, error) { return nil, nil }

func TestRegisterDuplicatePanics(t *testing.T) {
	t.Cleanup(snapshotForTest())

	Register(haprobe.DbTypeRedis, stubProcesser{})
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic on duplicate Register")
		}
	}()
	Register(haprobe.DbTypeRedis, stubProcesser{})
}

func TestRegisterNilPanics(t *testing.T) {
	t.Cleanup(snapshotForTest())

	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic on nil Processer")
		}
	}()
	Register(haprobe.DbTypeRedis, nil)
}

func TestRegisterInvalidDbTypePanics(t *testing.T) {
	t.Cleanup(snapshotForTest())

	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic on invalid DbType")
		}
	}()
	Register(haprobe.DbTypeNone, stubProcesser{})
}

func TestMySqlRegistered(t *testing.T) {
	if _, ok := Lookup(haprobe.DbTypeMySql); !ok {
		t.Fatal("mysql processer not registered")
	}
}
