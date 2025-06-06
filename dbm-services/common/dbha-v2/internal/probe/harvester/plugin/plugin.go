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

package plugin

import (
	"context"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// Options the options of a plugin
type Options struct {
}

// HarvestData harvst data from a db
type HarvestData struct {
	Data interface{} `json:"data"`
}

// Plugin probe plugin interface
type Plugin interface {
	Name() (string, error)
	Version() (string, error)
	Harvest(ctx context.Context, opt *Options) (chan *HarvestData, error)
	Close() error
}

// UnimplementedMethod the default methods of a plugin.
//
// When new interface methods are added to the Plugin,
// it ensures backwards compatibility for all plugins whithout immediate updates,
// and also avoids panics when some methods are not implemented, instread returning a clear error.
type UnimplementedMethod struct {
}

func (u *UnimplementedMethod) Name() (string, error) {
	return "unknow", gerrors.New(gerrors.Unimplemented, "unimplemented method")
}

func (u *UnimplementedMethod) Version() (string, error) {
	return "unknow", gerrors.New(gerrors.Unimplemented, "unimplemented method")
}

func (u *UnimplementedMethod) Harvest(ctx context.Context, opt *Options) (chan *HarvestData, error) {
	return nil, gerrors.New(gerrors.Unimplemented, "unimplemented method")
}

func (u *UnimplementedMethod) Close() error {
	return gerrors.New(gerrors.Unimplemented, "unimplemented method")
}
