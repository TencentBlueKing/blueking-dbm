package atommongodb

import (
	"encoding/json"
	"testing"
)

func TestRemoveExporterFromProcJSON_RemovesOnlyTargetExporter(t *testing.T) {
	t.Parallel()

	const procJSON = `{
		"proc": [
			{
				"procName": "bkmonitorbeat",
				"setupPath": "/path/to/gse2_bkte/plugins/bin",
				"pidPath": "/var/run/gse2_bkte/bkmonitorbeat.pid",
				"contact": "nodeman",
				"startCmd": "./start.sh bkmonitorbeat",
				"stopCmd": "./stop.sh bkmonitorbeat",
				"restartCmd": "./restart.sh bkmonitorbeat",
				"reloadCmd": "./reload.sh bkmonitorbeat",
				"killCmd": "",
				"versionCmd": "./bkmonitorbeat -v",
				"healthCmd": "",
				"type": 1,
				"cpulmt": 10,
				"memlmt": 10,
				"user": "root",
				"password": "",
				"userPwd": ":::root@@@",
				"valuekey": "nodeman:bkmonitorbeat",
				"startCheckBeginTime": 30,
				"startCheckEndTime": 0,
				"opTimeOut": 60,
				"operateType": 7,
				"timestamp": 1754358646
			},
			{
				"procName": "bkunifylogbeat",
				"setupPath": "/path/to/gse2_bkte/plugins/bin",
				"pidPath": "/var/run/gse2_bkte/bkunifylogbeat.pid",
				"contact": "nodeman",
				"startCmd": "./start.sh bkunifylogbeat",
				"stopCmd": "./stop.sh bkunifylogbeat",
				"restartCmd": "./restart.sh bkunifylogbeat",
				"reloadCmd": "./reload.sh bkunifylogbeat",
				"killCmd": "",
				"versionCmd": "./bkunifylogbeat -v",
				"healthCmd": "",
				"type": 1,
				"cpulmt": 30,
				"memlmt": 10,
				"user": "root",
				"password": "",
				"userPwd": ":::root@@@",
				"valuekey": "nodeman:bkunifylogbeat",
				"startCheckBeginTime": 30,
				"startCheckEndTime": 0,
				"opTimeOut": 60,
				"operateType": 3,
				"timestamp": 1747889407
			},
			{
				"procName": "dbm_mongodb_exporter",
				"setupPath": "/path/to/gse2_bkte/external_plugins/sub_123_service_456/dbm_mongodb_exporter",
				"pidPath": "/var/run/gse2_bkte/sub_123_service_456/dbm_mongodb_exporter.pid",
				"contact": "nodeman",
				"startCmd": "./start.sh",
				"stopCmd": "./stop.sh",
				"restartCmd": "./restart.sh",
				"reloadCmd": "./reload.sh",
				"killCmd": "",
				"versionCmd": "cat VERSION",
				"healthCmd": "",
				"type": 1,
				"cpulmt": 10,
				"memlmt": 10,
				"user": "root",
				"password": "",
				"userPwd": ":::root@@@",
				"valuekey": "nodeman:sub_123_service_456_dbm_mongodb_exporter",
				"startCheckBeginTime": 30,
				"startCheckEndTime": 0,
				"opTimeOut": 60,
				"operateType": 7,
				"timestamp": 1750997394
			}
		]
	}`

	out, changed, err := removeExporterFromProcJSON([]byte(procJSON), "dbm_mongodb_exporter")
	if err != nil {
		t.Fatalf("removeExporterFromProcJSON failed: %v", err)
	}
	if !changed {
		t.Fatal("expected changed=true")
	}

	var parsed map[string][]map[string]any
	if err := json.Unmarshal(out, &parsed); err != nil {
		t.Fatalf("output is not valid json: %v", err)
	}

	procs := parsed["proc"]
	if len(procs) != 2 {
		t.Fatalf("proc count=%d, want 2", len(procs))
	}
	for _, proc := range procs {
		name, _ := proc["procName"].(string)
		if name == "dbm_mongodb_exporter" {
			t.Fatalf("target exporter should be removed, got proc=%v", proc)
		}
	}
}

func TestRemoveExporterFromProcJSON_SubstringInPathDoesNotRemove(t *testing.T) {
	t.Parallel()

	// 路径/value 中含 dbm_mongodb_exporter 子串，但 procName 不同 — 不应误删
	const procJSON = `{
		"proc": [
			{
				"procName": "other_beat",
				"setupPath": "/x/external_plugins/sub_1/dbm_mongodb_exporter",
				"valuekey": "nodeman:sub_1_dbm_mongodb_exporter"
			}
		]
	}`

	out, changed, err := removeExporterFromProcJSON([]byte(procJSON), "dbm_mongodb_exporter")
	if err != nil {
		t.Fatalf("removeExporterFromProcJSON failed: %v", err)
	}
	if changed {
		t.Fatal("expected changed=false when only path fields contain substring")
	}
	if string(out) != procJSON {
		t.Fatalf("output changed unexpectedly, got=%s", string(out))
	}
}

func TestRemoveExporterFromProcJSON_NoMatchReturnsUnchanged(t *testing.T) {
	t.Parallel()

	const procJSON = `{
		"proc": [
			{"procName": "bkmonitorbeat"},
			{"procName": "bkunifylogbeat"}
		]
	}`

	out, changed, err := removeExporterFromProcJSON([]byte(procJSON), "dbm_mongodb_exporter")
	if err != nil {
		t.Fatalf("removeExporterFromProcJSON failed: %v", err)
	}
	if changed {
		t.Fatal("expected changed=false")
	}
	if string(out) != procJSON {
		t.Fatalf("output changed unexpectedly, got=%s", string(out))
	}
}

func TestRemoveExporterFromProcJSON_InvalidJSON(t *testing.T) {
	t.Parallel()

	_, _, err := removeExporterFromProcJSON([]byte("{invalid"), "dbm_mongodb_exporter")
	if err == nil {
		t.Fatal("expected json parse error")
	}
}
