package backup_download

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/httpclient"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"runtime/debug"
	"strconv"
	"time"

	"github.com/pkg/errors"
)

// IBSRecoverComp TODO
type IBSRecoverComp struct {
	Params IBSRecoverParam `json:"extend"`
}

// TaskFilesWild TODO
type TaskFilesWild struct {
	FileTag string `json:"file_tag"`
	// 搜索的模糊条件，不用带 *
	NameSearch string `json:"name_search"`
	// 在搜索的结果里面，应用该正则进行过滤
	NameRegex string `json:"name_regex"`
}

// TaskFilesExact TODO
type TaskFilesExact struct {
	// 任务ID，用于下载
	TaskId   string `json:"task_id,omitempty"`
	FileName string `json:"file_name,omitempty"`
	// 文件大小
	Size string `json:"size,omitempty"`
	Md5  string `json:"md5,omitempty"`
}

// IBSRecoverParam download ibs-recover
type IBSRecoverParam struct {
	IBSRecoverReq
	// ieg backup system url and auth params
	IBSInfo IBSBaseInfo `json:"ibs_info" validate:"required"`
	// 如果是精确文件名下载，用 task_files。提供需要下载的文件列表，提供 task_id 或者完整的 file_name 即可
	// 如果顺便提供了 size 信息则不用请求备份系统获取大小 来决定文件是否需要重新下载
	TaskFiles []TaskFilesExact `json:"task_files"`
	// 如果是模糊匹配搜索并下载，用 task_files_wild
	TaskFilesWild *TaskFilesWild `json:"task_files_wild"`

	// 如果本地目标目录已经存在对应文件，是否保留(即跳过下载). 默认 false
	SkipLocalExists bool `json:"skip_local_exists" example:"false"`
	// 根据文件名下载，或者判断是否跳过下载时，需要提供 ibs_query 参数用于查询
	IBSQuery IBSQueryForRecover `json:"ibs_query"`

	taskIdSlice []string

	client             *httpclient.HttpClient
	maxQueryRetryTimes int
	maxFailCheckNum    int
}

// IBSRecoverTask 与 IBSQueryResult 基本相同
// task_id="" 时，会根据 file_name 来查询 task_id
// 其它信息用于下载完成后进行校验，一般在给 task_id 时有效(来源于上一次备份查询接口)
// 当 task_id !="" file_name!="" 时，下载之前会检查目标目录文件是否已经存在，决定是否跳过下载
// 只提供 task_id 时是无法检查文件是跳过下载，会直接从备份系统下载该 task_id
// 当只提供 file_name 时，会从备份系统先搜索出 task_id，file size，如果文件大小匹配则跳过下载
type IBSRecoverTask struct {
	// 任务ID，用于下载
	TaskId   string `json:"task_id,omitempty"`
	FileName string `json:"file_name,omitempty"`
	// 文件大小
	Size string `json:"size,omitempty"`
	Md5  string `json:"md5,omitempty"`
	// 文件状态
	Status string `json:"status,omitempty"`
	// 文件最后修改时间
	FileLastMtime string `json:"file_last_mtime,omitempty"`
	// 上报该备份任务的IP
	SourceIp string `json:"source_ip,omitempty"`
	FileTag  string `json:"file_tag,omitempty"`
}

// IBSQueryForRecover 复刻 IBSQueryReq，去掉 required 选项
type IBSQueryForRecover struct {
	// 来源IP，即提交备份任务的机器IP
	SourceIp string `json:"source_ip"`
	// 查询文件起始时间，备份系统以 file_last_mtime 为条件
	BeginDate string `json:"begin_date"`
	// 哪一天提交，结束时间，与begin_date形成一个时间范围，建议begin_date与end_date形成的时间范围不要超过3天
	EndDate string `json:"end_date"`
}

// Example TODO
func (c *IBSRecoverComp) Example() interface{} {
	ibsReq := IBSRecoverParam{
		maxQueryRetryTimes: 100,
		maxFailCheckNum:    6,
		IBSInfo: IBSBaseInfo{
			SysID:  "bkdbm",
			Key:    "fzLosxxxxxxxxxxxx",
			Ticket: "",
			Url:    "http://{{BACKUP_SERVER}}",
		},
		IBSRecoverReq: IBSRecoverReq{
			TaskidList:  "",
			DestIp:      "1.1.1.1",
			Directory:   "/data/dbbak",
			LoginUser:   "mysql",
			LoginPasswd: "xxx",
			Reason:      "example recover",
		},
		TaskFiles: []TaskFilesExact{
			{FileName: "xxx", TaskId: "111", Size: "1023"},
			{FileName: "yyy"},
			{TaskId: "222"},
		},
		TaskFilesWild: &TaskFilesWild{
			FileTag:    INCREMENT_BACKUP,
			NameSearch: "20000",
			NameRegex:  "^.+20000\\.\\d+(\\..*)*$",
		},
		SkipLocalExists: true,
		IBSQuery: IBSQueryForRecover{
			SourceIp:  "1.1.1.1",
			BeginDate: "2022-10-30 01:01:01",
			EndDate:   "2022-10-31",
		},
	}
	return IBSRecoverComp{
		Params: ibsReq,
	}
}

// skipFileExists 是否跳过此文件
func (c *IBSRecoverComp) skipFileExists(f string, sizeExpect string) (bool, error) {
	if !c.Params.SkipLocalExists {
		return false, nil
	}
	if sizeExpect == "" {
		return false, nil // 本地不知道 file_size，即使文件存在也无法判断是否完整，所以不跳过
	}
	fileSize := cmutil.GetFileSize(f)
	if fileSize == -1 {
		logger.Info("local file not exists: %s", f)
		return false, nil // file not exists
	} else if fileSize < 0 {
		return false, errors.Errorf("cannot get file_size %s", f)
	}
	// 文件已存在，校验大小
	if strconv.FormatInt(fileSize, 10) != sizeExpect {
		logger.Warn("file %s exists but size %d not match %s. remove it", f, fileSize, sizeExpect)
		if err := os.Remove(f); err != nil {
			return false, err
		}
		// 有一种情况，文件正在下载，如果删除成功这里 sleep 一下，一定概率会让上一个下载任务失败掉，用当前这轮新任务下载
		time.Sleep(1 * time.Second)
		return false, nil
	} else {
		// 本地文件已经存在，且文件大小一致，不重复下载
		logger.Info("file already exists and size match: %s %s. skip it", f, sizeExpect)
		return true, nil
	}
}

// Init TODO
func (c *IBSRecoverComp) Init() error {
	c.Params.maxQueryRetryTimes = 100
	c.Params.maxFailCheckNum = 6
	c.Params.client = &httpclient.HttpClient{
		Client: httpclient.New(),
		Url:    c.Params.IBSInfo.Url,
	}
	if localIPAddrs, err := osutil.GetLocalIPAddrs(); err != nil {
		if c.Params.DestIp == "127.0.0.1" || !util.StringsHas(localIPAddrs, c.Params.DestIp) {
			return errors.Errorf("dest_ip %s should be local", c.Params.DestIp)
		}
	}
	// create dest directory
	p := c.Params.IBSRecoverReq
	_, err := user.Lookup(p.LoginUser)
	if err != nil {
		return errors.Wrap(err, p.LoginUser)
	}
	if !cmutil.FileExists(p.Directory) {
		if err := os.MkdirAll(p.Directory, 0755); err != nil {
			return errors.Wrap(err, p.Directory)
		}
	}
	if errStr, err := osutil.ExecShellCommand(
		false,
		fmt.Sprintf("chown %s %s", p.LoginUser, p.Directory),
	); err != nil {
		logger.Error(errStr)
		return err
	}
	return nil
}

// PreCheck TODO
func (c *IBSRecoverComp) PreCheck() error {
	// 检查目标目录是否存在
	// 检查 user 是否存在
	// 检查哪些文件在目标目录已经存在
	if c.Params.TaskFiles != nil && c.Params.TaskFilesWild != nil {
		return errors.New("either task_files or task_files_wild can be given")
	}
	if c.Params.TaskFilesWild != nil {
		if c.Params.TaskFilesWild.NameSearch == "" {
			return errors.New("task_files_wild.name_search is required")
		}
		if err := c.skipFilesAndInitWild(); err != nil {
			return err
		}
	}
	if c.Params.TaskFiles != nil {
		if err := c.skipFilesAndInit(); err != nil {
			return err
		}
	}
	// 检查空间是否足够 todo
	return nil
}

// Start TODO
func (c *IBSRecoverComp) Start() error {
	return c.Params.downloadFiles()
}

// WaitDone TODO
func (c *IBSRecoverComp) WaitDone() error {
	return nil
}

// PostCheck TODO
func (c *IBSRecoverComp) PostCheck() error {
	// 检查文件大小
	var errList []error
	for _, task := range c.Params.TaskFiles {
		f := filepath.Join(c.Params.Directory, task.FileName)
		if fileSize := cmutil.GetFileSize(f); fileSize == -1 {
			errList = append(errList, errors.Errorf("file %s not exists", f))
		} else if fileSize < 0 {
			errList = append(errList, errors.Errorf("file %s size get failed", f))
		} else if fileSize > 0 {
			if strconv.FormatInt(fileSize, 10) != task.Size {
				errList = append(errList, errors.Errorf("file size not match %s for %s", task.Size, f))
			}
		}
	}
	if len(errList) > 0 {
		logger.Error("IBSRecoverComp.PostCheck %v", errList)
		return util.SliceErrorsToError(errList)
	}
	return nil
}

// OutputCtx TODO
func (c *IBSRecoverComp) OutputCtx() error {
	return components.PrintOutputCtx(c.Params.TaskFiles)
}

func (r *IBSRecoverParam) downloadFiles() error {
	defer func() {
		if r := recover(); r != nil {
			logger.Error("doRow inner panic error,error:%v,stack:%s", r, string(debug.Stack()))
			return
		}
	}()
	// 因为并行读是由备份系统调度的，所以这里直接全部请求下载
	// 如果按 task_id 逐个请求备份系统，就需要客户端控制并发
	if err := r.RecoverAndWaitDone(r.IBSRecoverReq); err != nil {
		return err
	}
	// 确保最终用户权限是mysql
	cmd := fmt.Sprintf("chown -R %s %s", r.IBSRecoverReq.LoginUser, r.IBSRecoverReq.Directory)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Warn("cmd:%s failed, output:%s, err:%s", cmd, output, err.Error())
	}
	return nil
}
