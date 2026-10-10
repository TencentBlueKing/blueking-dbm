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

	"dbm-services/common/dbha-v2/pkg/dbtype"
)

func TestRegistryKeysNormalized(t *testing.T) {
	registryMu.RLock()
	defer registryMu.RUnlock()
	for key := range registry {
		if got := dbtype.NormalizeBlockName(key); got != key {
			t.Errorf("registry key %q is not normalized, want %q", key, got)
		}
	}
	for _, key := range regOrder {
		if got := dbtype.NormalizeBlockName(key); got != key {
			t.Errorf("regOrder entry %q is not normalized, want %q", key, got)
		}
		if _, ok := registry[key]; !ok {
			t.Errorf("regOrder entry %q missing from registry", key)
		}
	}
}
