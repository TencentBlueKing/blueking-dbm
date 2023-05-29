package checker

import (
	"bufio"
	"fmt"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"

	"golang.org/x/exp/slog"
)

func summary(stdout string) (summaries []ChecksumSummary, err error) {
	scanner := bufio.NewScanner(strings.NewReader(stdout))
	scanner.Split(bufio.ScanLines)

	isSummary := false
	SplitRe, _ := regexp.Compile(`\s+`)

	for scanner.Scan() {
		line := scanner.Text()
		/*
			Checking if all tables can be checksummed ...
			Starting checksum ...
			            TS ERRORS  DIFFS     ROWS  DIFF_ROWS  CHUNKS SKIPPED    TIME TABLE
			11-07T15:22:36      0      0        0          0       1       0   0.563 mysql.time_zone_leap_second
			11-07T15:22:38      0      0     1826          0       4       0   2.242 mysql.time_zone_name

			pt-table-checksum 的标准输出是这样子, 如果找到 TS 行
			就认为接下来的是报表
		*/
		if strings.HasPrefix(strings.TrimSpace(line), "TS") {
			isSummary = true
			continue
		}
		if isSummary {
			var cs ChecksumSummary
			splitRow := SplitRe.Split(line, -1)

			// pt-table-checksum 摘要的 ts 缺少年份信息, 得自己加上
			ts, err := time.ParseInLocation(
				"2006-01-02T15:04:05",
				fmt.Sprintf(`%d-%s`, time.Now().Year(), splitRow[0]),
				time.Local,
			)
			if err != nil {
				slog.Error("parse time", err, slog.String("original row", line))
				return nil, err
			}

			cs.Ts = ts
			cs.Errors, _ = strconv.Atoi(splitRow[1])
			cs.Diffs, _ = strconv.Atoi(splitRow[2])
			cs.Rows, _ = strconv.Atoi(splitRow[3])
			cs.DiffRows, _ = strconv.Atoi(splitRow[4])
			cs.Chunks, _ = strconv.Atoi(splitRow[5])
			cs.Skipped, _ = strconv.Atoi(splitRow[6])
			cs.Time, _ = strconv.Atoi(splitRow[7])
			cs.Table = splitRow[8]

			summaries = append(summaries, cs)
		}
	}
	return summaries, nil
}

func collectFlags(exitErr *exec.ExitError) (ptFlags []PtExitFlag) {
	exitCode := exitErr.ExitCode()
	for k, v := range PtExitFlagMap {
		if exitCode&k != 0 {
			ptFlags = append(ptFlags, v)
		}
	}
	return
}
