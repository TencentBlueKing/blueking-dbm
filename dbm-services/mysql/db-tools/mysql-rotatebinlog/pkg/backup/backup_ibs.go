package backup

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
)

const (
	// IBSModeCos TODO
	IBSModeCos = "cos"
	// IBSModeHdfs TODO
	IBSModeHdfs = "hdfs"
)

// IBSBackupClient TODO
type IBSBackupClient struct {
	Enable   bool   `mapstructure:"enable" json:"enable"`
	ToolPath string `mapstructure:"tool_path" json:"tool_path" validate:"required"`
	WithMD5  bool   `mapstructure:"with_md5" json:"with_md5"`
	FileTag  string `mapstructure:"file_tag" json:"file_tag" validate:"required"`
	IBSMode  string `mapstructure:"ibs_mode" json:"ibs_mode" validate:"required" enums:"hdfs,cos"`

	// ibsBackup string
	ibsQueryCmd  string
	ibsUploadCmd string
}

// Init TODO
func (o *IBSBackupClient) Init() error {
	if err := validate.GoValidateStruct(o, false, false); err != nil {
		return err
	}
	o.ibsQueryCmd = o.ToolPath
	o.ibsUploadCmd = fmt.Sprintf("%s -n --tag %s", o.ToolPath, o.FileTag)
	if o.WithMD5 {
		o.ibsUploadCmd += " --with-md5"
	}
	if o.IBSMode == IBSModeCos {
		o.ibsUploadCmd += " -c"
	}
	return nil
}

// Upload 提交上传任务，等候调度，异步上传
func (o *IBSBackupClient) Upload(fileName string) (taskId string, err error) {
	logger.Info("backup upload to ibs: %s", fileName)
	backupCmd := fmt.Sprintf(`%s -f %s`, o.ibsUploadCmd, fileName)
	var stdout, stderr string
	if stdout, stderr, err = cmutil.ExecCommand(true, "", backupCmd); err != nil {
		return "", errors.Wrapf(err, "upload failed:%s", stderr)
	}
	reTaskId := regexp.MustCompile(`taskid:(\d+)`)
	if matches := reTaskId.FindStringSubmatch(stdout); len(matches) == 2 {
		if _, err = strconv.ParseInt(matches[1], 10, 64); err != nil {
			return "", errors.Errorf("parse taskid failed for %s: %v", fileName, matches)
		}
		taskId = matches[1]
		return taskId, nil
	} else {
		return "", errors.Errorf("failed to match backup taskid for %s", fileName)
	}
}

// Query QueryTaskStatus
func (o *IBSBackupClient) Query(taskid string) (taskStatus int, err error) {
	// queryCmd := fmt.Sprintf(`%s -q --taskid=%s`, o.IBSBackup, taskid)
	queryCmd := fmt.Sprintf(`%s -q --taskid %s`, o.ibsQueryCmd, taskid)
	var stdout, stderr string
	if stdout, stderr, err = cmutil.ExecCommand(true, "", queryCmd); err != nil {
		return 0, errors.Wrapf(err, "query failed:%s", stderr)
	}
	outLines := strings.Split(stdout, "\n")
	lineMap := map[string]string{
		"sendup datetime": "",
		"status":          "",
		"status info":     "",
		"expire_time":     "",
		"complete_time":   "",
	}
	for _, l := range outLines {
		if !strings.Contains(l, ":") { // key : value 才是合法的一行输出
			continue
		}
		if lkv := strings.SplitN(l, ":", 2); len(lkv) != 2 {
			return 0, errors.Errorf("error format parsing backup query result:%s", l)
		} else {
			k := strings.TrimSpace(lkv[0])
			lineMap[k] = strings.TrimSpace(lkv[1])
		}
	}
	// logger.Info("query task[%s]: %+v", queryCmd, lineMap)
	if taskStatus, err = strconv.Atoi(lineMap["status"]); err != nil {
		return 0, errors.Errorf("invalid backup task status %s. queryCmd:%s", lineMap["status"], queryCmd)
	} else {
		return taskStatus, nil
	}
}
