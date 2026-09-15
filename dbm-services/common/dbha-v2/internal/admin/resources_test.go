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

package admin

import (
	"context"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
)

func TestStorageCloseWaitsForActiveRequest(t *testing.T) {
	closed := make(chan struct{})
	resource := newStorageResource(hamysql.WithGormDB(&gorm.DB{}, func() { close(closed) }))
	if !resource.acquire() {
		t.Fatal("initial acquire should succeed")
	}

	done := make(chan struct{})
	go func() {
		resource.close(context.Background())
		close(done)
	}()

	select {
	case <-closed:
		t.Fatal("database closed before active request released")
	case <-time.After(20 * time.Millisecond):
	}
	if resource.acquire() {
		t.Fatal("acquire should fail after close starts")
	}
	resource.release()

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("storage close did not finish after release")
	}
}
