package bk

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ShellResCollection TODO
type ShellResCollection struct {
	Cpu      int        `json:"cpu"`
	Mem      int        `json:"mem"` // MB
	TxRegion string     `json:"region"`
	TxZone   string     `json:"zone"`
	Disk     []DiskInfo `json:"disk"`
}

const (
	// SSD TODO
	SSD = "SSD"
)

// DiskInfo TODO
type DiskInfo struct {
	// 挂载点
	MountPoint string `json:"mount_point"`
	DiskDetail
}

// DiskDetail TODO
type DiskDetail struct {
	Size int `json:"size"`
	// 磁盘格式化类型 ext4,xfs
	FileType string `json:"file_type"`
	// 磁盘类型,是SSD还是非ssd
	DiskType string `json:"disk_type"`
	DiskId   string `json:"disk_id"`
}

// GetDiskInfoShellContent TODO
var GetDiskInfoShellContent []byte

func init() {
	c, err := GetDiskInfoScript.ReadFile(DiskInfoScriptName)
	if err != nil {
		logger.Fatal("read get disk info shell content  failed %s", err.Error())
	}
	GetDiskInfoShellContent = c
}

// GetAllDiskIds TODO
func GetAllDiskIds(c []DiskInfo) (diskIds []string) {
	for _, v := range c {
		if cmutil.IsNotEmpty(v.DiskId) {
			diskIds = append(diskIds, v.DiskId)
		}
	}
	return
}

// MarshalDisk TODO
func MarshalDisk(c []DiskInfo) (result string, err error) {
	var b []byte
	t := make(map[string]DiskDetail)
	for idx, v := range c {
		if cmutil.IsEmpty(v.MountPoint) {
			v.MountPoint = fmt.Sprintf("NOMOUNT%d", idx)
		}
		t[v.MountPoint] = v.DiskDetail
	}
	if b, err = json.Marshal(t); err != nil {
		logger.Error("marshal disk info failed ")
		return "{}", err
	}
	return string(b), nil
}

// SetDiskType TODO
func SetDiskType(elems []DiskInfo, t string) (ds []DiskInfo) {
	for _, v := range elems {
		d := v
		d.DiskType = t
		ds = append(ds, d)
	}
	return ds
}

// GetDiskInfo TODO
func GetDiskInfo(hosts []string, bk_cloud_id, bk_biz_id int) (ipLogContentMap map[string]*ShellResCollection,
	failedipLogInfo map[string]string, err error) {
	iplist := []IPList{}
	for _, ip := range hosts {
		iplist = append(iplist, IPList{
			IP:        ip,
			BkCloudID: bk_cloud_id,
		})
	}
	jober := JobV3{
		Client: EsbClient,
	}
	logger.Info("api %s", config.AppConfig.BkSecretConfig.BkBaseUrl)
	job, err := jober.ExecuteJob(&FastExecuteScriptParam{
		BkBizID:        bk_biz_id,
		ScriptContent:  base64.StdEncoding.EncodeToString(GetDiskInfoShellContent),
		ScriptTimeout:  300,
		ScriptLanguage: 1,
		AccountAlias:   "root",
		TargetServer: TargetServer{
			IPList: iplist,
		},
	},
	)
	if err != nil {
		logger.Error("call execute job failed %s", err.Error())
		return nil, nil, err
	}
	// 查询任务
	var errCnt int
	var jobStatus GetJobInstanceStatusRpData
	for i := 0; i < 100; i++ {
		jobStatus, err = jober.GetJobStatus(&GetJobInstanceStatusParam{
			BKBizId:       bk_biz_id,
			JobInstanceID: job.JobInstanceID,
		})
		if err != nil {
			logger.Error("query job %d status failed %s", job.JobInstanceID, err.Error())
			errCnt++
		}
		if jobStatus.Finished {
			break
		}
		if errCnt > 10 {
			return nil, nil, fmt.Errorf("more than 10 errors when query job %d,some err: %s", job.JobInstanceID, err.Error())
		}
		time.Sleep(1 * time.Second)
	}
	// 在查询一遍转态
	jobStatus, err = jober.GetJobStatus(&GetJobInstanceStatusParam{
		BKBizId:       bk_biz_id,
		JobInstanceID: job.JobInstanceID,
	})
	if err != nil {
		logger.Error("query job %d status failed %s", job.JobInstanceID, err.Error())
		return nil, nil, err
	}
	failedipLogInfo = make(map[string]string)
	for _, stepInstance := range jobStatus.StepInstanceList {
		for _, step_ip_result := range stepInstance.StepIpResultList {
			switch step_ip_result.Status {
			case 1:
				failedipLogInfo[step_ip_result.IP] += "Agent异常\n"
			case 12:
				failedipLogInfo[step_ip_result.IP] += "任务下发失败\n"
			case 403:
				failedipLogInfo[step_ip_result.IP] += "任务强制终止成功\n"
			case 404:
				failedipLogInfo[step_ip_result.IP] += "任务强制终止失败\n"
			case 11:
				failedipLogInfo[step_ip_result.IP] += "执行失败;\n"
			default:
				continue
			}
		}
	}
	// 查询执行输出
	var ipLogs BatchGetJobInstanceIpLogRpData
	ipLogs, err = jober.BatchGetJobInstanceIpLog(&BatchGetJobInstanceIpLogParam{
		BKBizId:        bk_biz_id,
		JobInstanceID:  job.JobInstanceID,
		StepInstanceID: job.StepInstanceID,
		IPList:         iplist,
	})
	ipLogContentMap = make(map[string]*ShellResCollection)
	for _, d := range ipLogs.ScriptTaskLogs {
		var dl ShellResCollection
		if err = json.Unmarshal([]byte(d.LogContent), &dl); err != nil {
			logger.Error("unmarshal log content failed %s", err.Error())
			continue
		}
		ipLogContentMap[d.Ip] = &dl
	}
	return ipLogContentMap, failedipLogInfo, err
}
