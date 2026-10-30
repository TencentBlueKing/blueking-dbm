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

// Package migrator migrates Admin schema and data with explicit, idempotent steps.
package migrator

import (
	"fmt"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
)

// Run migrates every configured storage endpoint. Failures return a non-nil error.
func Run(opts Options) error {
	if !opts.RunsInventory() && !opts.ValidType() {
		return gerrors.Newf(
			gerrors.InvalidParameter,
			"unknown migrate type: %s; supported types: schema, data, all",
			opts.Type,
		)
	}

	// Reject a broken catalog before touching any endpoint.
	if _, err := assembledSteps(); err != nil {
		return err
	}

	stores, err := openConfigured()
	if err != nil {
		return err
	}

	return run(opts, stores)
}

// openConfigured builds one Store per endpoint declared in the storage config.
func openConfigured() ([]Store, error) {
	storage := config.Cfg.Storage
	if storage.Endpoint == "" || storage.User == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "storage endpoint and user are required")
	}

	endpoints, err := hanet.NewEndpoints(storage.Endpoint)
	if err != nil {
		return nil, err
	}

	stores := make([]Store, 0, len(endpoints))
	for _, endpoint := range endpoints {
		stores = append(stores, newMySQLStore(
			endpoint.Proto, endpoint.Host, endpoint.Port, storage.User, storage.Password,
		))
	}

	if len(stores) == 0 {
		return nil, fmt.Errorf("storage endpoint is empty")
	}

	return stores, nil
}
