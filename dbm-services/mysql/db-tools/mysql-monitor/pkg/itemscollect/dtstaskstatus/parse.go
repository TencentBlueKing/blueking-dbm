package dtstaskstatus

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

const (
	metricTaskState = "dts_worker_task_state"
	metricLag       = "dts_replication_lag_seconds"
)

// 0-5 保持原语义；Failed/Error/Unscheduled 是 OpenAPI 会返回、原先被静默丢掉的阶段。
var stageValue = map[string]int64{
	"Invalid":     0,
	"New":         1,
	"Running":     2,
	"Paused":      3,
	"Stopped":     4,
	"Finished":    5,
	"Failed":      6,
	"Error":       7,
	"Unscheduled": 8,
}

type taskListResponse struct {
	Data  []json.RawMessage `json:"data"`
	Total int               `json:"total"`
}

type syncStatus struct {
	SecondsBehindMaster *int64 `json:"seconds_behind_master"`
}

type statusItem struct {
	Name       string       `json:"name"`
	SourceName string       `json:"source_name"`
	Stage      string       `json:"stage"`
	SyncStatus *syncStatus  `json:"sync_status"`
	StatusList []statusItem `json:"status_list"`
}

type parsedSubTask struct {
	TaskName   string
	SourceName string
	Stage      string
	StageValue int64
	Lag        *int64
}

func parseTaskList(body []byte) ([]parsedSubTask, error) {
	var resp taskListResponse
	if err := json.Unmarshal(body, &resp); err != nil {
		return nil, err
	}
	out := make([]parsedSubTask, 0)
	for _, raw := range resp.Data {
		var item statusItem
		if err := json.Unmarshal(raw, &item); err != nil {
			return nil, err
		}
		if len(item.StatusList) > 0 {
			for _, sub := range item.StatusList {
				p, err := toParsed(sub, item.Name)
				if err != nil {
					return nil, err
				}
				out = append(out, p)
			}
			continue
		}
		p, err := toParsed(item, "")
		if err != nil {
			return nil, err
		}
		out = append(out, p)
	}
	return out, nil
}

func toParsed(item statusItem, fallbackName string) (parsedSubTask, error) {
	stage := strings.TrimSpace(item.Stage)
	val, ok := stageValue[stage]
	if !ok {
		return parsedSubTask{}, fmt.Errorf("unknown dts task stage %q", stage)
	}
	name := item.Name
	if name == "" {
		name = fallbackName
	}
	if name == "" {
		return parsedSubTask{}, fmt.Errorf("dts task missing name")
	}
	p := parsedSubTask{
		TaskName:   name,
		SourceName: item.SourceName,
		Stage:      stage,
		StageValue: val,
	}
	if item.SyncStatus != nil && item.SyncStatus.SecondsBehindMaster != nil {
		lag := *item.SyncStatus.SecondsBehindMaster
		p.Lag = &lag
	}
	return p, nil
}

var ticketFromTaskNameRE = regexp.MustCompile(`^mysql-dts-(\d+)`)

func ticketIDFromTaskName(name string) string {
	m := ticketFromTaskNameRE.FindStringSubmatch(name)
	if len(m) < 2 {
		return "0"
	}
	return m[1]
}

func taskDimension(task parsedSubTask) map[string]interface{} {
	return map[string]interface{}{
		"dts_ticket_id":   ticketIDFromTaskName(task.TaskName),
		"dts_task_name":   task.TaskName,
		"dts_source_name": task.SourceName,
	}
}
