package atomsys

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"encoding/json"
	"os"
	"strconv"
	"testing"
)

func TestKeyStat(t *testing.T) {
	apiServer := os.Getenv("KeyStat_API_SERVER")
	token := os.Getenv("KeyStat_DB_CLOUD_TOKEN")
	cloudId, err := strconv.Atoi(os.Getenv("KeyStat_DB_CLOUD_ID"))
	if err != nil {
		t.Errorf("strconv.Atoi failed, err:%v", err)
		return
	}

	if apiServer == "" || token == "" {
		t.Errorf("apiServer or token or cloudId is empty")
		return
	}

	param := KeyStatParams{
		RedisPassword:   "x",
		ApiServer:       apiServer,
		BkCloudId:       cloudId,
		DbCloudToken:    token,
		RecordId:        1,
		ExecIp:          "127.0.0.1",
		CheckInterval:   1,
		ClusterId:       1,
		ClusterShardNum: 1000,
		InsList: []KeyStatIns{
			{
				Addr:        "127.0.0.1:6379",
				SlaveAddr:   "127.0.0.1:6379",
				ShardName:   "test",
				StartBucket: 0,
				EndBucket:   1000000,
			},
		},
	}
	payload, err := json.Marshal(param)
	if err != nil {
		t.Errorf("json.Marshal failed, err:%v", err)
		return
	}
	runtime, err := jobruntime.NewJobGenericRuntime(
		"111", "222", "3333", "4444",
		string(payload), consts.PayloadFormatRaw, "keystat", "test", 1)
	if err != nil {
		t.Errorf("NewJobGenericRuntime failed, err:%v", err)
		return
	}
	v := NewKeyStat()
	err = v.Init(runtime)
	if err != nil {
		t.Errorf("Init failed, err:%v", err)
		return
	}
	err = v.Run()
	if err != nil {
		t.Errorf("Run failed, err:%v", err)
		return
	}
}
