package partitionsvr

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// timestampMonthPartitionType 按自然月分区，字段是 timestamp。
// MySQL 不允许 TIMESTAMP 进入 TO_DAYS，表达式用 RANGE (UNIX_TIMESTAMP(列))。
// 分区名、保留月份、追加间隔和类型 7 相同。上界字面量是下一段月初，
// 由会话 time_zone 解释成 unix 秒。配置里的 time_zone 必须是 +08:00 这种偏移。
const timestampMonthPartitionType = 8

func (pc *PartitionConfig) timestampMonthLocation() (*time.Location, error) {
	tz := strings.TrimSpace(pc.TimeZone)
	if len(tz) != 6 || (tz[0] != '+' && tz[0] != '-') || tz[3] != ':' {
		return nil, fmt.Errorf("time_zone %q must be like +08:00", pc.TimeZone)
	}
	hour, errH := strconv.Atoi(tz[1:3])
	minute, errM := strconv.Atoi(tz[4:6])
	if errH != nil || errM != nil || hour > 14 || minute > 59 {
		return nil, fmt.Errorf("time_zone %q must be like +08:00", pc.TimeZone)
	}
	sign := 1
	if tz[0] == '-' {
		sign = -1
	}
	return time.FixedZone(tz, sign*(hour*3600+minute*60)), nil
}

func (pc *PartitionConfig) checkTimestampMonthColumn() error {
	columnType := strings.ToLower(strings.TrimSpace(pc.PartitionColumnType))
	if !strings.HasPrefix(columnType, "timestamp") {
		return fmt.Errorf("partition type 8 requires timestamp column, got %q", pc.PartitionColumnType)
	}
	if pc.PartitionColumn == "" || strings.ContainsAny(pc.PartitionColumn, " `'\";") {
		return fmt.Errorf("invalid partition column %q", pc.PartitionColumn)
	}
	return nil
}

func (pc *PartitionConfig) timestampMonthNow() (time.Time, *time.Location, error) {
	if err := pc.checkTimestampMonthColumn(); err != nil {
		return time.Time{}, nil, err
	}
	loc, err := pc.timestampMonthLocation()
	if err != nil {
		return time.Time{}, nil, err
	}
	return time.Now().In(loc), loc, nil
}

func unixDescriptionToMonthDate(raw string, loc *time.Location) (time.Time, error) {
	raw = strings.TrimSpace(raw)
	if dot := strings.IndexByte(raw, '.'); dot >= 0 {
		raw = raw[:dot]
	}
	sec, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return time.Time{}, fmt.Errorf("invalid timestamp partition description %q", raw)
	}
	wall := time.Unix(sec, 0).In(loc)
	return time.Date(wall.Year(), wall.Month(), wall.Day(), 0, 0, 0, 0, loc), nil
}

func (pc *PartitionConfig) timestampMonthLessThan(boundary time.Time) string {
	return fmt.Sprintf("unix_timestamp('%s')", boundary.Format("2006-01-02"))
}

func (pc *PartitionConfig) timestampMonthInitStatement(pd *PartitionDetail, now time.Time) (string, error) {
	parts, err := pc.monthInitParts(now)
	if err != nil {
		return "", err
	}
	clauses := make([]string, 0, len(parts))
	for _, part := range parts {
		clauses = append(clauses, fmt.Sprintf(
			" partition %s values less than (%s)",
			part.Name, pc.timestampMonthLessThan(part.Boundary),
		))
	}
	pkey := fmt.Sprintf("RANGE (UNIX_TIMESTAMP(%s))", pc.PartitionColumn)
	body := strings.Join(clauses, ",")
	if pd.HasUniqueKey {
		options := fmt.Sprintf(
			"--charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=%d "+
				"--critical-load=Threads_running=%d --set-vars lock_wait_timeout=%d,time_zone=%s --print --pause-file=/tmp/partition_osc_pause_%s_%s --execute ",
			PT_MAX_LOAD_THREADS_RUNNING,
			PT_CRITICAL_LOAD_THREADS_RUNNING, PT_LOCK_WAIT_TIMEOUT, pc.TimeZone, pd.DbName, pd.TbName)
		return fmt.Sprintf(`D=%s,t=%s --alter "partition by %s (%s)" %s`, pd.DbName, pd.TbName, pkey, body, options), nil
	}
	return fmt.Sprintf("set session time_zone='%s'; alter table `%s`.`%s` partition by %s (%s)",
		pc.TimeZone, pd.DbName, pd.TbName, pkey, body), nil
}

func (pc *PartitionConfig) executeTimestampMonthInitStatement(pd *PartitionDetail, conn *native.DbWorker, forceInitInfo *ForceInitInfo) (partitionStepInfo *PartitionStepInfo) {
	partitionStepInfo = &PartitionStepInfo{
		Step:      "init",
		Status:    false,
		Message:   "",
		Statement: "",
	}
	now, _, err := pc.timestampMonthNow()
	if err != nil {
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	if forceInitInfo != nil {
		err = pd.CheckUniqueKey(conn)
		if err != nil {
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	} else {
		err = pd.CheckTableSize(conn)
		if err != nil {
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	}
	initStatement, err := pc.timestampMonthInitStatement(pd, now)
	if err != nil {
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	if forceInitInfo != nil && pd.HasUniqueKey {
		pc.ExecuteInitStatementByPTTool(initStatement, forceInitInfo, partitionStepInfo)
		return partitionStepInfo
	}
	pc.ExecuteInitStatementByDDL(initStatement, conn, partitionStepInfo)
	return partitionStepInfo
}

func (pc *PartitionConfig) listTimestampMonthPartitions(pd *PartitionDetail, conn *native.DbWorker, loc *time.Location) ([]monthPart, error) {
	querySQL := "" +
		"SELECT PARTITION_NAME AS PARTITION_NAME, PARTITION_DESCRIPTION AS PARTITION_DESCRIPTION " +
		"FROM INFORMATION_SCHEMA.PARTITIONS " +
		"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND PARTITION_NAME IS NOT NULL " +
		"ORDER BY PARTITION_DESCRIPTION+0 ASC"
	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)
	if err != nil {
		if strings.Contains(err.Error(), "not row found") {
			return nil, nil
		}
		return nil, err
	}
	parts := make([]monthPart, 0, len(rows))
	for _, row := range rows {
		boundary, parseErr := unixDescriptionToMonthDate(row["PARTITION_DESCRIPTION"].(string), loc)
		if parseErr != nil {
			return nil, parseErr
		}
		parts = append(parts, monthPart{Name: row["PARTITION_NAME"].(string), Boundary: boundary})
	}
	return parts, nil
}

func (pc *PartitionConfig) timestampMonthAddStatement(pd *PartitionDetail, conn *native.DbWorker, now time.Time, loc *time.Location) (string, error) {
	if pc.PartitionTimeInterval <= 0 {
		return "", fmt.Errorf("partition_time_interval must be > 0")
	}
	if pc.ExtraPartition < 0 {
		return "", fmt.Errorf("extra_partition must be >= 0")
	}
	existing, err := pc.listTimestampMonthPartitions(pd, conn, loc)
	if err != nil {
		return "", err
	}
	boundaries := make([]time.Time, 0, len(existing))
	for _, part := range existing {
		boundaries = append(boundaries, part.Boundary)
	}
	start, need, err := monthAddNeed(boundaries, now, pc.PartitionTimeInterval, pc.ExtraPartition)
	if err != nil {
		return "", err
	}
	if need == 0 {
		return "", nil
	}
	parts, err := monthPartsFrom(start, need, pc.PartitionTimeInterval)
	if err != nil {
		return "", err
	}
	clauses := make([]string, 0, len(parts))
	for _, part := range parts {
		clauses = append(clauses, fmt.Sprintf(
			"partition `%s` values less than (%s)",
			part.Name, pc.timestampMonthLessThan(part.Boundary),
		))
	}
	return fmt.Sprintf("alter table `%s`.`%s` add partition( %s )", pd.DbName, pd.TbName, strings.Join(clauses, ",")), nil
}

func (pc *PartitionConfig) executeTimestampMonthAddStatement(pd *PartitionDetail, conn *native.DbWorker) (partitionStepInfo *PartitionStepInfo) {
	partitionStepInfo = &PartitionStepInfo{
		Step:      "add",
		Status:    true,
		Message:   "",
		Statement: "",
	}
	now, loc, err := pc.timestampMonthNow()
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	if pc.IntervalCheck {
		err = pc.checkTimestampMonthInterval(pd, conn, now, loc)
		if err != nil {
			partitionStepInfo.Status = false
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	}
	addStatement, err := pc.timestampMonthAddStatement(pd, conn, now, loc)
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	if addStatement == "" {
		partitionStepInfo.Message = "No need to execute add partition statement"
		return partitionStepInfo
	}
	partitionStepInfo.Statement = addStatement
	err = execPartitionStmtWithRetry(fmt.Sprintf("add partition `%s`.`%s`", pd.DbName, pd.TbName), func(lockWaitTimeout int) error {
		addSQL := fmt.Sprintf("set session time_zone='%s'; set session lock_wait_timeout=%d; %s", pc.TimeZone, lockWaitTimeout, addStatement)
		_, execErr := conn.ExecWithTimeout(ExecTimeout, addSQL)
		return execErr
	})
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	partitionStepInfo.Message = "success"
	return partitionStepInfo
}

func (pc *PartitionConfig) timestampMonthDropStatement(pd *PartitionDetail, conn *native.DbWorker, now time.Time, loc *time.Location) (string, error) {
	parts, err := pc.listTimestampMonthPartitions(pd, conn, loc)
	if err != nil {
		return "", fmt.Errorf("error occurred while checking partition info: %s", err.Error())
	}
	if len(parts) == 0 {
		return "", nil
	}
	boundaries := make([]time.Time, 0, len(parts))
	for _, part := range parts {
		boundaries = append(boundaries, part.Boundary)
	}
	if monthCurrentIndex(boundaries, now) < 0 {
		return "", nil
	}
	threshold, err := monthDropThreshold(now, pc.ExpireTime)
	if err != nil {
		return "", err
	}
	expired := make([]string, 0)
	for _, part := range parts {
		if part.Boundary.After(threshold) {
			continue
		}
		if !monthPartitionNameReg.MatchString(part.Name) {
			return "", fmt.Errorf("partition_name [%s] not like 'p201301', "+
				"not created by partition system, can't be dropped", part.Name)
		}
		expired = append(expired, part.Name)
	}
	if len(expired) == 0 {
		return "", nil
	}
	return fmt.Sprintf("alter table `%s`.`%s` drop partition %s", pd.DbName, pd.TbName, strings.Join(expired, ",")), nil
}

func (pc *PartitionConfig) executeTimestampMonthDropStatement(pd *PartitionDetail, conn *native.DbWorker) (partitionStepInfo *PartitionStepInfo) {
	partitionStepInfo = &PartitionStepInfo{
		Step:      "drop",
		Status:    true,
		Message:   "",
		Statement: "",
	}
	if pc.Phase != "online" {
		partitionStepInfo.Message = "Phase is off, no need to execute drop partition statement"
		return partitionStepInfo
	}
	now, loc, err := pc.timestampMonthNow()
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	dropStatement, err := pc.timestampMonthDropStatement(pd, conn, now, loc)
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	if dropStatement == "" {
		partitionStepInfo.Message = "No need to execute drop partition statement"
		return partitionStepInfo
	}
	partitionStepInfo.Statement = dropStatement
	err = execPartitionStmtWithRetry(fmt.Sprintf("drop partition `%s`.`%s`", pd.DbName, pd.TbName), func(lockWaitTimeout int) error {
		dropSQL := fmt.Sprintf("set session time_zone='%s'; set session lock_wait_timeout=%d; %s", pc.TimeZone, lockWaitTimeout, dropStatement)
		_, execErr := conn.ExecWithTimeout(ExecTimeout, dropSQL)
		return execErr
	})
	if err != nil {
		partitionStepInfo.Status = false
		partitionStepInfo.Message = err.Error()
		return partitionStepInfo
	}
	partitionStepInfo.Message = "success"
	return partitionStepInfo
}

func (pc *PartitionConfig) checkTimestampMonthInterval(pd *PartitionDetail, conn *native.DbWorker, now time.Time, loc *time.Location) error {
	if pc.PartitionTimeInterval <= 0 {
		return fmt.Errorf("partition_time_interval must be > 0")
	}
	parts, err := pc.listTimestampMonthPartitions(pd, conn, loc)
	if err != nil {
		return fmt.Errorf("get month partitions: %w", err)
	}
	if len(parts) == 0 {
		return nil
	}
	active := monthActiveBoundary(now)
	currentIdx := -1
	boundaries := make([]time.Time, 0, len(parts))
	names := make([]string, 0, len(parts))
	for _, part := range parts {
		names = append(names, part.Name)
		boundaries = append(boundaries, part.Boundary)
		if currentIdx < 0 && !part.Boundary.Before(active) {
			currentIdx = len(boundaries) - 1
		}
	}
	if currentIdx < 0 || len(boundaries)-currentIdx-1 < 2 {
		return nil
	}
	futureBoundaries := boundaries[currentIdx+1:]
	if monthBoundariesMatch(futureBoundaries, pc.PartitionTimeInterval) {
		return nil
	}
	futureNames := names[currentIdx+1:]
	hasData, err := pc.HasDataInPartitions(pd, conn, futureNames)
	if err != nil {
		return fmt.Errorf("check if future partitions have data: %w", err)
	}
	if hasData {
		return fmt.Errorf("Future partitions have data, cannot directly clean up and apply new interval rules. Please clean up and try again.")
	}
	if err = pc.CleanupFuturePartitions(pd, conn, futureNames); err != nil {
		return fmt.Errorf("cleanup future partitions: %w", err)
	}
	return nil
}
