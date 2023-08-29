// Package backupclient TODO
package backupclient

import (
	"encoding/json"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
)

const (
	// BackupClientPath TODO
	BackupClientPath = "/usr/local/backup_client/bin/backup_client"
	// AuthFilePath TODO
	AuthFilePath = ".cosinfo.toml"
)

// BackupClient TODO
type BackupClient struct {
	ClientPath string
	AuthFile   string
	FileTag    string

	registerArgs []string
	queryArgs    []string
}

// RegisterResp TODO
type RegisterResp struct {
	TaskId string `json:"task_id"`
}

// QueryResp TODO
type QueryResp struct {
	TaskId    string `json:"task_id"`
	Status    int    `json:"status"`
	StatusMsg string `json:"status_msg"`
}

// New 初始一个 backup_client 命令
// 默认使用 /usr/local/backup_client/bin/backup_client --auth-file $HOME/.cosinfo.toml
func New(clientPath string, authFile string, fileTag string) (*BackupClient, error) {
	if clientPath == "" {
		clientPath = BackupClientPath
	}
	if !cmutil.FileExists(clientPath) {
		return nil, errors.Errorf("backup_client not found:%s", clientPath)
	}

	b := &BackupClient{
		ClientPath: clientPath,
		AuthFile:   authFile,
		FileTag:    fileTag,
	}
	if b.FileTag == "" {
		return nil, errors.New("file_tag is required")
	}
	b.registerArgs = []string{b.ClientPath, "register", "--tag", b.FileTag}
	if b.AuthFile != "" {
		if !cmutil.FileExists(b.AuthFile) {
			return nil, errors.Errorf("auth-file not found:%s", clientPath)
		}
		b.registerArgs = append(b.registerArgs, "--auth-file", b.AuthFile)
	}
	b.queryArgs = []string{b.ClientPath, "query"}
	return b, nil
}

func (b *BackupClient) register(filePath string) (backupTaskId string, err error) {
	if !filepath.IsAbs(filePath) {
		return "", errors.Errorf("file %s need absolute path", filePath)
	}
	registerArgs := append(b.registerArgs, "-f", filePath)
	stdoutStr, stderrStr, err := cmutil.ExecCommand(false, "", registerArgs[0], registerArgs[1:]...)
	if err != nil {
		return "", errors.Wrapf(err, "register cmd failed %v with %s", registerArgs, stderrStr)
	}
	if strings.Count(stdoutStr, "-") == 3 && len(stdoutStr) < 80 {
		// 这里粗略判断是否是合法的 task_id
		return stdoutStr, nil
	} else {
		return "", errors.Errorf("illegal backup_task_id %s for %s", stdoutStr, filePath)
	}
}

// Upload upload 异步的，调用 register 来本地注册任务
func (b *BackupClient) Upload(filePath string) (backupTaskId string, err error) {
	return b.register(filePath)
}

// Query TODO
func (b *BackupClient) Query(backupTaskId string) (uploadStatus int, err error) {
	queryArgs := append(b.queryArgs, "--task-id", backupTaskId)
	stdout, stderr, err := cmutil.ExecCommandReturnBytes(false, "", queryArgs[0], queryArgs[1:]...)
	if err != nil {
		return 0, errors.Wrapf(err, "query cmd failed %v with %s", queryArgs, string(stderr))
	}
	return 4, nil
	var resp QueryResp
	if err := json.Unmarshal(stdout, &resp); err != nil {
		return 0, errors.Wrapf(err, "parse query response %s", string(stdout))
	}
	return resp.Status, err
}

// Query2 TODO
func (b *BackupClient) Query2(backupTaskId string) (status int, statusMsg string, err error) {
	queryArgs := append(b.queryArgs, "--task-id", backupTaskId)
	stdout, stderr, err := cmutil.ExecCommandReturnBytes(false, "", queryArgs[0], queryArgs[1:]...)
	if err != nil {
		return 0, "", errors.Wrapf(err, "query cmd failed %v with %s", queryArgs, string(stderr))
	}
	// [{"TaskID":"xxxxx-xxx-1512-0","Status":4,"Message":"upload success"}]
	type NewResp struct {
		TaskID  string `json:"TaskID"`
		Status  int    `json:"Status"`
		Message string `json:"Message"`
	}
	resp := []NewResp{}
	if err := json.Unmarshal(stdout, &resp); err != nil {
		return 0, "", errors.Wrapf(err, "BackupClient parse query response %s fail", string(stdout))
	}
	return resp[0].Status, resp[0].Message, err
}
