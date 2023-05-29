package atomredis

import (
	"bufio"
	"bytes"
	"context"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/go-playground/validator/v10"
)

// TendisKeysFilesDeleteParams 按文件删除job参数
type TendisKeysFilesDeleteParams struct {
	common.DbToolsMediaPkg
	FileServer           util.FileServerInfo `json:"fileserver" validate:"required"`
	BkBizID              string              `json:"bk_biz_id" validate:"required"`
	Domain               string              `json:"domain" validate:"required"`
	ProxyPort            int                 `json:"proxy_port" validate:"required"`
	ProxyPassword        string              `json:"proxy_password" validate:"required"`
	Path                 string              `json:"path" validate:"required"`
	TendisType           string              `json:"tendis_type" validate:"required"`
	DeleteRate           int                 `json:"delete_rate" validate:"required"`            // cache Redis删除速率,避免del 命令执行过快
	TendisplusDeleteRate int                 `json:"tendisplus_delete_rate" validate:"required"` // tendisplus删除速率,避免del 命令执行过快
}

// TendisKeysFilesDelete 按文件形式的提取结果删除key:
type TendisKeysFilesDelete struct {
	deleteDir   string
	Err         error  `json:"_"`
	SafeDelTool string `json:"safeDelTool"` // 执行安全删除的工具
	params      TendisKeysFilesDeleteParams
	runtime     *jobruntime.JobGenericRuntime
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*TendisKeysFilesDelete)(nil)

// NewTendisKeysFilesDelete  new
func NewTendisKeysFilesDelete() jobruntime.JobRunner {
	return &TendisKeysFilesDelete{}
}

// Init 初始化
func (job *TendisKeysFilesDelete) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("TendisKeysFilesDelete Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("TendisKeysFilesDelete Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}

	return nil

}

// Name 原子任务名
func (job *TendisKeysFilesDelete) Name() string {
	return "tendis_keysdelete_files"
}

// Run 执行
func (job *TendisKeysFilesDelete) Run() error {
	deleteDir := filepath.Join(consts.GetRedisBackupDir(), "dbbak/delete_keys_dir")
	job.deleteDir = deleteDir
	// 解压key工具包介质
	job.UntarMedia()
	if job.Err != nil {
		return job.Err
	}
	// 清理目录下15天以前的文件
	job.ClearFilesNDaysAgo(job.deleteDir, 15)

	// time.Sleep(10 * time.Second)

	job.DownloadFileFromoBkrepo()
	if job.Err != nil {
		return job.Err
	}

	folderName := filepath.Base(job.params.Path)
	filespath := filepath.Join(job.deleteDir, folderName)
	files, err := ioutil.ReadDir(filespath)
	if err != nil {
		log.Fatal(err)
	}

	chanFileDelTask := make(chan fs.FileInfo)
	DelWorkLimit := job.SetDelWorkLimit(files)
	job.runtime.Logger.Info("DelWorkLimit is %d", DelWorkLimit)
	// 生产者
	go job.keysFileDelTaskQueue(chanFileDelTask, files)
	wg := sync.WaitGroup{}
	wg.Add(DelWorkLimit)
	for worker := 0; worker < DelWorkLimit; worker++ {
		// 消费者
		go job.keysFileDelTask(chanFileDelTask, &wg)
	}
	// 等待所有线程退出
	wg.Wait()

	if job.Err != nil {
		return job.Err
	}
	return nil
}

// Retry times
func (job *TendisKeysFilesDelete) Retry() uint {
	return 2
}

// Rollback rollback
func (job *TendisKeysFilesDelete) Rollback() error {
	return nil

}

// keysFileDelTaskQueue 删除keys文件任务队列
func (job *TendisKeysFilesDelete) keysFileDelTaskQueue(chanFileDelTask chan fs.FileInfo, files []fs.FileInfo) {
	for _, file := range files {
		fileTask := file
		chanFileDelTask <- fileTask
	}
	close(chanFileDelTask)
	job.runtime.Logger.Info("....add keysFileDelTask to Queue finish...")
	return

}

// keysFileDelTask delete job
func (job *TendisKeysFilesDelete) keysFileDelTask(chanFileDelTask chan fs.FileInfo, wg *sync.WaitGroup) (err error) {
	defer wg.Done()
	for fileDelTask := range chanFileDelTask {
		job.runtime.Logger.Info("....file keys Delete job...")
		folderName := filepath.Base(job.params.Path)
		filepath := filepath.Join(job.deleteDir, folderName, fileDelTask.Name())
		job.DelKeysRateLimitFromFiles(filepath)
		if job.Err != nil {
			return job.Err
		}
	}
	job.runtime.Logger.Info("....keysFileDelTask  goroutine finish...")
	return nil

}

// CheckDeleteDir key分析本地数据目录
func (job *TendisKeysFilesDelete) CheckDeleteDir() (err error) {
	_, err = os.Stat(job.deleteDir)
	if err != nil && os.IsNotExist(err) {
		mkCmd := fmt.Sprintf("mkdir -p %s ", job.deleteDir)
		_, err = util.RunLocalCmd("bash", []string{"-c", mkCmd}, "", nil, 100*time.Second)
		if err != nil {
			err = fmt.Errorf("创建目录:%s失败,err:%v", job.deleteDir, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		util.LocalDirChownMysql(job.deleteDir)
	} else if err != nil {
		err = fmt.Errorf("访问目录:%s 失败,err:%v", job.deleteDir, err)
		job.runtime.Logger.Error(err.Error())
		return err

	}
	return nil
}

// UntarMedia 解压key工具包介质
func (job *TendisKeysFilesDelete) UntarMedia() {
	err := job.params.Check()
	if err != nil {
		job.runtime.Logger.Error("UntarMedis failed err:%v", err)
		job.Err = err
		return
	}
	err = job.CheckDeleteDir()
	if err != nil {
		job.runtime.Logger.Error("检查key保存目录失败: err:%v", err)
		job.Err = err
		return
	}

	// Install: 确保dbtools符合预期
	err = job.params.DbToolsMediaPkg.Install()
	if err != nil {
		job.runtime.Logger.Error("DbToolsPkg dbtools不符合预期: err:%v,请检查", err)
		job.Err = err
		return
	}

	cpCmd := fmt.Sprintf("cp  %s/* %s", consts.DbToolsPath, job.deleteDir)
	_, err = util.RunBashCmd(cpCmd, "", nil, 10*time.Second)
	if err != nil {
		job.Err = err
		return
	}
	job.runtime.Logger.Info(cpCmd)

	return

}

// SetDelWorkLimit 设置并发度
func (job *TendisKeysFilesDelete) SetDelWorkLimit(files []fs.FileInfo) (delWorkLimit int) {
	// 根据节点数确认并发度
	delWorkLimit = 0
	fileNumber := len(files)
	if fileNumber <= 8 {
		delWorkLimit = 1
	} else if fileNumber <= 16 {
		delWorkLimit = 2
	} else if fileNumber <= 32 {
		delWorkLimit = 3
	} else if fileNumber <= 64 {
		delWorkLimit = 4
	} else if fileNumber <= 128 {
		delWorkLimit = 5
	} else {
		delWorkLimit = 6
	}
	msg := fmt.Sprintf("goroutine delWorkLimit is: %d", delWorkLimit)
	job.runtime.Logger.Info(msg)
	return delWorkLimit
}

// ClearFilesNDaysAgo 清理目录下 N天前更新的文件
func (job *TendisKeysFilesDelete) ClearFilesNDaysAgo(dir string, nDays int) {
	if dir == "" || dir == "/" || dir == "/data/" || dir == "/data1/" {
		return
	}
	if strings.Contains(dir, "dbbak") {
		clearCmd := fmt.Sprintf(`cd %s && find ./ -mtime +%d  -exec rm -rf {} \;`, dir, nDays)
		job.runtime.Logger.Info("clear %d day cmd:%s", nDays, clearCmd)
		util.RunLocalCmd("bash", []string{"-c", clearCmd}, "", nil, 10*time.Minute)
	}

}

// DownloadFileFromoBkrepo 从蓝盾制品库下载keys文件
func (job *TendisKeysFilesDelete) DownloadFileFromoBkrepo() {

	folderName := filepath.Base(job.params.Path)
	downloadFileArchive := fmt.Sprintf(job.deleteDir + "/" + folderName + ".zip")
	folderDir := filepath.Join(job.deleteDir, folderName)
	_, err := os.Stat(folderDir)
	if err == nil {
		job.runtime.Logger.Info("文件夹已存在,不用重复下载解压")
		return
	}
	ArchiveInfo, err := os.Stat(downloadFileArchive)
	if err == nil && ArchiveInfo.Size() > 0 {
		job.runtime.Logger.Info("文件压缩包已存在且文件大小为:%d,不用重复下载", ArchiveInfo.Size())
		unzipCmd := fmt.Sprintf("unzip -o %s -d %s/%s", downloadFileArchive, job.deleteDir, folderName)
		job.runtime.Logger.Info("unzip files cmd: %s", unzipCmd)
		_, err = util.RunLocalCmd("bash", []string{"-c", unzipCmd}, "", nil, 10*time.Minute)
		if err != nil {
			job.Err = err
			return
		}
	} else {
		targetURL := fmt.Sprintf(job.params.FileServer.URL + "/generic/" + job.params.FileServer.Project + "/" +
			job.params.FileServer.Bucket + job.params.Path + "?download=true")
		err = util.DownloadFile(downloadFileArchive, targetURL, job.params.FileServer.Username,
			job.params.FileServer.Password)
		if err != nil {
			err = fmt.Errorf("下载文件 %s 到 %s 失败:%v", targetURL, downloadFileArchive, err)
			job.runtime.Logger.Error(err.Error())
			job.Err = err
			return
		}

		unzipCmd := fmt.Sprintf("unzip -o %s -d %s/%s", downloadFileArchive, job.deleteDir, folderName)
		job.runtime.Logger.Info("unzip files cmd: %s", unzipCmd)
		_, err = util.RunLocalCmd("bash", []string{"-c", unzipCmd}, "", nil, 10*time.Minute)
		if err != nil {
			job.Err = err
			return
		}
	}

}

// GetRedisSafeDelTool 获取安全删除key的工具
func (job *TendisKeysFilesDelete) GetRedisSafeDelTool() (bool, error) {

	remoteSafeDelTool := "redisSafeDeleteTool"
	job.SafeDelTool = filepath.Join(job.deleteDir, remoteSafeDelTool)
	_, err := os.Stat(job.SafeDelTool)
	if err != nil && os.IsNotExist(err) {
		job.Err = fmt.Errorf("获取redisSafeDeleteTool失败,请检查是否下发成功:err:%v", err)
		job.runtime.Logger.Error(job.Err.Error())
		return false, job.Err
	}
	util.LocalDirChownMysql(job.SafeDelTool)
	err = os.Chmod(job.SafeDelTool, 0755)
	if err != nil {
		job.Err = fmt.Errorf(" redisSafeDeleteTool 加可执行权限失败:err:%v", err)
		return false, job.Err
	}
	return true, nil
}

// DelKeysRateLimitFromFiles 对redis key执行安全删除
func (job *TendisKeysFilesDelete) DelKeysRateLimitFromFiles(resultFile string) {

	msg := fmt.Sprintf("redis:%s#%d start delete keys ...", job.params.Domain, job.params.ProxyPort)
	job.runtime.Logger.Info(msg)

	job.GetRedisSafeDelTool()
	if job.Err != nil {
		return
	}

	fileData, err := os.Stat(resultFile)
	if err != nil {
		job.Err = fmt.Errorf("redis:%s#%d keys resultFile:%s os.stat fail,err:%v", job.params.Domain, job.params.ProxyPort,
			resultFile, err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	if fileData.Size() == 0 {
		msg = fmt.Sprintf("redis:%s#%d keys resultFile:%s size==%d,skip delKeys", job.params.Domain, job.params.ProxyPort,
			resultFile, fileData.Size())
		job.runtime.Logger.Info(msg)
		return
	}

	keyFile, err := os.Open(resultFile)
	if err != nil {
		job.Err = fmt.Errorf("DelKeysRateLimit open %s fail,err:%v", resultFile, err)
		job.runtime.Logger.Error(job.Err.Error())
		return
	}
	defer keyFile.Close()

	// tendisplus 与 cache 删除默认速率不同
	delRateLimit := 10000
	if consts.IsTendisplusInstanceDbType(job.params.TendisType) {
		if job.params.TendisplusDeleteRate >= 10 {
			delRateLimit = job.params.TendisplusDeleteRate
		} else {
			delRateLimit = 3000
		}
	} else if job.params.DeleteRate >= 10 {
		delRateLimit = job.params.DeleteRate
	} else {
		delRateLimit = 10000
	}

	var errBuffer bytes.Buffer
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	bigKeyThread := 1000 // 如果hash,hlen>1000,则算big key
	threadCnt := 30
	subScanCount := 100 // hscan 中count 个数

	addr := fmt.Sprintf("%s:%d", job.params.Domain, job.params.ProxyPort)
	delCmd := fmt.Sprintf(
		`%s bykeysfile --dbtype=standalone --redis-addr=%s --redis-password=%s --keys-file=%s --big-key-threashold=%d --del-rate-limit=%d --thread-cnt=%d --sub-scan-count=%d --without-config-cmd`,
		job.SafeDelTool, addr, job.params.ProxyPassword, resultFile, bigKeyThread, delRateLimit, threadCnt, subScanCount)
	logCmd := fmt.Sprintf(
		`%s bykeysfile --dbtype=standalone --redis-addr=%s --redis-password=xxxxx --keys-file=%s --big-key-threashold=%d --del-rate-limit=%d --thread-cnt=%d --sub-scan-count=%d --without-config-cmd`,
		job.SafeDelTool, addr, resultFile, bigKeyThread, delRateLimit, threadCnt, subScanCount)
	job.runtime.Logger.Info(logCmd)

	cmd := exec.CommandContext(ctx, "bash", "-c", delCmd)
	stdout, _ := cmd.StdoutPipe()
	cmd.Stderr = &errBuffer

	if err = cmd.Start(); err != nil {
		err = fmt.Errorf("DelKeysRateLimitV2 cmd.Start fail,err:%v", err)
		job.runtime.Logger.Error(err.Error())
		job.Err = err
		return
	}

	scanner := bufio.NewScanner(stdout)
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		// 不断打印进度
		m := scanner.Text()
		if strings.Contains(m, `"level":"error"`) == true {
			err = errors.New(m)
			job.runtime.Logger.Info(m)
			continue
		}
		m = m + ";" + addr
		job.runtime.Logger.Info(m)
	}
	if err != nil {
		job.Err = err
		return
	}

	if err = cmd.Wait(); err != nil {
		err = fmt.Errorf("DelKeysRateLimitV2 cmd.Wait fail,err:%v", err)
		job.runtime.Logger.Error(err.Error())
		job.Err = err
		return
	}
	errStr := errBuffer.String()
	errStr = strings.TrimSpace(errStr)
	if len(errStr) > 0 {
		err = fmt.Errorf("DelKeysRateLimitV2 fail,err:%s", errStr)
		job.runtime.Logger.Error(err.Error())
		job.Err = err
		return
	}

}
