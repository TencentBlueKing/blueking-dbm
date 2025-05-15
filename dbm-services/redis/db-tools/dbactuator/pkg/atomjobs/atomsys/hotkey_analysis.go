package atomsys

import (
	"bufio"
	"container/heap"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

type Ins struct {
	Port     int `json:"port" validate:"required"`
	RecordId int `json:"record_id" validate:"required"`
}

// AnalysisHotkeyParams AnalysisHotkey参数
type AnalysisHotkeyParams struct {
	IP           string `json:"ip" validate:"required"`
	InsList      []Ins  `json:"ins_list"`
	AnalysisTime int    `json:"analysis_time" validate:"required" `
	ClusterId    int64  `json:"cluster_id" validate:"required"`
	TicketId     int64  `json:"ticket_id" validate:"required"`
	BkBizId      int64  `json:"bk_biz_id" validate:"required"`
	ApiServer    string `json:"api_server" validate:"required"`
	BkCloudId    int    `json:"bk_cloud_id"`
	DbCloudToken string `json:"db_cloud_token" validate:"required"`
}

// HotkeyAnalysis  结构体
type HotkeyAnalysis struct {
	runtime     *jobruntime.JobGenericRuntime
	params      *AnalysisHotkeyParams
	saveDir     string
	device      string
	monitorTool string
	errChan     chan error
}

// NewHotkeyAnalysis 创建一个AnalysisHotkey对象
func NewHotkeyAnalysis() jobruntime.JobRunner {
	return &HotkeyAnalysis{}
}

const MaxTimeout = 10 * 60
const ReportUrl = "/apis/proxypass/create_analysis_report/"

// Init 初始化
func (job *HotkeyAnalysis) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisCapturer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisCapturer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	// 6379<= start_port <= 55535
	ins := job.params.InsList
	for _, i := range ins {
		if i.Port > 55535 || i.Port < 6379 {
			err = fmt.Errorf("RedisCapturer port[%d] must range [6379,5535]", i.Port)
			job.runtime.Logger.Error(err.Error())
			return err
		}

	}
	job.errChan = make(chan error, len(ins))
	job.monitorTool = consts.MyRedisCaptureBin
	_, err = os.Stat(job.monitorTool)
	if err != nil && os.IsNotExist(err) {
		return fmt.Errorf("获取myRedisCapture失败,请检查是否下发成功:err:%v", err)
	}

	job.device, err = util.GetIpv4InterfaceName(job.params.IP)
	if err != nil {
		return err
	}

	job.saveDir = filepath.Join(consts.GetRedisBackupDir(), "dbbak/hotkey")
	_, err = os.Stat(job.saveDir)
	if err != nil && os.IsNotExist(err) {
		mkCmd := fmt.Sprintf("mkdir -p %s ", job.saveDir)
		_, err = util.RunLocalCmd("bash", []string{"-c", mkCmd}, "", nil, 100*time.Second)
		if err != nil {
			err = fmt.Errorf("创建目录:%s失败,err:%v", job.saveDir, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		util.LocalDirChownMysql(job.saveDir)
	} else if err != nil {
		err = fmt.Errorf("访问目录:%s 失败,err:%v", job.saveDir, err)
		job.runtime.Logger.Error(err.Error())
		return err

	}
	return nil
}

// ClearFilesNDaysAgo 清理目录下 N天前更新的文件
func (job *HotkeyAnalysis) ClearFilesNDaysAgo(dir string, nDays int) {
	if dir == "" || dir == "/" {
		return
	}
	clearCmd := fmt.Sprintf(`cd %s && find ./ -mtime +%d -exec rm -f {} \;`, dir, nDays)
	job.runtime.Logger.Info("clear %d day cmd:%s", nDays, clearCmd)
	util.RunLocalCmd("bash", []string{"-c", clearCmd}, "", nil, 10*time.Minute)
}

// Run 运行监听请求任务
func (job *HotkeyAnalysis) Run() (err error) {
	ins := job.params.InsList

	// 清理目录下15天以前的文件
	job.ClearFilesNDaysAgo(job.saveDir, 15)

	wg := sync.WaitGroup{}
	for _, i := range ins {
		wg.Add(1)
		go func(port, recordId int) {
			defer wg.Done()
			job.Analysis(port, recordId)
		}(i.Port, i.RecordId)
	}
	wg.Wait()
	close(job.errChan)

	errMsg := ""
	for err := range job.errChan {
		errMsg = fmt.Sprintf("%s\n%s", errMsg, err.Error())
	}

	return nil
}

type HotkeyInsert struct {
	TicketId  int64  `json:"ticket_id"`
	RecordId  int    `json:"record_id"`
	BkBizId   int64  `json:"bk_biz_id"`
	ClusterId int64  `json:"cluster_id"`
	Ins       string `json:"ins"`
	Key       string `json:"key"`
	CmdInfo   string `json:"cmd_info"`
	ExecCount int64  `json:"exec_count"`
	Ratio     string `json:"ratio"`
}

type HotkeyParams struct {
	HotKeyInfos []HotkeyInsert `json:"hot_key_infos"`
}

// Analysis 监听请求
func (job *HotkeyAnalysis) Analysis(port, recordId int) {
	job.runtime.Logger.Info("Analysis port[%d] begin..", port)
	defer job.runtime.Logger.Info("Analysis port[%d] end..", port)
	var err error
	running, err := job.IsRedisRunning(port)
	if err != nil || !running {
		err = fmt.Errorf("port:%d not running", port)
		job.errChan <- err
		return
	}

	nowstr := time.Now().Local().Format("150405")
	capturelog := fmt.Sprintf("%s/capture_%s_%d_%s.log", job.saveDir, job.params.IP, port, nowstr)
	timeout := MaxTimeout

	// 抓AnalysisTime时长的包
	fileCount := job.params.AnalysisTime/MaxTimeout + 1
	for seq := 1; seq <= fileCount; seq++ {
		if seq == fileCount {
			timeout = job.params.AnalysisTime % MaxTimeout
		}
		outputlog := fmt.Sprintf("%s/capture_result_%s_%d_%s_%d.txt",
			job.saveDir, job.params.IP, port, nowstr, seq)
		monitorCmd := fmt.Sprintf("%s --device=%s --ip=%s --port=%d --timeout=%d --log-file=%s --output-file=%s",
			job.monitorTool, job.device, job.params.IP, port, timeout, capturelog, outputlog)
		job.runtime.Logger.Info("will to exec monitor cmd is [%s]", monitorCmd)
		_, err = util.RunLocalCmd("bash", []string{"-c", monitorCmd}, "", nil, 10*time.Minute)
		if err != nil {
			if err.Error() == "RunLocalCmd cmd wait fail,err:exit status 1" {
				continue
			}
			err = fmt.Errorf("monitor cmd[%s] exec error:%s", monitorCmd, err.Error())
			job.errChan <- err
			return
		}
	}

	// 开始统计key命令执行情况
	hotkeyMap := make(map[string]*HotKey)
	allTotalCount := int64(0)
	for seq := 1; seq <= fileCount; seq++ {
		outputlog := fmt.Sprintf("%s/capture_result_%s_%d_%s_%d.txt",
			job.saveDir, job.params.IP, port, nowstr, seq)
		file, err := os.Open(outputlog)
		if err != nil {
			job.errChan <- err
			return
		}
		defer file.Close()

		// 创建一个 Scanner 对象
		scanner := bufio.NewScanner(file)

		// 按行读取文件内容
		for scanner.Scan() {
			line := scanner.Text() // 获取当前行的内容

			splitList := strings.Split(line, " ")
			if len(splitList) < 13 {
				job.runtime.Logger.Warn("%s is Illegal")
				continue
			}
			// key 大小写区分。 cmd 大小写不区分
			key := strings.Trim(splitList[12], "\"")
			cmd := strings.ToLower(strings.Trim(splitList[11], "\""))
			if cmd == "auth" {
				key = "******"
			}

			//统计
			allTotalCount++
			_, _ok := hotkeyMap[key]
			if !_ok {
				hotkeyMap[key] = &HotKey{
					Key:        key,
					TotalCount: 1,
					Ratio:      0,
				}
				hotkeyMap[key].CmdCount = make(map[string]int64)
				hotkeyMap[key].CmdCount[cmd]++
			} else {
				hotkeyMap[key].TotalCount++
				hotkeyMap[key].CmdCount[cmd]++
			}
		}

		// 检查是否在读取过程中发生错误
		if err := scanner.Err(); err != nil {
			job.errChan <- err
			return
		}
	}

	// 处理结果，只取前20条记录插入表中
	// 初始化一个大小为 20 的最小堆
	h := &MinHeap{}
	heap.Init(h)

	// 遍历 map
	for _, hotKey := range hotkeyMap {
		if h.Len() < 20 {
			heap.Push(h, hotKey) // 如果堆大小小于 20，直接加入
		} else if hotKey.TotalCount > (*h)[0].TotalCount {
			heap.Pop(h)          // 如果当前元素的 TotalCount 大于堆顶，弹出堆顶
			heap.Push(h, hotKey) // 将当前元素加入堆
		}
	}

	cli, err := util.NewClient(job.params.ApiServer, job.params.DbCloudToken, job.params.BkCloudId)
	if err != nil {
		return
	}

	// 将堆中的元素提取出来
	var hotkeyList []HotkeyInsert
	for h.Len() != 0 {
		hotKeyT := heap.Pop(h).(*HotKey)
		hotKeyT.Ratio = float32(hotKeyT.TotalCount) / float32(allTotalCount)
		var sb strings.Builder
		for key, value := range hotKeyT.CmdCount {
			sb.WriteString(fmt.Sprintf("%s:%d ", key, value))
		}
		// 去掉最后一个逗号
		cmdStr := sb.String()

		// 调用api插入分析记录
		hotkey := HotkeyInsert{
			TicketId:  job.params.TicketId,
			RecordId:  recordId,
			BkBizId:   job.params.BkBizId,
			ClusterId: job.params.ClusterId,
			Ins:       fmt.Sprintf("%s:%d", job.params.IP, port),
			Key:       hotKeyT.Key,
			CmdInfo:   cmdStr,
			ExecCount: hotKeyT.TotalCount,
			Ratio:     fmt.Sprintf("%.2f", hotKeyT.Ratio*100),
		}
		hotkeyList = append(hotkeyList, hotkey)
		job.runtime.Logger.Info(fmt.Sprintf("hotKey: %+v", hotKeyT))
	}
	ret, err := cli.Do(http.MethodPost, ReportUrl, HotkeyParams{HotKeyInfos: hotkeyList})
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		job.errChan <- err
		return
	}
	job.runtime.Logger.Info(fmt.Sprintf("ret:{code:%d,message:%s}", ret.Code, ret.Message))

	job.runtime.Logger.Info(fmt.Sprintf("insert %d hot key success", port))
}

// IsRedisRunning 检查实例是否在运行。
func (job *HotkeyAnalysis) IsRedisRunning(port int) (installed bool, err error) {
	time.Sleep(10 * time.Second)
	portIsUse, err := util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
	return portIsUse, err
}

// Name 原子任务名
func (job *HotkeyAnalysis) Name() string {
	return "hotkey_analysis"
}

// Retry times
func (job *HotkeyAnalysis) Retry() uint {
	return 2
}

// Rollback rollback
func (job *HotkeyAnalysis) Rollback() error {
	return nil
}

type HotKey struct {
	Key        string
	TotalCount int64
	// 存储cmd执行次数
	CmdCount map[string]int64
	Ratio    float32
}

// MinHeap 定义一个最小堆结构排序
type MinHeap []*HotKey

func (h MinHeap) Len() int           { return len(h) }
func (h MinHeap) Less(i, j int) bool { return h[i].TotalCount < h[j].TotalCount }
func (h MinHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *MinHeap) Push(x interface{}) {
	*h = append(*h, x.(*HotKey))
}

func (h *MinHeap) Pop() interface{} {
	old := *h
	n := len(old)
	x := old[n-1]
	*h = old[0 : n-1]
	return x
}
