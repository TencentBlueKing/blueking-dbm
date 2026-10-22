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
	"context"
	"database/sql"
	"fmt"
)

func (s *mysqlStore) ApplyStrategies(repair bool) error {
	snap, err := s.Load()
	if err != nil {
		return err
	}
	if !strategyReady(snap) {
		return fmt.Errorf("strategy table is not ready")
	}
	empty, hits, err := s.defaultStrategyHits()
	if err != nil {
		return err
	}
	plan := planDefaultStrategies(empty, hits, repair)
	logStrategyActions(s.Endpoint(), plan.Actions)
	if !plan.Complete {
		return nil
	}
	if err = s.EnsureDataLedger(); err != nil {
		return err
	}
	return s.writeStrategyPlan(plan)
}

func (s *mysqlStore) defaultStrategyHits() (bool, map[string]strategyHit, error) {
	empty, err := s.strategyTableEmpty()
	if err != nil || empty {
		return empty, nil, err
	}
	hits := map[string]strategyHit{}
	for _, seed := range defaultStrategies() {
		hit, err := s.oneStrategyHit(seed)
		if err != nil {
			return false, nil, err
		}
		hits[strategyIdentity(seed)] = hit
	}
	return false, hits, nil
}

func (s *mysqlStore) strategyTableEmpty() (bool, error) {
	var one int
	err := s.conn.QueryRowContext(
		context.Background(), "SELECT 1 FROM `t_db_switching_strategy` LIMIT 1",
	).Scan(&one)
	if err == sql.ErrNoRows {
		return true, nil
	}
	return false, err
}

func (s *mysqlStore) oneStrategyHit(seed strategySeed) (strategyHit, error) {
	var status sql.NullString
	var deleted sql.NullTime
	err := s.conn.QueryRowContext(context.Background(),
		"SELECT status, deleted_at FROM `t_db_switching_strategy` "+
			"WHERE bk_biz_id = ? AND trigger_event_name = ? LIMIT 1",
		seed.BkBizID, seed.Event,
	).Scan(&status, &deleted)
	if err == sql.ErrNoRows {
		return strategyHit{}, nil
	}
	if err != nil {
		return strategyHit{}, err
	}
	return strategyHit{Found: true, Status: status.String, Deleted: deleted.Valid}, nil
}

func (s *mysqlStore) writeStrategyPlan(plan strategyPlan) error {
	tx, err := s.conn.BeginTx(context.Background(), nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	for _, seed := range plan.Insert {
		if err = insertStrategy(tx, seed); err != nil {
			return err
		}
	}
	if err = insertLedger(tx, dataVersion, dataName, strategySchemaVersion()); err != nil {
		return err
	}
	return tx.Commit()
}

func insertStrategy(tx *sql.Tx, seed strategySeed) error {
	_, err := tx.ExecContext(context.Background(),
		"INSERT INTO `t_db_switching_strategy` "+
			"(status, name, bk_biz_id, trigger_event_name, trigger_event_name_reason, "+
			"trigger_count, priority, scope, action, description, created_at, updated_at) "+
			"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', NOW(), NOW())",
		seed.Status, seed.Name, seed.BkBizID, seed.Event, seed.Reason,
		seed.Count, seed.Priority, seed.Scope, seed.Action,
	)
	return err
}

func insertLedger(tx *sql.Tx, version int64, name string, required int64) error {
	var existing string
	err := tx.QueryRowContext(context.Background(),
		"SELECT name FROM `dbha_data_migrations` WHERE version = ?", version,
	).Scan(&existing)
	if err == nil {
		if existing != name {
			return fmt.Errorf("data ledger name conflict, version: %d", version)
		}
		return nil
	}
	if err != sql.ErrNoRows {
		return err
	}
	_, err = tx.ExecContext(context.Background(),
		"INSERT INTO `dbha_data_migrations` (version, name, required_schema_version, applied_at) "+
			"VALUES (?, ?, ?, NOW())",
		version, name, required,
	)
	return err
}
