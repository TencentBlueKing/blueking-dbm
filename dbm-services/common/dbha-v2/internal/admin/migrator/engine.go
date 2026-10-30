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
	"sort"
	"strconv"

	"dbm-services/common/dbha-v2/pkg/logger"
)

// run drives one migrate invocation over every distinct physical server.
func run(opts Options, stores []Store) error {
	if err := validateOptions(opts); err != nil {
		return err
	}

	targets, err := orderStores(stores)
	if err != nil {
		unlockAll(stores)
		return err
	}

	// Lock in a deterministic order; release everything on the way out.
	attempted, err := lockAll(targets.migrate)
	defer releaseTargets(attempted, targets.migrate[len(attempted):], targets.aliases)
	if err != nil {
		return err
	}

	if opts.RunsInventory() {
		return inventory(targets.migrate, opts)
	}

	if err = precheckAll(targets.migrate, opts); err != nil {
		return err
	}

	for _, store := range targets.migrate {
		if err = applyOne(store, opts); err != nil {
			return err
		}
	}

	return nil
}

// storePair binds one endpoint to the server identity it belongs to.
type storePair struct {
	id    Identity
	store Store
}

// storeTargets splits endpoints into the ones to migrate and their read-only aliases.
type storeTargets struct {
	migrate []Store
	aliases []Store
}

// orderStores resolves identities and sorts endpoints by a process-stable key.
func orderStores(stores []Store) (storeTargets, error) {
	pairs := make([]storePair, 0, len(stores))
	for _, store := range stores {
		id, err := store.Identity()
		if err != nil {
			return storeTargets{}, fmt.Errorf("read server identity failed, endpoint: %s, errmsg: %w", store.Endpoint(), err)
		}
		if id.ServerUUID == "" {
			return storeTargets{}, fmt.Errorf("server identity unavailable, endpoint: %s", store.Endpoint())
		}
		pairs = append(pairs, storePair{id: id, store: store})
	}

	sort.SliceStable(pairs, func(i, j int) bool { return pairs[i].id.Key() < pairs[j].id.Key() })

	return dedupStores(pairs)
}

// dedupStores keeps one migrate target per physical server; duplicates become aliases.
func dedupStores(pairs []storePair) (storeTargets, error) {
	seen := map[string]Identity{}
	seenFallback := map[string]bool{}
	targets := storeTargets{
		migrate: make([]Store, 0, len(pairs)),
		aliases: make([]Store, 0, len(pairs)),
	}
	for _, pair := range pairs {
		// No server uuid: fall back to server_id, host, and port, and warn once per server.
		// Containers often share a host name and port, so server_id keeps distinct servers apart.
		if pair.id.Fallback {
			key := pair.id.ServerUUID + "|" + pair.id.Hostname + "|" + strconv.Itoa(pair.id.Port)
			if seenFallback[key] {
				logger.Warn("reuse connection for same fallback identity, endpoint: %s, server_id: %s",
					pair.store.Endpoint(), pair.id.ServerUUID)
				targets.aliases = append(targets.aliases, pair.store)
				continue
			}
			logger.Warn("server uuid unavailable, endpoint: %s", pair.store.Endpoint())
			seenFallback[key] = true
			targets.migrate = append(targets.migrate, pair.store)
			continue
		}

		// Same uuid must always resolve to the same host and port.
		prev, ok := seen[pair.id.ServerUUID]
		if ok && (prev.Hostname != pair.id.Hostname || prev.Port != pair.id.Port) {
			return storeTargets{}, fmt.Errorf("server identity conflict, server_uuid: %s", pair.id.ServerUUID)
		}
		if ok {
			logger.Info("reuse connection for same server, endpoint: %s", pair.store.Endpoint())
			targets.aliases = append(targets.aliases, pair.store)
			continue
		}
		seen[pair.id.ServerUUID] = pair.id
		targets.migrate = append(targets.migrate, pair.store)
	}

	return targets, nil
}

// validateOptions rejects flag combinations that cannot be honored.
func validateOptions(opts Options) error {
	if opts.RunsInventory() {
		if opts.RepairMissing || opts.RepairMissingSchema || opts.RepairMissingData {
			return fmt.Errorf("inventory cannot be combined with repair")
		}
		return nil
	}

	if !opts.ValidType() {
		return fmt.Errorf(
			"unknown migrate type: %s; supported types: schema, data, all",
			opts.Type,
		)
	}

	if opts.Type == MigrateTypeSchema && opts.RepairMissingData {
		return fmt.Errorf("schema migrate cannot be combined with repair-missing-data")
	}

	if opts.Type == MigrateTypeData && opts.RepairMissingSchema {
		return fmt.Errorf("data migrate cannot be combined with repair-missing-schema")
	}

	return nil
}

// releaseTargets unlocks every store, including the ones never locked.
func releaseTargets(attempted, remaining, aliases []Store) {
	unlockAll(attempted)
	unlockAll(remaining)
	unlockAll(aliases)
}
