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
	"strconv"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	dataVersion = 1
	dataName    = "000001_default_global_strategies"
)

type strategySeed struct {
	Name     string
	BkBizID  int
	Status   string
	Event    string
	Reason   int
	Count    int
	Priority int
	Scope    string
	Action   string
}

func defaultStrategies() []strategySeed {
	rows := []hamodel.DbSwitchingStrategy{
		strategy(haprobe.DbEventNameDoubleCheckSshFailureV1, haprobe.DbEventNameReasonConnectionException),
		strategy(haprobe.DbEventNameSshAuthFailure, haprobe.DbEventNameReasonSSHAuthException),
		strategy(haprobe.DbEventNameSshTimeout, haprobe.DbEventNameReasonSshTimeout),
		strategy(haprobe.DbEventNameDiskWriteFailure, haprobe.DbEventNameReasonDiskWriteException),
		strategy(haprobe.DbEventNameUptimeFailure, haprobe.DbEventNameReasonUptimeException),
	}
	out := make([]strategySeed, 0, len(rows))
	for _, row := range rows {
		out = append(out, strategySeed{
			Name:     row.Name,
			BkBizID:  row.BkBizID,
			Status:   row.Status.String(),
			Event:    row.TriggerEventName.String(),
			Reason:   int(row.TriggerEventNameReason),
			Count:    row.TriggerCount,
			Priority: row.Priority,
			Scope:    row.Scope.String(),
			Action:   row.Action.String(),
		})
	}
	return out
}

func strategy(event haprobe.DbEventName, reason haprobe.DbEventNameReason) hamodel.DbSwitchingStrategy {
	return hamodel.DbSwitchingStrategy{
		Name:                   event.String(),
		BkBizID:                0,
		Status:                 hamodel.StatusTypeEnabled,
		TriggerEventName:       event,
		TriggerEventNameReason: reason,
		TriggerCount:           1,
		Priority:               9999,
		Scope:                  hamodel.ActionScopeTypeHost,
		Action:                 hamodel.ActionTypeSwitch,
	}
}

func strategySchemaVersion() int64 {
	for _, step := range schemaSteps() {
		if step.Table == hamodel.DbSwitchingStrategyTableName && step.Kind == objectTable {
			return step.Version
		}
	}
	return 0
}

type strategyHit struct {
	Found   bool
	Status  string
	Deleted bool
}

type strategyAction struct {
	Seed   strategySeed
	Action string
}

type strategyPlan struct {
	Insert   []strategySeed
	Actions  []strategyAction
	Complete bool
}

func strategyReady(snap *Snapshot) bool {
	table := snap.Tables[hamodel.DbSwitchingStrategyTableName]
	if table == nil {
		return false
	}
	spec, ok := tableByName(hamodel.DbSwitchingStrategyTableName)
	if !ok || !strategyColumnsReady(table, spec) {
		return false
	}
	for _, index := range spec.Indexes {
		if !index.Unique {
			continue
		}
		present, conflict := matchIndex(table.Indexes, index)
		if !present || conflict {
			return false
		}
	}
	return true
}

func strategyColumnsReady(table *Table, spec tableSpec) bool {
	families := map[string]string{}
	for _, column := range spec.Columns {
		families[column.Name] = column.Family
	}
	for _, name := range strategyReadColumns() {
		live, ok := table.Columns[name]
		family, known := families[name]
		if !ok || !known || !familyOK(family, live.DataType) {
			return false
		}
	}
	return true
}

func strategyReadColumns() []string {
	return []string{
		"status", "name", "bk_biz_id", "trigger_event_name", "trigger_event_name_reason",
		"trigger_count", "priority", "scope", "action", "description",
		"created_at", "updated_at", "deleted_at",
	}
}

func planDefaultStrategies(empty bool, hits map[string]strategyHit, repair bool) strategyPlan {
	plan := strategyPlan{Complete: true}
	for _, seed := range defaultStrategies() {
		if empty {
			plan.Insert = append(plan.Insert, seed)
			continue
		}
		hit := hits[strategyIdentity(seed)]
		if !hit.Found {
			if repair {
				plan.Insert = append(plan.Insert, seed)
				continue
			}
			plan.Complete = false
			plan.Actions = append(plan.Actions, strategyAction{Seed: seed, Action: "skip"})
			continue
		}
		if strategyDeleted(hit) {
			plan.Actions = append(plan.Actions, strategyAction{Seed: seed, Action: "keep-deleted"})
		}
	}
	return plan
}

func strategyDeleted(hit strategyHit) bool {
	return hit.Status == hamodel.StatusTypeDeleted.String() || hit.Deleted
}

func strategyIdentity(seed strategySeed) string {
	return strconv.Itoa(seed.BkBizID) + "\x00" + seed.Event
}

func logStrategyActions(endpoint string, actions []strategyAction) {
	for _, action := range actions {
		logger.Info(
			"default strategy, endpoint: %s, bk_biz_id: %d, trigger_event_name: %s, action: %s",
			endpoint, action.Seed.BkBizID, action.Seed.Event, action.Action,
		)
	}
}
