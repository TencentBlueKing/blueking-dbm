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
	"database/sql"
	"fmt"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"

	"gorm.io/gorm"
)

// ApplyStrategies reconciles the default strategies inside one transaction.
func (s *mysqlStore) ApplyStrategies(repair bool) (dataApplyResult, error) {
	snap, err := s.Load()
	if err != nil {
		return dataApplyResult{}, err
	}
	if !strategyReady(snap) {
		return dataApplyResult{}, fmt.Errorf("strategy table is not ready")
	}

	plan, err := s.PlanStrategies(snap, repair)
	if err != nil {
		return dataApplyResult{}, err
	}
	if !plan.Complete || plan.SkipWrite {
		return dataResult(plan, false), nil
	}

	if err = s.EnsureDataLedger(); err != nil {
		return dataApplyResult{}, err
	}
	if err = s.writeStrategyPlan(plan); err != nil {
		return dataApplyResult{}, err
	}

	return dataResult(plan, true), nil
}

// PlanStrategies decides what the data step would do on snap's ledger, without writing.
// It fails with a unique_conflict blocker when a strategy to insert would collide with an existing row.
func (s *mysqlStore) PlanStrategies(snap *Snapshot, repair bool) (strategyPlan, error) {
	empty, hits, err := s.defaultStrategyHits()
	if err != nil {
		return strategyPlan{}, err
	}
	plan, err := planDefaultStrategies(empty, hits, repair, ledgerFrom(snap))
	if err != nil {
		return strategyPlan{}, err
	}
	if !insertConflictsWanted(empty, plan) {
		return plan, nil
	}

	db, err := s.orm()
	if err != nil {
		return strategyPlan{}, err
	}
	for _, seed := range plan.Insert {
		if err = seedConflict(db, seed); err != nil {
			return strategyPlan{}, err
		}
	}

	return plan, nil
}

// seedConflict fails when an existing row, soft-deleted or not, holds any unique key of seed.
func seedConflict(db *gorm.DB, seed hamodel.DbSwitchingStrategy) error {
	lookups, err := strategyLookups(seed)
	if err != nil {
		return err
	}

	for _, lookup := range lookups {
		conflict, found, err := oneStrategyConflict(db, lookup)
		if err != nil {
			return err
		}
		if found {
			return uniqueConflictError(seed, conflict)
		}
	}

	return nil
}

// oneStrategyConflict reads one row holding a unique key value set; the column collation decides equality.
func oneStrategyConflict(db *gorm.DB, lookup strategyLookup) (strategyConflict, bool, error) {
	rows, err := db.Model(&hamodel.DbSwitchingStrategy{}).Unscoped().
		Select([]string{
			hamodel.DbSwitchingStrategyFieldName,
			hamodel.DbSwitchingStrategyFieldBkBizID,
			hamodel.DbSwitchingStrategyFieldTriggerEventName,
			hamodel.DbSwitchingStrategyFieldTriggerEventNameReason,
		}).
		Where(lookup.Values).Limit(1).Rows()
	if err != nil {
		return strategyConflict{}, false, err
	}
	defer rows.Close()

	if !rows.Next() {
		return strategyConflict{}, false, rows.Err()
	}
	var name, event sql.NullString
	var bkBizID, reason sql.NullInt64
	if err = rows.Scan(&name, &bkBizID, &event, &reason); err != nil {
		return strategyConflict{}, false, err
	}

	return strategyConflict{
		Index: lookup.Index, Name: name.String, BkBizID: int(bkBizID.Int64), Event: event.String,
		Reason: int(reason.Int64),
	}, true, nil
}

// defaultStrategyHits reports whether the table is empty, and what each seed matches.
func (s *mysqlStore) defaultStrategyHits() (bool, map[string]strategyHit, error) {
	db, err := s.orm()
	if err != nil {
		return false, nil, err
	}

	empty, err := strategyTableEmpty(db)
	if err != nil || empty {
		return empty, nil, err
	}

	hits := map[string]strategyHit{}
	for _, seed := range defaultStrategies() {
		hit, err := oneStrategyHit(db, seed)
		if err != nil {
			return false, nil, err
		}
		hits[seedIdentity(seed)] = hit
	}

	return false, hits, nil
}

// writeStrategyPlan inserts the planned strategies and the data ledger row in one transaction.
// Timestamps come from the server NOW(); the connection round-trips them in UTC, so the written
// literal equals the session time whatever the migrator host time zone is.
func (s *mysqlStore) writeStrategyPlan(plan strategyPlan) error {
	db, err := s.orm()
	if err != nil {
		return err
	}

	return db.Transaction(func(tx *gorm.DB) error {
		now, err := serverNow(tx)
		if err != nil {
			return err
		}

		for _, seed := range plan.Insert {
			row := seed
			row.CreatedAt, row.UpdatedAt = now, now
			if err = tx.Create(&row).Error; err != nil {
				return err
			}
		}

		ledger := dataLedgerRow{
			Version: dataVersion, Name: dataName, RequiredSchemaVersion: strategySchemaVersion(), AppliedAt: now,
		}

		return recordLedger(tx, ledger, "data ledger")
	})
}

// strategyTableEmpty reports whether the strategy table has no rows, reading no column values.
func strategyTableEmpty(db *gorm.DB) (bool, error) {
	rows, err := db.Model(&hamodel.DbSwitchingStrategy{}).Unscoped().Select("1").Limit(1).Rows()
	if err != nil {
		return false, err
	}
	defer rows.Close()

	if rows.Next() {
		return false, nil
	}

	return true, rows.Err()
}

// oneStrategyHit reads every row that shares the identity of one default strategy and ranks them.
// Matching stays in MySQL so the column collation decides identity. A NULL reason never matches.
func oneStrategyHit(db *gorm.DB, seed hamodel.DbSwitchingStrategy) (strategyHit, error) {
	rows, err := db.Model(&hamodel.DbSwitchingStrategy{}).Unscoped().
		Select([]string{
			hamodel.DbSwitchingStrategyFieldStatus,
			hamodel.DbSwitchingStrategyFieldDeletedAt,
		}).
		Where(map[string]any{
			hamodel.DbSwitchingStrategyFieldBkBizID:                seed.BkBizID,
			hamodel.DbSwitchingStrategyFieldTriggerEventName:       seed.TriggerEventName.String(),
			hamodel.DbSwitchingStrategyFieldTriggerEventNameReason: int(seed.TriggerEventNameReason),
		}).
		Rows()
	if err != nil {
		return strategyHit{}, err
	}
	defer rows.Close()

	var live []strategyRow
	for rows.Next() {
		var status sql.NullString
		var deleted sql.NullTime
		if err = rows.Scan(&status, &deleted); err != nil {
			return strategyHit{}, err
		}
		live = append(live, strategyRow{Status: status.String, Deleted: deleted.Valid})
	}
	if err = rows.Err(); err != nil {
		return strategyHit{}, err
	}

	return bestStrategyHit(live), nil
}
