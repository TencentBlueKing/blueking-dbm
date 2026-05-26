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

package switcher

import (
	"fmt"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Factory creates a switcher implementation instance.
type Factory func() Switcher

// Registry stores switcher factories by db type.
type Registry struct {
	factories map[haprobe.DbType]Factory
}

// NewRegistry creates an empty switcher registry.
func NewRegistry() *Registry {
	return &Registry{
		factories: map[haprobe.DbType]Factory{},
	}
}

// Register adds a switcher factory for the given db type.
func (r *Registry) Register(dbType haprobe.DbType, factory Factory) error {
	if factory == nil {
		return fmt.Errorf("switcher factory is nil, dbType: %s", dbType)
	}
	if _, exists := r.factories[dbType]; exists {
		return fmt.Errorf("switcher factory already registered, dbType: %s", dbType)
	}

	r.factories[dbType] = factory
	return nil
}

// BuildEnabled builds switchers with db types not in the disabled list.
func (r *Registry) BuildEnabled(disabled []haprobe.DbType) map[haprobe.DbType]Switcher {
	disabledSet := map[haprobe.DbType]struct{}{}
	for _, dbType := range disabled {
		disabledSet[dbType] = struct{}{}
	}

	switchers := map[haprobe.DbType]Switcher{}
	for dbType, factory := range r.factories {
		if _, exists := disabledSet[dbType]; exists {
			continue
		}
		switchers[dbType] = factory()
	}

	return switchers
}
