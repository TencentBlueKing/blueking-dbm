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

package credential

import (
	"context"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/dbcred"
)

func TestConfigure(t *testing.T) {
	r := &resolver{}

	if err := r.Configure(func(name string) (dbcred.DbmApi, bool) {
		if name != dbmApiNameQueryRedisPassword {
			t.Fatalf("unexpected api name: %s", name)
		}
		return dbcred.DbmApi{Api: "http://127.0.0.1:1", Token: "t", Timeout: time.Second}, true
	}); err != nil {
		t.Fatalf("Configure failed, errmsg: %s", err)
	}

	if err := r.Configure(func(string) (dbcred.DbmApi, bool) {
		return dbcred.DbmApi{}, false
	}); err == nil {
		t.Fatal("expected error when the api name is not configured")
	}
}

func TestFillEmpty(t *testing.T) {
	r := &resolver{}
	if err := r.Fill(context.Background(), 0, nil); err != nil {
		t.Fatalf("Fill empty must return nil, got: %v", err)
	}
}
