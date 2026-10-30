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

package migrator

import (
	"fmt"

	"dbm-services/common/dbha-v2/pkg/logger"
)

// lockAll acquires the advisory lock on every target in order.
// It returns the stores it attempted so the caller can release them.
func lockAll(stores []Store) ([]Store, error) {
	attempted := make([]Store, 0, len(stores))
	for _, store := range stores {
		attempted = append(attempted, store)
		if err := store.Lock(); err != nil {
			return attempted, fmt.Errorf("migrate lock failed, endpoint: %s, errmsg: %w", store.Endpoint(), err)
		}
	}

	return attempted, nil
}

// unlockAll releases locks in reverse order, logging but never failing.
func unlockAll(stores []Store) {
	for i := len(stores) - 1; i >= 0; i-- {
		if err := stores[i].Unlock(); err != nil {
			logger.Warn("release migrate lock failed, endpoint: %s, errmsg: %s", stores[i].Endpoint(), err)
		}
	}
}

// precheckAll refuses to start when any endpoint cannot be migrated safely.
func precheckAll(stores []Store, opts Options) error {
	for _, store := range stores {
		snap, err := store.Load()
		if err != nil {
			return precheckError(store, err)
		}
		if err = store.ProbeFacts(snap, factScope{}); err != nil {
			return precheckError(store, err)
		}
		if opts.RunsSchema() {
			if err = probeStepData(store, snap); err != nil {
				return precheckError(store, err)
			}
		}
		if err = validateWrite(snap, opts); err != nil {
			return precheckError(store, err)
		}
	}

	return nil
}

// precheckError wraps a precheck failure with the endpoint it happened on.
func precheckError(store Store, err error) error {
	return fmt.Errorf("precheck failed, endpoint: %s, errmsg: %w", store.Endpoint(), err)
}

// validateWrite checks server state and blockers before any write.
// Privileges are not prechecked: a missing privilege fails the statement that needs it.
func validateWrite(snap *Snapshot, opts Options) error {
	if snap.ReadOnly || snap.SuperReadOnly {
		return fmt.Errorf("server is read only")
	}
	if !snap.VersionOK {
		return fmt.Errorf("database version unavailable")
	}
	if !snap.LedgerSchemaOK || !snap.LedgerDataOK {
		return fmt.Errorf("migration ledger conflict")
	}

	if opts.RunsSchema() {
		if err := schemaBlocker(snap, opts); err != nil {
			return err
		}
	}

	if opts.RunsData() && !opts.RunsSchema() && (!snap.Database || !strategyReady(snap)) {
		return fmt.Errorf("strategy table is not ready")
	}

	return nil
}
