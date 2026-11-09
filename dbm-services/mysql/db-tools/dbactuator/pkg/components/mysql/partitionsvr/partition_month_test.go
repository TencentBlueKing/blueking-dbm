/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package partitionsvr

import (
	"testing"
	"time"
)

func TestMonthInitKeepsFiveMonths(t *testing.T) {
	pc := &PartitionConfig{
		PartitionTimeInterval: 1,
		ReservedPartition:     5,
		ExtraPartition:        2,
		PartitionColumn:       "dt",
	}
	now := time.Date(2026, 11, 7, 15, 0, 0, 0, time.Local)
	parts, err := pc.monthInitParts(now)
	if err != nil {
		t.Fatal(err)
	}
	got := make([]string, 0, len(parts))
	for _, part := range parts {
		got = append(got, part.Name+"->"+part.Boundary.Format("2006-01-02"))
	}
	want := []string{
		"p202606->2026-07-01",
		"p202607->2026-08-01",
		"p202608->2026-09-01",
		"p202609->2026-10-01",
		"p202610->2026-11-01",
		"p202611->2026-12-01",
		"p202612->2027-01-01",
		"p202701->2027-02-01",
	}
	if len(got) != len(want) {
		t.Fatalf("parts=%v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("parts=%v", got)
		}
	}

	stmt, err := pc.monthInitStatement(&PartitionDetail{DbName: "db", TbName: "tb"}, now)
	if err != nil {
		t.Fatal(err)
	}
	wantSQL := "alter table `db`.`tb` partition by RANGE (TO_DAYS(dt)) (" +
		" partition p202606 values less than (to_days('2026-07-01'))," +
		" partition p202607 values less than (to_days('2026-08-01'))," +
		" partition p202608 values less than (to_days('2026-09-01'))," +
		" partition p202609 values less than (to_days('2026-10-01'))," +
		" partition p202610 values less than (to_days('2026-11-01'))," +
		" partition p202611 values less than (to_days('2026-12-01'))," +
		" partition p202612 values less than (to_days('2027-01-01'))," +
		" partition p202701 values less than (to_days('2027-02-01')))"
	if stmt != wantSQL {
		t.Fatalf("sql=%s", stmt)
	}
}

func TestMonthDropThreshold(t *testing.T) {
	now := time.Date(2026, 11, 7, 0, 0, 0, 0, time.Local)
	threshold, err := monthDropThreshold(now, 5)
	if err != nil {
		t.Fatal(err)
	}
	if threshold.Format("2006-01-02") != "2026-06-01" {
		t.Fatalf("threshold=%s", threshold.Format("2006-01-02"))
	}
}

func TestMonthDropKeepsIntervalSegmentUntilItEnds(t *testing.T) {
	sep := time.Date(2026, 9, 1, 0, 0, 0, 0, time.Local)
	nov := time.Date(2026, 11, 1, 0, 0, 0, 0, time.Local)
	jan := time.Date(2027, 1, 1, 0, 0, 0, 0, time.Local)
	bounds := []time.Time{sep, nov, jan}
	dec := time.Date(2026, 12, 15, 0, 0, 0, 0, time.Local)
	idx := monthCurrentIndex(bounds, dec)
	if idx != 2 {
		t.Fatalf("current index=%d", idx)
	}
	threshold, err := monthDropThreshold(dec, 6)
	if err != nil {
		t.Fatal(err)
	}
	if threshold.Format("2006-01-02") != "2026-06-01" {
		t.Fatalf("threshold=%s", threshold.Format("2006-01-02"))
	}
	if !bounds[0].After(threshold) {
		t.Fatal("July-August segment must stay through December")
	}
}

func TestMonthDropKeepsPreviousSegmentForExpireInsideIt(t *testing.T) {
	sep := time.Date(2026, 9, 1, 0, 0, 0, 0, time.Local)
	nov := time.Date(2026, 11, 1, 0, 0, 0, 0, time.Local)
	jan := time.Date(2027, 1, 1, 0, 0, 0, 0, time.Local)
	bounds := []time.Time{sep, nov, jan}
	now := time.Date(2026, 11, 7, 0, 0, 0, 0, time.Local)
	threshold, err := monthDropThreshold(now, 2)
	if err != nil {
		t.Fatal(err)
	}
	if threshold.Format("2006-01-02") != "2026-09-01" {
		t.Fatalf("threshold=%s", threshold.Format("2006-01-02"))
	}
	if !bounds[1].After(threshold) {
		t.Fatal("September and October are the two months before November and must stay")
	}
	if bounds[0].After(threshold) {
		t.Fatal("July-August segment ends at September 1 and can be dropped")
	}
}

func TestMonthAddNeedContinuesExistingInterval(t *testing.T) {
	sep := time.Date(2026, 9, 1, 0, 0, 0, 0, time.Local)
	nov := time.Date(2026, 11, 1, 0, 0, 0, 0, time.Local)
	dec := time.Date(2026, 12, 15, 0, 0, 0, 0, time.Local)
	start, count, err := monthAddNeed([]time.Time{sep, nov}, dec, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	if start.Format("2006-01-02") != "2026-11-01" || count != 3 {
		t.Fatalf("start=%s count=%d", start.Format("2006-01-02"), count)
	}
	parts, err := monthPartsFrom(start, count, 2)
	if err != nil {
		t.Fatal(err)
	}
	if parts[0].Name != "p202611" || parts[0].Boundary.Format("2006-01-02") != "2027-01-01" {
		t.Fatalf("current=%+v", parts[0])
	}
	if parts[2].Name != "p202703" || parts[2].Boundary.Format("2006-01-02") != "2027-05-01" {
		t.Fatalf("last=%+v", parts[2])
	}
}

func TestMonthPartsFromExistingBoundary(t *testing.T) {
	start := time.Date(2026, 12, 1, 0, 0, 0, 0, time.Local)
	parts, err := monthPartsFrom(start, 2, 1)
	if err != nil {
		t.Fatal(err)
	}
	if parts[0].Name != "p202612" || parts[0].Boundary.Format("2006-01-02") != "2027-01-01" {
		t.Fatalf("first=%+v", parts[0])
	}
	if parts[1].Name != "p202701" || parts[1].Boundary.Format("2006-01-02") != "2027-02-01" {
		t.Fatalf("second=%+v", parts[1])
	}
}

func TestMonthBoundariesMatch(t *testing.T) {
	dec := time.Date(2026, 12, 1, 0, 0, 0, 0, time.Local)
	jan := time.Date(2027, 1, 1, 0, 0, 0, 0, time.Local)
	feb := time.Date(2027, 2, 1, 0, 0, 0, 0, time.Local)
	if !monthBoundariesMatch([]time.Time{dec, jan, feb}, 1) {
		t.Fatal("interval 1 should match")
	}
	if monthBoundariesMatch([]time.Time{dec, feb}, 1) {
		t.Fatal("two-month gap should not match interval 1")
	}
	if !monthBoundariesMatch([]time.Time{dec, feb}, 2) {
		t.Fatal("interval 2 should match")
	}
}
