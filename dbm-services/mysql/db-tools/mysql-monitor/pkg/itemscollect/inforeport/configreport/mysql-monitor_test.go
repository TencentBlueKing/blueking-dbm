package configreport

import (
	"strings"
	"testing"

	"gopkg.in/yaml.v2"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func TestMonitorItemToJSON(t *testing.T) {
	content := `
- name: scene-snapshot
  enable: true
  schedule: '@every 1m'
  machine_type: [spider, remote, backend, single]
  role: []
  options:
    snapshot_on_demand: true
    snapshot_keep_hours: 48
    snapshot_long_query_exclude_user: [dba_bak_all_sel, MONITOR]
    query_kill_rules:
      - rule_name: bad-query-1
        match_user: xxuser
        time_gt: 60
- name: db-up
  enable: true
`
	var items []*config.MonitorItem
	if err := yaml.UnmarshalStrict([]byte(content), &items); err != nil {
		t.Fatal(err)
	}
	if len(items) != 2 {
		t.Fatalf("expect 2 items, got %d", len(items))
	}

	itemsMap := make(map[string]*config.MonitorItem)
	for _, item := range items {
		item.Options = normalizeYamlMap(item.Options)
		itemsMap[item.Name] = item
	}
	_, body, err := MaskedJSONPayload(itemsMap)
	if err != nil {
		t.Fatalf("MaskedJSONPayload: %v", err)
	}
	if !strings.HasPrefix(body, `{"db-up":{`) {
		t.Errorf("whole file should be a json object keyed by item name: %s", body)
	}
	for _, s := range []string{
		`"scene-snapshot":{`,
		`"name":"scene-snapshot"`,
		`"schedule":"@every 1m"`,
		`"snapshot_keep_hours":48`,
		`"query_kill_rules":[{"match_user":"xxuser","rule_name":"bad-query-1","time_gt":60}]`,
		`"role":[]`,
		`"name":"db-up"`,
		`"options":null`,
	} {
		if !strings.Contains(body, s) {
			t.Errorf("expect %s in %s", s, body)
		}
	}
}
