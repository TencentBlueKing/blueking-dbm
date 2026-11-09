package partitionsvr

import (
	"strconv"
	"strings"
	"testing"
	"time"
)

func TestTimestampMonthInitSQL(t *testing.T) {
	pc := &PartitionConfig{
		PartitionType:         timestampMonthPartitionType,
		PartitionColumn:       "ts",
		PartitionColumnType:   "timestamp",
		PartitionTimeInterval: 1,
		ReservedPartition:     2,
		ExtraPartition:        1,
		ExpireTime:            2,
		TimeZone:              "+08:00",
	}
	loc, err := pc.timestampMonthLocation()
	if err != nil {
		t.Fatal(err)
	}
	now := time.Date(2026, 11, 7, 15, 0, 0, 0, loc)
	stmt, err := pc.timestampMonthInitStatement(&PartitionDetail{DbName: "db", TbName: "tb"}, now)
	if err != nil {
		t.Fatal(err)
	}
	want := "set session time_zone='+08:00'; alter table `db`.`tb` partition by RANGE (UNIX_TIMESTAMP(ts)) (" +
		" partition p202609 values less than (unix_timestamp('2026-10-01'))," +
		" partition p202610 values less than (unix_timestamp('2026-11-01'))," +
		" partition p202611 values less than (unix_timestamp('2026-12-01'))," +
		" partition p202612 values less than (unix_timestamp('2027-01-01')))"
	if stmt != want {
		t.Fatalf("sql=%s", stmt)
	}
}

func TestUnixDescriptionUsesConfiguredZone(t *testing.T) {
	pc := &PartitionConfig{TimeZone: "+08:00"}
	loc, err := pc.timestampMonthLocation()
	if err != nil {
		t.Fatal(err)
	}
	boundary := time.Date(2026, 12, 1, 0, 0, 0, 0, loc)
	got, err := unixDescriptionToMonthDate(strconv.FormatInt(boundary.Unix(), 10), loc)
	if err != nil {
		t.Fatal(err)
	}
	if !got.Equal(boundary) {
		t.Fatalf("boundary=%s", got.Format(time.RFC3339))
	}
}

func TestTimestampMonthRejectsDatetime(t *testing.T) {
	pc := &PartitionConfig{
		PartitionColumn:     "dt",
		PartitionColumnType: "datetime",
		TimeZone:            "+08:00",
	}
	_, _, err := pc.timestampMonthNow()
	if err == nil || !strings.Contains(err.Error(), "timestamp") {
		t.Fatalf("err=%v", err)
	}
}
