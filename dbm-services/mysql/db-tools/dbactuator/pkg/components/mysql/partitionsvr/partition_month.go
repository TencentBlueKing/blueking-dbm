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
	"fmt"
	"regexp"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// monthPartitionType 按自然月分区，字段是 date 或 datetime。
// RANGE (TO_DAYS(列))，分区名 pYYYYMM，边界是该分区结束后的下一段月初。
// timestamp 不能放进 TO_DAYS，用类型 8。
// expire_time、partition_time_interval 的单位是月。
// expire_time 不含当月。例如 expire_time=2、interval=1，2026-11-07 保留 9 月和 10 月，当月分区另外留下。
// extra_partition 只算当前月之后的未来分区。2 表示再留 12 月和 1 月。
const monthPartitionType = 7

var monthPartitionNameReg = regexp.MustCompile(`^p[0-9]{6}$`)

type monthPart struct {
	Name     string
	Boundary time.Time
}

func monthStart(t time.Time) time.Time {
	return time.Date(t.Year(), t.Month(), 1, 0, 0, 0, 0, t.Location())
}

// monthActiveBoundary 当前分区的上界至少到明天，用来把它和更早的历史分区分开。
func monthActiveBoundary(now time.Time) time.Time {
	day := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location())
	return day.AddDate(0, 0, 1)
}

func (pc *PartitionConfig) checkMonthArgs() error {
	if pc.PartitionTimeInterval <= 0 {
		return fmt.Errorf("partition_time_interval must be > 0")
	}
	if pc.ReservedPartition <= 0 {
		return fmt.Errorf("expire_time must be > 0")
	}
	if pc.ExtraPartition < 0 {
		return fmt.Errorf("extra_partition must be >= 0")
	}
	return nil
}

// monthInitParts 按 ReservedPartition 段覆盖当月之前的月份，当月这段另外创建。
// ExtraPartition 只计当前月之后的未来分区，不把当前月算进去。
func (pc *PartitionConfig) monthInitParts(now time.Time) ([]monthPart, error) {
	if err := pc.checkMonthArgs(); err != nil {
		return nil, err
	}
	current := monthStart(now)
	start := -pc.ReservedPartition
	parts := make([]monthPart, 0, pc.ReservedPartition+pc.ExtraPartition)
	for i := start; i <= pc.ExtraPartition; i++ {
		partMonth := current.AddDate(0, i*pc.PartitionTimeInterval, 0)
		parts = append(parts, monthPart{
			Name:     partMonth.Format("p200601"),
			Boundary: partMonth.AddDate(0, pc.PartitionTimeInterval, 0),
		})
	}
	if len(parts) == 0 {
		return nil, fmt.Errorf("no month partition to initialize")
	}
	return parts, nil
}

// monthDropThreshold 保留当月之前的 expire 个月，返回最早保留月的月初。当月分区另外留下。
// 上界早于或等于这一天的分区不含这些月，可以删除。
// 间隔大于 1 时，最早保留月可能落在上一段的后半。那段必须整段留下，段里更早的月份一起多留。
func monthDropThreshold(now time.Time, expire int) (time.Time, error) {
	if expire <= 0 {
		return time.Time{}, fmt.Errorf("expire_time must be > 0")
	}
	return monthStart(now).AddDate(0, -expire, 0), nil
}

// monthCurrentIndex 返回上界能盖住今天的那段分区。没有则返回 -1。
func monthCurrentIndex(boundaries []time.Time, now time.Time) int {
	active := monthActiveBoundary(now)
	for i, boundary := range boundaries {
		if !boundary.Before(active) {
			return i
		}
	}
	return -1
}

// monthAddNeed 计算从哪个上界开始、按间隔补多少段。
// 已有上界还没盖住今天时，从最后一段继续按间隔往后接，不改接到本月 1 号。
func monthAddNeed(boundaries []time.Time, now time.Time, interval, extra int) (time.Time, int, error) {
	if interval <= 0 {
		return time.Time{}, 0, fmt.Errorf("partition_time_interval must be > 0")
	}
	if extra < 0 {
		return time.Time{}, 0, fmt.Errorf("extra_partition must be >= 0")
	}
	if len(boundaries) == 0 {
		return monthStart(now), extra + 1, nil
	}
	currentIdx := monthCurrentIndex(boundaries, now)
	if currentIdx >= 0 {
		futureCount := len(boundaries) - currentIdx - 1
		if futureCount >= extra {
			return time.Time{}, 0, nil
		}
		return boundaries[len(boundaries)-1], extra - futureCount, nil
	}
	start := boundaries[len(boundaries)-1]
	active := monthActiveBoundary(now)
	count := 0
	cursor := start
	for {
		count++
		cursor = cursor.AddDate(0, interval, 0)
		if !cursor.Before(active) {
			return start, count + extra, nil
		}
	}
}

func monthPartsFrom(start time.Time, count, interval int) ([]monthPart, error) {
	if count <= 0 {
		return nil, nil
	}
	if interval <= 0 {
		return nil, fmt.Errorf("partition_time_interval must be > 0")
	}
	if start.Day() != 1 {
		return nil, fmt.Errorf("month partition boundary %s is not the first day of a month", start.Format("2006-01-02"))
	}
	parts := make([]monthPart, 0, count)
	for i := 0; i < count; i++ {
		partMonth := start.AddDate(0, i*interval, 0)
		parts = append(parts, monthPart{
			Name:     partMonth.Format("p200601"),
			Boundary: partMonth.AddDate(0, interval, 0),
		})
	}
	return parts, nil
}

func monthBoundariesMatch(boundaries []time.Time, interval int) bool {
	if interval <= 0 || len(boundaries) < 2 {
		return false
	}
	for i := 0; i < len(boundaries)-1; i++ {
		if boundaries[i].Day() != 1 || boundaries[i+1].Day() != 1 {
			return false
		}
		expect := boundaries[i].AddDate(0, interval, 0)
		if !boundaries[i+1].Equal(expect) {
			return false
		}
	}
	return true
}

func parseMonthBoundary(raw string) (time.Time, error) {
	s := strings.TrimSpace(raw)
	if len(s) >= 10 {
		s = s[:10]
	}
	t, err := time.ParseInLocation("2006-01-02", s, time.Local)
	if err != nil {
		return time.Time{}, fmt.Errorf("invalid month partition boundary %q", raw)
	}
	return t, nil
}

func (pc *PartitionConfig) monthInitStatement(pd *PartitionDetail, now time.Time) (string, error) {
	parts, err := pc.monthInitParts(now)
	if err != nil {
		return "", err
	}
	clauses := make([]string, 0, len(parts))
	for _, part := range parts {
		clauses = append(clauses, fmt.Sprintf(
			" partition %s values less than (to_days('%s'))",
			part.Name, part.Boundary.Format("2006-01-02"),
		))
	}
	pkey := fmt.Sprintf("RANGE (TO_DAYS(%s))", pc.PartitionColumn)
	body := strings.Join(clauses, ",")
	if pd.HasUniqueKey {
		options := fmt.Sprintf(
			"--charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=%d "+
				"--critical-load=Threads_running=%d --set-vars lock_wait_timeout=%d --print --pause-file=/tmp/partition_osc_pause_%s_%s --execute ",
			PT_MAX_LOAD_THREADS_RUNNING,
			PT_CRITICAL_LOAD_THREADS_RUNNING, PT_LOCK_WAIT_TIMEOUT, pd.DbName, pd.TbName)
		return fmt.Sprintf(`D=%s,t=%s --alter "partition by %s (%s)" %s`, pd.DbName, pd.TbName, pkey, body, options), nil
	}
	return fmt.Sprintf("alter table `%s`.`%s` partition by %s (%s)", pd.DbName, pd.TbName, pkey, body), nil
}

func (pc *PartitionConfig) executeMonthInitStatement(pd *PartitionDetail, conn *native.DbWorker, forceInitInfo *ForceInitInfo) (partitionStepInfo *PartitionStepInfo) {
	partitionStepInfo = &PartitionStepInfo{
		Step:      "init",
		Status:    false,
		Message:   "",
		Statement: "",
	}

	if forceInitInfo != nil {
		err := pd.CheckUniqueKey(conn)
		if err != nil {
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	} else {
		err := pd.CheckTableSize(conn)
		if err != nil {
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	}

	initStatement, err := pc.monthInitStatement(pd, time.Now())
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

func (pc *PartitionConfig) executeMonthAddStatement(pd *PartitionDetail, conn *native.DbWorker) (partitionStepInfo *PartitionStepInfo) {
	partitionStepInfo = &PartitionStepInfo{
		Step:      "add",
		Status:    true,
		Message:   "",
		Statement: "",
	}

	if pc.IntervalCheck {
		err := pc.checkMonthInterval(pd, conn, time.Now())
		if err != nil {
			partitionStepInfo.Status = false
			partitionStepInfo.Message = err.Error()
			return partitionStepInfo
		}
	}

	addStatement, err := pc.monthAddStatement(pd, conn, time.Now())
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
		addSQL := fmt.Sprintf("set session lock_wait_timeout=%d; %s", lockWaitTimeout, addStatement)
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

func (pc *PartitionConfig) monthAddStatement(pd *PartitionDetail, conn *native.DbWorker, now time.Time) (string, error) {
	if pc.PartitionTimeInterval <= 0 {
		return "", fmt.Errorf("partition_time_interval must be > 0")
	}
	if pc.ExtraPartition < 0 {
		return "", fmt.Errorf("extra_partition must be >= 0")
	}
	existing, err := pc.listMonthPartitions(pd, conn)
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
			"partition `%s` values less than (to_days('%s'))",
			part.Name, part.Boundary.Format("2006-01-02"),
		))
	}
	return fmt.Sprintf("alter table `%s`.`%s` add partition( %s )", pd.DbName, pd.TbName, strings.Join(clauses, ",")), nil
}

func (pc *PartitionConfig) executeMonthDropStatement(pd *PartitionDetail, conn *native.DbWorker) (partitionStepInfo *PartitionStepInfo) {
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

	dropStatement, err := pc.monthDropStatement(pd, conn, time.Now())
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
		dropSQL := fmt.Sprintf("set session lock_wait_timeout=%d; %s", lockWaitTimeout, dropStatement)
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

func (pc *PartitionConfig) listMonthPartitions(pd *PartitionDetail, conn *native.DbWorker) ([]monthPart, error) {
	querySQL := "" +
		"SELECT " +
		"PARTITION_NAME AS PARTITION_NAME, " +
		"DATE_FORMAT(FROM_DAYS(PARTITION_DESCRIPTION), '%Y-%m-%d') AS BOUNDARY_DATE " +
		"FROM INFORMATION_SCHEMA.PARTITIONS " +
		"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND PARTITION_NAME IS NOT NULL " +
		"ORDER BY PARTITION_DESCRIPTION ASC"
	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)
	if err != nil {
		if strings.Contains(err.Error(), "not row found") {
			return nil, nil
		}
		return nil, err
	}
	parts := make([]monthPart, 0, len(rows))
	for _, row := range rows {
		name := row["PARTITION_NAME"].(string)
		boundary, parseErr := parseMonthBoundary(row["BOUNDARY_DATE"].(string))
		if parseErr != nil {
			return nil, parseErr
		}
		parts = append(parts, monthPart{Name: name, Boundary: boundary})
	}
	return parts, nil
}

func (pc *PartitionConfig) monthDropStatement(pd *PartitionDetail, conn *native.DbWorker, now time.Time) (string, error) {
	parts, err := pc.listMonthPartitions(pd, conn)
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

func (pc *PartitionConfig) checkMonthInterval(pd *PartitionDetail, conn *native.DbWorker, now time.Time) error {
	if pc.PartitionTimeInterval <= 0 {
		return fmt.Errorf("partition_time_interval must be > 0")
	}
	querySQL := "" +
		"SELECT " +
		"PARTITION_NAME AS PARTITION_NAME, " +
		"DATE_FORMAT(FROM_DAYS(PARTITION_DESCRIPTION), '%Y-%m-%d') AS BOUNDARY_DATE " +
		"FROM INFORMATION_SCHEMA.PARTITIONS " +
		"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND PARTITION_NAME IS NOT NULL " +
		"ORDER BY PARTITION_DESCRIPTION ASC"
	rows, err := conn.QueryWithArgs(querySQL, pd.DbName, pd.TbName)
	if err != nil {
		if strings.Contains(err.Error(), "not row found") {
			return nil
		}
		return fmt.Errorf("get month partitions: %w", err)
	}

	active := monthActiveBoundary(now)
	currentIdx := -1
	boundaries := make([]time.Time, 0, len(rows))
	names := make([]string, 0, len(rows))
	for _, row := range rows {
		boundary, parseErr := parseMonthBoundary(row["BOUNDARY_DATE"].(string))
		if parseErr != nil {
			return parseErr
		}
		names = append(names, row["PARTITION_NAME"].(string))
		boundaries = append(boundaries, boundary)
		if currentIdx < 0 && !boundary.Before(active) {
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
