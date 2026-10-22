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

func applyOne(store Store, opts Options) error {
	if runsSchemaWork(opts) {
		if err := applySchema(store, opts); err != nil {
			return err
		}
	}
	if opts.RunsData() {
		if err := store.ApplyStrategies(opts.RepairMissingData); err != nil {
			return fmt.Errorf("data step failed, endpoint: %s, errmsg: %s", store.Endpoint(), err)
		}
	}
	return nil
}

func applySchema(store Store, opts Options) error {
	snap, err := probed(store)
	if err != nil {
		return endpointError("load schema snapshot", store, err)
	}
	warnLegacyKeys(store.Endpoint(), snap)
	rebuilding := map[string]bool{}
	partial := partialBusiness(snap)
	if opts.RepairMissingTables {
		for _, table := range managedTables() {
			if snap.Tables[table.Name] == nil {
				rebuilding[table.Name] = true
			}
		}
	}
	if err = store.EnsureDatabase(); err != nil {
		return endpointError("ensure database", store, err)
	}
	if err = store.EnsureSchemaLedger(); err != nil {
		return endpointError("ensure schema ledger", store, err)
	}
	for _, step := range schemaSteps() {
		if err = applyStep(store, opts, step, partial, rebuilding[step.Table]); err != nil {
			return err
		}
	}
	return nil
}

func applyStep(store Store, opts Options, step schemaStep, partial, rebuildTable bool) error {
	snap, err := probed(store)
	if err != nil {
		return stepError("load schema snapshot", store, step, err)
	}
	view := inspectStep(snap, step)
	choice := schemaChoice(
		view.Recorded, view.Present, view.Conflict, step.Kind, partial, rebuildTable, opts,
	)
	logger.Info(
		"migrate step, endpoint: %s, version: %d, phase: check, result: %s",
		store.Endpoint(), step.Version, choiceName(choice),
	)
	switch choice {
	case decisionRecord:
		if err := store.RecordSchema(step.Version, step.Name); err != nil {
			return stepError("record schema ledger", store, step, err)
		}
		return nil
	case decisionApply:
		if err = applyChosen(store, step); err != nil {
			return err
		}
		if err = verifyStep(store, step); err != nil {
			return err
		}
		logger.Info(
			"migrate step, endpoint: %s, version: %d, phase: apply, result: ok",
			store.Endpoint(), step.Version,
		)
		if err = store.RecordSchema(step.Version, step.Name); err != nil {
			return stepError("record schema ledger", store, step, err)
		}
		return nil
	default:
		return fmt.Errorf(
			"schema step blocked, endpoint: %s, version: %d, result: %s",
			store.Endpoint(), step.Version, choiceName(choice),
		)
	}
}

func verifyStep(store Store, step schemaStep) error {
	snap, err := probed(store)
	if err != nil {
		return stepError("load schema snapshot", store, step, err)
	}
	view := inspectStep(snap, step)
	if view.Present && !view.Conflict {
		return nil
	}
	result := "missing"
	if view.Conflict {
		result = "conflict"
	}
	return fmt.Errorf(
		"verify schema DDL failed, endpoint: %s, version: %d, result: %s",
		store.Endpoint(), step.Version, result,
	)
}

func probed(store Store) (*Snapshot, error) {
	snap, err := store.Load()
	if err != nil || snap == nil || !snap.Database {
		return snap, err
	}
	if err = store.ProbeFacts(snap); err != nil {
		return nil, err
	}
	return snap, nil
}

func applyChosen(store Store, step schemaStep) error {
	if !convergeKind(step.Kind) {
		if err := store.ExecDDL(step.Apply); err != nil {
			return stepError("apply schema DDL", store, step, err)
		}
		return nil
	}
	if err := applyConvergeStep(store, step); err != nil {
		return stepError("apply schema DDL", store, step, err)
	}
	return nil
}

func applyConvergeStep(store Store, step schemaStep) error {
	snap, err := probed(store)
	if err != nil {
		return err
	}
	table := snap.Tables[step.Table]
	spec, _ := tableByName(step.Table)
	if table == nil {
		return nil
	}
	plan, err := convergePlanFor(table, spec, step)
	if err != nil || len(plan.Statements) == 0 {
		return err
	}
	return store.ApplyConverge(plan)
}

func convergePlanFor(table *Table, spec tableSpec, step schemaStep) (convergePlan, error) {
	switch step.Kind {
	case objectColumnDef:
		if _, ok := table.Columns[step.Column]; !ok {
			return convergePlan{}, fmt.Errorf("column missing, table: %s, column: %s", step.Table, step.Column)
		}
		want := columnByName(spec, step.Column)
		if columnRelation(want, table.Columns[step.Column]) == relSatisfy {
			return convergePlan{}, nil
		}
		return buildColumnPlan(table, spec, want), nil
	case objectPrimaryKey:
		for _, name := range spec.Baseline {
			if _, ok := table.Columns[name]; !ok {
				return convergePlan{}, fmt.Errorf("primary key column missing, table: %s, column: %s", step.Table, name)
			}
		}
		if sameCols(table.PK, spec.Baseline) && targetNeedsNothing(table, spec) {
			return convergePlan{}, nil
		}
		return buildPKPlan(table, spec), nil
	default:
		return convergePlan{}, nil
	}
}

func targetNeedsNothing(table *Table, spec tableSpec) bool {
	present, conflict := targetPKView(table, spec)
	return present && !conflict
}

func endpointError(stage string, store Store, err error) error {
	return fmt.Errorf("%s failed, endpoint: %s, errmsg: %w", stage, store.Endpoint(), err)
}

func stepError(stage string, store Store, step schemaStep, err error) error {
	return fmt.Errorf(
		"%s failed, endpoint: %s, version: %d, errmsg: %w",
		stage, store.Endpoint(), step.Version, err,
	)
}
