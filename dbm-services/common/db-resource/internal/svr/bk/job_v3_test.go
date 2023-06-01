package bk_test

import (
	"encoding/base64"
	"os"
	"testing"

	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cc.v3"
)

var BKBizId = 9999431

func TestExecuteJob(t *testing.T) {
	client, err := cc.NewClient(os.Getenv("BK_BASE_URL"), cc.Secret{
		BKAppCode:   os.Getenv("BK_APP_CODE"),
		BKAppSecret: os.Getenv("BK_APP_SECRET"),
		BKUsername:  os.Getenv("BK_USERNAME"),
	})
	if err != nil {
		t.Fatal("new cc client failed", err.Error())
		return
	}
	c, err := bk.GetDiskInfoScript.ReadFile(bk.DiskInfoScriptName)
	if err != nil {
		t.Fatal(err)
	}
	jober := bk.JobV3{
		Client: client,
	}
	data, err := jober.ExecuteJob(&bk.FastExecuteScriptParam{
		BkBizID:        BKBizId,
		ScriptContent:  base64.StdEncoding.EncodeToString(c),
		ScriptTimeout:  180,
		ScriptLanguage: 1,
		AccountAlias:   "mysql",
		TargetServer: bk.TargetServer{
			IPList: []bk.IPList{
				{
					BkCloudID: 0,
					IP:        "127.0.0.1",
				},
			},
		},
	})
	if err != nil {
		t.Logf("execute job failed %s\n", err.Error())
		return
	}
	t.Log(data.JobInstanceID)
}

func TestGetJobInstanceStatus(t *testing.T) {
	t.Logf("start testing \n")
	// t.Log(os.Getenv("BK_BASE_URL"))
	client, err := cc.NewClient(os.Getenv("BK_BASE_URL"), cc.Secret{
		BKAppCode:   os.Getenv("BK_APP_CODE"),
		BKAppSecret: os.Getenv("BK_APP_SECRET"),
		BKUsername:  os.Getenv("BK_USERNAME"),
	})
	if err != nil {
		t.Fatal("new cc client failed", err.Error())
		return
	}
	jober := bk.JobV3{
		Client: client,
	}
	data, err := jober.GetJobStatus(&bk.GetJobInstanceStatusParam{
		BKBizId:       BKBizId,
		JobInstanceID: 27936528246,
	})
	if err != nil {
		t.Fatal("get job status failed", err.Error())
	}
	t.Logf("%v", data.JobInstance)
	t.Logf("%v", data.StepInstanceList)
	data1, err := jober.BatchGetJobInstanceIpLog(&bk.BatchGetJobInstanceIpLogParam{
		BKBizId:        BKBizId,
		JobInstanceID:  27936528246,
		StepInstanceID: 27996200699,
		IPList:         []bk.IPList{{BkCloudID: 0, IP: "127.0.0.1"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	t.Log(data1.ScriptTaskLogs[0].LogContent)
	t.Logf("end testing ...")
}
