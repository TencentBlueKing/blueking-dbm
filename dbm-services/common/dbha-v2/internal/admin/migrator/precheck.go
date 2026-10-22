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

func lockAll(stores []Store) ([]Store, error) {
	attempted := make([]Store, 0, len(stores))
	for _, store := range stores {
		attempted = append(attempted, store)
		if err := store.Lock(); err != nil {
			return attempted, fmt.Errorf("migrate lock failed, endpoint: %s, errmsg: %s", store.Endpoint(), err)
		}
	}
	return attempted, nil
}

func unlockAll(stores []Store) {
	for i := len(stores) - 1; i >= 0; i-- {
		if err := stores[i].Unlock(); err != nil {
			logger.Warn("release migrate lock failed, endpoint: %s, errmsg: %s", stores[i].Endpoint(), err)
		}
	}
}

func inventory(stores []Store) error {
	var conflict bool
	for _, store := range stores {
		snap, err := store.LoadInventory()
		if err != nil {
			return fmt.Errorf("inventory failed, endpoint: %s, errmsg: %s", store.Endpoint(), err)
		}
		warnLegacyKeys(store.Endpoint(), snap)
		if err = store.ProbeFacts(snap); err != nil {
			return fmt.Errorf("inventory failed, endpoint: %s, errmsg: %s", store.Endpoint(), err)
		}
		class, tables, columns := classify(snap)
		logger.Info(
			"inventory, endpoint: %s, class: %s, version: %s, create_tables: %s, add_columns: %s",
			store.Endpoint(), class, versionText(snap), joinNames(tables), joinNames(columns),
		)
		for _, profile := range inventoryProfiles(snap) {
			logger.Info("inventory table, endpoint: %s, %s", store.Endpoint(), profileLine(profile))
		}
		if class == classConflict {
			conflict = true
		}
	}
	if conflict {
		return fmt.Errorf("inventory found a structural conflict")
	}
	return nil
}

func precheckAll(stores []Store, opts Options) error {
	for _, store := range stores {
		snap, err := store.Load()
		if err != nil {
			return fmt.Errorf("precheck failed, endpoint: %s, errmsg: %s", store.Endpoint(), err)
		}
		if err = store.ProbeFacts(snap); err != nil {
			return fmt.Errorf("precheck failed, endpoint: %s, errmsg: %s", store.Endpoint(), err)
		}
		if err = validateWrite(snap, opts); err != nil {
			return fmt.Errorf("precheck failed, endpoint: %s, errmsg: %s", store.Endpoint(), err)
		}
	}
	return nil
}

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
	if err := validatePrivilege(snap, opts); err != nil {
		return err
	}
	if runsSchemaWork(opts) {
		if err := schemaBlocker(snap, opts); err != nil {
			return err
		}
	}
	if opts.RunsData() && !createsTables(opts) {
		if !strategyReady(snap) {
			return fmt.Errorf("strategy table is not ready")
		}
	}
	return nil
}

func validatePrivilege(snap *Snapshot, opts Options) error {
	if opts.RunsData() && !opts.RunsSchema() && !snap.Database {
		return fmt.Errorf("strategy table is not ready")
	}
	if !snap.Database && opts.RunsSchema() && !snap.CanCreate {
		return fmt.Errorf("missing create privilege")
	}
	if !snap.CanWrite {
		return fmt.Errorf("missing migrate privilege")
	}
	return nil
}

func runsSchemaWork(opts Options) bool {
	return opts.RunsSchema() || opts.RepairMissing || opts.RepairMissingTables
}

func createsTables(opts Options) bool {
	return opts.RunsSchema() || opts.RepairMissingTables
}
