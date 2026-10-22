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

	"dbm-services/common/dbha-v2/pkg/logger"
)

func run(opts Options, stores []Store) error {
	if !opts.Inventory && !opts.ValidType() {
		return fmt.Errorf("unknown migrate type: %s", opts.Type)
	}
	targets, err := orderStores(stores)
	if err != nil {
		unlockAll(stores)
		return err
	}
	attempted, err := lockAll(targets.migrate)
	defer releaseTargets(attempted, targets.migrate[len(attempted):], targets.aliases)
	if err != nil {
		return err
	}
	if opts.Inventory {
		return inventory(targets.migrate)
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

type storePair struct {
	id    Identity
	store Store
}

type storeTargets struct {
	migrate []Store
	aliases []Store
}

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

func dedupStores(pairs []storePair) (storeTargets, error) {
	seen := map[string]Identity{}
	targets := storeTargets{
		migrate: make([]Store, 0, len(pairs)),
		aliases: make([]Store, 0, len(pairs)),
	}
	for _, pair := range pairs {
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

func releaseTargets(attempted, remaining, aliases []Store) {
	unlockAll(attempted)
	unlockAll(remaining)
	unlockAll(aliases)
}
