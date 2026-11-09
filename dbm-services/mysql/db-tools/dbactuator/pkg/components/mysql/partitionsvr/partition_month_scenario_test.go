package partitionsvr

import (
	"fmt"
	"strings"
	"testing"
	"time"
)

// 按真实函数走初始化、追加、删除。expire 取间隔的 3 倍，保留段数固定为 3，额外 2 段。
func TestMonthLifecycleIntervals(t *testing.T) {
	cases := []struct {
		interval int
		expire   int
	}{
		{1, 3},
		{2, 6},
		{3, 9},
	}
	for _, tc := range cases {
		t.Run(fmt.Sprintf("interval_%d", tc.interval), func(t *testing.T) {
			runMonthLifecycle(t, tc.interval, tc.expire, 2)
		})
	}
}

func runMonthLifecycle(t *testing.T, interval, expire, extra int) {
	t.Helper()
	reserved := (expire + interval - 1) / interval
	pc := &PartitionConfig{
		PartitionTimeInterval: interval,
		ExpireTime:            expire,
		ReservedPartition:     reserved,
		ExtraPartition:        extra,
		PartitionColumn:       "dt",
	}
	start := time.Date(2026, 11, 7, 12, 0, 0, 0, time.Local)
	parts, err := pc.monthInitParts(start)
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("初始化 %s interval=%d expire=%d reserved=%d extra=%d", start.Format("2006-01-02"), interval, expire, reserved, extra)
	t.Log(formatMonthParts(parts))
	if err := checkMonthSteps(parts, interval); err != nil {
		t.Fatal(err)
	}
	if err := checkMonthCovers(parts, start); err != nil {
		t.Fatal(err)
	}

	for month := 0; month < 8; month++ {
		now := time.Date(2026, 11, 15, 12, 0, 0, 0, time.Local).AddDate(0, month, 0)
		before := append([]monthPart(nil), parts...)
		parts, err = applyMonthAdd(parts, now, interval, extra)
		if err != nil {
			t.Fatalf("%s add: %v", now.Format("2006-01-02"), err)
		}
		parts, err = applyMonthDrop(parts, now, expire)
		if err != nil {
			t.Fatalf("%s drop: %v", now.Format("2006-01-02"), err)
		}
		t.Logf("%s 追加后删除", now.Format("2006-01-02"))
		t.Log(formatMonthParts(parts))
		if err := checkMonthSteps(parts, interval); err != nil {
			t.Fatalf("%s step: %v\nbefore %s", now.Format("2006-01-02"), err, formatMonthParts(before))
		}
		if err := checkMonthCovers(parts, now); err != nil {
			t.Fatal(err)
		}
		if err := checkMonthRetention(parts, now, expire); err != nil {
			t.Fatal(err)
		}
		future, err := countFuture(parts, now)
		if err != nil {
			t.Fatal(err)
		}
		if future != extra {
			t.Fatalf("%s future=%d want %d", now.Format("2006-01-02"), future, extra)
		}
	}
}

func applyMonthAdd(parts []monthPart, now time.Time, interval, extra int) ([]monthPart, error) {
	bounds := make([]time.Time, len(parts))
	for i, part := range parts {
		bounds[i] = part.Boundary
	}
	start, count, err := monthAddNeed(bounds, now, interval, extra)
	if err != nil || count == 0 {
		return parts, err
	}
	added, err := monthPartsFrom(start, count, interval)
	if err != nil {
		return parts, err
	}
	return append(parts, added...), nil
}

func applyMonthDrop(parts []monthPart, now time.Time, expire int) ([]monthPart, error) {
	bounds := make([]time.Time, len(parts))
	for i, part := range parts {
		bounds[i] = part.Boundary
	}
	idx := monthCurrentIndex(bounds, now)
	if idx < 0 {
		return parts, nil
	}
	threshold, err := monthDropThreshold(now, expire)
	if err != nil {
		return parts, err
	}
	kept := make([]monthPart, 0, len(parts))
	for _, part := range parts {
		if !part.Boundary.After(threshold) {
			continue
		}
		kept = append(kept, part)
	}
	return kept, nil
}

func checkMonthSteps(parts []monthPart, interval int) error {
	for i := 1; i < len(parts); i++ {
		got := monthsBetween(parts[i-1].Boundary, parts[i].Boundary)
		if got != interval {
			return fmt.Errorf("%s -> %s is %d months, interval=%d", parts[i-1].Name, parts[i].Name, got, interval)
		}
	}
	return nil
}

func checkMonthCovers(parts []monthPart, now time.Time) error {
	bounds := make([]time.Time, len(parts))
	for i, part := range parts {
		bounds[i] = part.Boundary
	}
	if monthCurrentIndex(bounds, now) < 0 {
		return fmt.Errorf("%s is not covered", now.Format("2006-01-02"))
	}
	return nil
}

func checkMonthRetention(parts []monthPart, now time.Time, expire int) error {
	threshold, err := monthDropThreshold(now, expire)
	if err != nil {
		return err
	}
	for _, part := range parts {
		if !part.Boundary.After(threshold) {
			return fmt.Errorf("%s still present but boundary %s is not after %s", part.Name, part.Boundary.Format("2006-01-02"), threshold.Format("2006-01-02"))
		}
	}
	if len(parts) == 0 || !parts[0].Boundary.After(threshold) {
		return fmt.Errorf("oldest kept partition does not cover %s", threshold.Format("2006-01-02"))
	}
	return nil
}

func countFuture(parts []monthPart, now time.Time) (int, error) {
	bounds := make([]time.Time, len(parts))
	for i, part := range parts {
		bounds[i] = part.Boundary
	}
	idx := monthCurrentIndex(bounds, now)
	if idx < 0 {
		return 0, fmt.Errorf("no current partition")
	}
	return len(parts) - idx - 1, nil
}

func monthsBetween(a, b time.Time) int {
	return (b.Year()-a.Year())*12 + int(b.Month()-a.Month())
}

func formatMonthParts(parts []monthPart) string {
	items := make([]string, 0, len(parts))
	for _, part := range parts {
		items = append(items, fmt.Sprintf("%s<%s", part.Name, part.Boundary.Format("2006-01-02")))
	}
	return strings.Join(items, " ")
}
