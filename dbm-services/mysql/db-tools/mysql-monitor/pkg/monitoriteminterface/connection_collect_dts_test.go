package monitoriteminterface

import (
	"testing"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func TestNewConnectionCollect_DtsSkipsMysql(t *testing.T) {
	biz, cloud, inst := 20, 0, int64(0)
	for _, mt := range []string{"mysql_dts_master", "mysql_dts_worker"} {
		t.Run(mt, func(t *testing.T) {
			config.MonitorConfig = &config.Config{
				BkBizId:      biz,
				Ip:           "127.0.0.1",
				Port:         18301,
				BkInstanceId: &inst,
				MachineType:  mt,
				BkCloudID:    &cloud,
			}
			cc, err := NewConnectionCollect()
			if err != nil {
				t.Fatalf("dts machine_type should not connect mysql: %v", err)
			}
			if cc == nil || cc.MySqlDB != nil {
				t.Fatalf("expected empty collect, got %#v", cc)
			}
		})
	}
}
