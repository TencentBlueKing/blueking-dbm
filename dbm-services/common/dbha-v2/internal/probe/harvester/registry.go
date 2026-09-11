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

// Package harvester provides the probe-side plugin registry. Concrete DB
// harvester implementations live under provider/<db>/harvest and register
// themselves via Register.
package harvester

import (
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Factory creates a harvester plugin. Returning (nil, nil) means the block is
// absent / not configured and the probe should skip starting it.
type Factory func() (plugin.Plugin, error)

// Entry binds a harvester config block name to its DbType and factory.
type Entry struct {
	BlockName string
	DbType    haprobe.DbType
	Factory   Factory
}

var (
	registryMu sync.RWMutex
	registry   = map[string]Entry{}
	regOrder   []string
)

// Register adds a harvester plugin entry. Panics on duplicate BlockName or empty fields.
// Registry keys and regOrder store NormalizeBlockName(BlockName); Entry.BlockName keeps
// the original casing for logs and YAML.
func Register(e Entry) {
	if e.BlockName == "" {
		panic("harvester: refuse to register Entry with empty BlockName")
	}
	if e.Factory == nil {
		panic(fmt.Sprintf("harvester: refuse to register Entry %q with nil Factory", e.BlockName))
	}
	if e.DbType == haprobe.DbTypeNone || e.DbType == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf(
			"harvester: refuse to register Entry %q with invalid DbType: %q", e.BlockName, e.DbType,
		))
	}

	norm := dbtype.NormalizeBlockName(e.BlockName)

	registryMu.Lock()
	defer registryMu.Unlock()

	if _, exists := registry[norm]; exists {
		panic(fmt.Sprintf("harvester: duplicate BlockName registration: %s", e.BlockName))
	}
	registry[norm] = e
	regOrder = append(regOrder, norm)
}

// Entries returns registered harvester entries in registration order.
func Entries() []Entry {
	registryMu.RLock()
	defer registryMu.RUnlock()

	out := make([]Entry, 0, len(regOrder))
	for _, name := range regOrder {
		out = append(out, registry[name])
	}
	return out
}
