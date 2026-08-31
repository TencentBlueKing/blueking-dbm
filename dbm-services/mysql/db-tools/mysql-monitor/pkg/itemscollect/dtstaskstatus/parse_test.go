package dtstaskstatus

import (
	"testing"
)

func TestParseTaskList_StatusList(t *testing.T) {
	body := []byte(`{
		"total": 1,
		"data": [{
			"name": "t1",
			"status_list": [{
				"name": "t1",
				"source_name": "s1",
				"stage": "Running",
				"sync_status": {"seconds_behind_master": 3}
			}]
		}]
	}`)
	got, err := parseTaskList(body)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 {
		t.Fatalf("len=%d", len(got))
	}
	if got[0].TaskName != "t1" || got[0].SourceName != "s1" || got[0].StageValue != 2 {
		t.Fatalf("got %+v", got[0])
	}
	if got[0].Lag == nil || *got[0].Lag != 3 {
		t.Fatalf("lag %+v", got[0].Lag)
	}
}

func TestParseTaskList_FlatSubTask(t *testing.T) {
	body := []byte(`{
		"total": 1,
		"data": [{
			"name": "t2",
			"source_name": "src-a",
			"stage": "Paused"
		}]
	}`)
	got, err := parseTaskList(body)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 || got[0].StageValue != 3 || got[0].Lag != nil {
		t.Fatalf("got %+v", got)
	}
}

func TestParseTaskList_UnscheduledAndFailed(t *testing.T) {
	body := []byte(`{
		"total": 2,
		"data": [
			{"name":"t-off","source_name":"s1","stage":"Unscheduled"},
			{"name":"t-fail","source_name":"s2","stage":"Failed"}
		]
	}`)
	got, err := parseTaskList(body)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 2 {
		t.Fatalf("len=%d", len(got))
	}
	if got[0].Stage != "Unscheduled" || got[0].StageValue != 8 {
		t.Fatalf("unscheduled %+v", got[0])
	}
	if got[1].Stage != "Failed" || got[1].StageValue != 6 {
		t.Fatalf("failed %+v", got[1])
	}
}

func TestParseTaskList_UnknownStageErrors(t *testing.T) {
	body := []byte(`{"total":1,"data":[{"name":"t3","source_name":"s","stage":"Weird"}]}`)
	got, err := parseTaskList(body)
	if err == nil {
		t.Fatalf("expected error, got %+v", got)
	}
	if got != nil {
		t.Fatalf("expected nil slice on error, got %+v", got)
	}
}

func TestParseTaskList_Empty(t *testing.T) {
	got, err := parseTaskList([]byte(`{"total":0,"data":[]}`))
	if err != nil || len(got) != 0 {
		t.Fatalf("err=%v got=%v", err, got)
	}
}

func TestTaskDimension_FromTaskName(t *testing.T) {
	dim := taskDimension(parsedSubTask{TaskName: "mysql-dts-950-12-34", SourceName: "s1"})
	if dim["dts_ticket_id"] != "950" || dim["dts_task_name"] != "mysql-dts-950-12-34" || dim["dts_source_name"] != "s1" {
		t.Fatalf("got %v", dim)
	}
}

func TestTaskDimension_MultiSourceSuffix(t *testing.T) {
	name := "mysql-dts-950-1_2-34-abcdef012345"
	dim := taskDimension(parsedSubTask{TaskName: name, SourceName: "s1"})
	if dim["dts_ticket_id"] != "950" || dim["dts_task_name"] != name {
		t.Fatalf("got %v", dim)
	}
}

func TestTaskDimension_UnknownName(t *testing.T) {
	dim := taskDimension(parsedSubTask{TaskName: "t1", SourceName: "s1"})
	if dim["dts_ticket_id"] != "0" || dim["dts_task_name"] != "t1" {
		t.Fatalf("got %v", dim)
	}
	empty := taskDimension(parsedSubTask{TaskName: "", SourceName: "s1"})
	if empty["dts_ticket_id"] != "0" {
		t.Fatalf("empty name got %v", empty)
	}
}
