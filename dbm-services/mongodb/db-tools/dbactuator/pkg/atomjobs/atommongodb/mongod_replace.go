package atommongodb

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// MongoDReplaceConfParams 参数  // 替换mongod
type MongoDReplaceConfParams struct {
	IP             string `json:"ip" validate:"required"` // 执行节点
	Port           int    `json:"port" validate:"required"`
	SourceIP       string `json:"sourceIP"`   // 源节点，新加节点时可以为null
	SourcePort     int    `json:"sourcePort"` // 源端口，新加节点时可以为null
	SourceDown     bool   `json:"sourceDown"` // 源端已down机 true：已down false：未down
	AdminUsername  string `json:"adminUsername" validate:"required"`
	AdminPassword  string `json:"adminPassword" validate:"required"`
	TargetIP       string `json:"targetIP"`       // 目标节点，移除节点时可以为null
	TargetPort     int    `json:"targetPort"`     // 目标端口，移除节点时可以为null
	TargetPriority string `json:"targetPriority"` // 可选，默认为null，如果为null，则使用source端的Priority，取值：0-正无穷
	TargetHidden   string `json:"targetHidden"`   // 可选，默认为null，如果为null，则使用source端的Hidden，取值：null，0，1，0：显现 1：隐藏
}

// MongoDReplace 添加分片到集群
type MongoDReplace struct {
	BaseJob
	runtime         *jobruntime.JobGenericRuntime
	BinDir          string
	Mongo           string
	OsUser          string
	DataDir         string
	DbpathDir       string
	PrimaryIP       string
	PrimaryPort     int
	AddTargetScript string
	ConfParams      *MongoDReplaceConfParams
	TargetIPStatus  int
	TargetPriority  int
	TargetHidden    bool
	StatusCh        chan int
}

// NewMongoDReplace 实例化结构体
func NewMongoDReplace() jobruntime.JobRunner {
	return &MongoDReplace{}
}

// Name 获取原子任务的名字
func (r *MongoDReplace) Name() string {
	return "mongod_replace"
}

// Run 运行原子任务
func (r *MongoDReplace) Run() error {
	// 主节点进行切换
	if err := r.primaryStepDown(); err != nil {
		return err
	}

	// 生成添加新节点脚本
	if err := r.makeAddTargetScript(); err != nil {
		return err
	}

	// 执行添加新节点脚本
	if err := r.execAddTargetScript(); err != nil {
		return err
	}

	// 查看新节点状态
	go r.checkTargetStatus()

	// 执行删除老节点脚本
	if err := r.checkTargetStatusAndRemoveSource(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (r *MongoDReplace) Retry() uint {
	return 2
}

// Rollback 回滚
func (r *MongoDReplace) Rollback() error {
	return nil
}

// Init 初始化
func (r *MongoDReplace) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	r.runtime = runtime
	r.runtime.Logger.Info("start to init")
	r.BinDir = consts.UsrLocal
	r.Mongo = filepath.Join(r.BinDir, "mongodb", "bin", "mongo")
	r.OsUser = consts.GetProcessUser()
	r.DataDir = consts.GetMongoDataDir()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.ConfParams); err != nil {
		r.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of mongodReplace fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of mongodReplace fail by json.Unmarshal, error:%s", err)
	}

	r.DbpathDir = filepath.Join(r.DataDir, "mongodata", strconv.Itoa(r.ConfParams.Port), "db")

	// 获取primary信息
	info, err := common.AuthGetPrimaryInfo(r.Mongo, r.ConfParams.AdminUsername, r.ConfParams.AdminPassword,
		r.ConfParams.IP, r.ConfParams.Port)
	if err != nil {
		r.runtime.Logger.Error(fmt.Sprintf(
			"get primary db info of mongodReplace fail, error:%s", err))
		return fmt.Errorf("get primary db info of mongodReplace fail, error:%s", err)
	}
	// 判断info是否为null
	if info == "" {
		r.runtime.Logger.Error(fmt.Sprintf(
			"get primary db info of mongodReplace fail, error:%s", err))
		return fmt.Errorf("get primary db info of mongodReplace fail, error:%s", err)
	}
	getInfo := strings.Split(info, ":")
	r.PrimaryIP = getInfo[0]
	r.PrimaryPort, _ = strconv.Atoi(getInfo[1])
	r.StatusCh = make(chan int, 1)

	// 获取源端的配置信息
	_, _, _, hidden, priority, _, err := common.GetNodeInfo(r.Mongo, r.PrimaryIP, r.PrimaryPort,
		r.ConfParams.AdminUsername, r.ConfParams.AdminPassword, r.ConfParams.SourceIP, r.ConfParams.SourcePort)
	if err != nil {
		return err
	}
	r.TargetHidden = hidden
	if r.ConfParams.TargetHidden == "0" {
		r.TargetHidden = false
	} else if r.ConfParams.TargetHidden == "1" {
		r.TargetHidden = true
	}

	r.TargetPriority = priority
	if r.ConfParams.TargetPriority != "" {
		r.TargetPriority, _ = strconv.Atoi(r.ConfParams.TargetPriority)
	}

	r.runtime.Logger.Info("init successfully")

	// 进行校验
	if err = r.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (r *MongoDReplace) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	r.runtime.Logger.Info("start to validate parameters of mongodReplace")
	if err := validate.Struct(r.ConfParams); err != nil {
		r.runtime.Logger.Error("validate parameters of mongodReplace fail, error:%s", err)
		return fmt.Errorf("validate parameters of mongodReplace fail, error:%s", err)
	}
	r.runtime.Logger.Info("validate parameters of mongodReplace successfully")
	return nil
}

// makeAddTargetScript 创建添加脚本
func (r *MongoDReplace) makeAddTargetScript() error {
	if r.ConfParams.TargetIP == "" {
		return nil
	}
	// 生成脚本内容
	r.runtime.Logger.Info("start to make addTarget script content")
	addMember := common.NewReplicasetMemberAdd()
	addMember.Host = strings.Join([]string{r.ConfParams.TargetIP, strconv.Itoa(r.ConfParams.TargetPort)}, ":")
	addMember.Priority = r.TargetPriority
	addMember.Hidden = r.TargetHidden
	addMemberJson, err := addMember.GetJson()
	if err != nil {
		r.runtime.Logger.Error("get addMemberJson info fail, error:%s", err)
		return fmt.Errorf("get addMemberJson info fail, error:%s", err)
	}
	addMemberJson = strings.Replace(addMemberJson, "\"", "\\\"", -1)
	addTargetConfScript := strings.Join([]string{"rs.add(", addMemberJson, ")"}, "")
	r.AddTargetScript = addTargetConfScript
	r.runtime.Logger.Info("make addTarget script content successfully")
	return nil
}

// execAddTargetScript 执行添加脚本
func (r *MongoDReplace) execAddTargetScript() error {
	if r.ConfParams.TargetIP == "" {
		return nil
	}
	// 检查target是否已经存在
	flag, _, _, _, _, _, _ := common.GetNodeInfo(r.Mongo, r.PrimaryIP, r.PrimaryPort,
		r.ConfParams.AdminUsername, r.ConfParams.AdminPassword, r.ConfParams.TargetIP, r.ConfParams.TargetPort)
	if flag == true {
		r.runtime.Logger.Info("target:%s has been existed", strings.Join(
			[]string{r.ConfParams.TargetIP, strconv.Itoa(r.ConfParams.TargetPort)}, ":"))
		return nil
	}

	r.runtime.Logger.Info("start to execute addTarget script")
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\"",
		r.Mongo, r.ConfParams.AdminUsername, r.ConfParams.AdminPassword, r.PrimaryIP,
		r.PrimaryPort, r.AddTargetScript)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		r.runtime.Logger.Error("execute addTarget script fail, error:%s", err)
		return fmt.Errorf("execute addTarget script fail, error:%s", err)
	}
	r.runtime.Logger.Info("execute addTarget script successfully")
	return nil
}

// checkTargetStatus 检查target状态
func (r *MongoDReplace) checkTargetStatus() {
	if r.ConfParams.TargetIP == "" {
		return
	}
	r.runtime.Logger.Info("start to check Target status")
	for {
		_, _, status, _, _, _, err := common.GetNodeInfo(r.Mongo, r.PrimaryIP, r.PrimaryPort,
			r.ConfParams.AdminUsername,
			r.ConfParams.AdminPassword, r.ConfParams.TargetIP, r.ConfParams.TargetPort)
		if err != nil {
			r.runtime.Logger.Error("get target status fail, error:%s", err)
		}
		if status != 0 {
			r.StatusCh <- status
			if status == 2 {
				r.runtime.Logger.Info("target status is %d", status)
				return
			}
		}
		time.Sleep(5 * time.Second)
	}
}

// primaryStepDown 主库切换
func (r *MongoDReplace) primaryStepDown() error {
	if r.ConfParams.SourceIP == r.PrimaryIP && r.ConfParams.SourcePort == r.PrimaryPort {
		r.runtime.Logger.Info("start to convert primary secondary db")
		flag, err := common.AuthRsStepDown(r.Mongo, r.PrimaryIP, r.PrimaryPort, r.ConfParams.AdminUsername,
			r.ConfParams.AdminPassword)
		if err != nil {
			r.runtime.Logger.Error(fmt.Sprintf("convert primary secondary db fail, error:%s", err))
			return fmt.Errorf("convert primary secondary db fail, error:%s", err)
		}
		if flag == true {
			info, err := common.AuthGetPrimaryInfo(r.Mongo, r.ConfParams.AdminUsername, r.ConfParams.AdminPassword,
				r.ConfParams.IP, r.ConfParams.Port)
			if err != nil {
				r.runtime.Logger.Error(fmt.Sprintf("get new primary info fail, error:%s", err))
				return fmt.Errorf("get new primary info fail, error:%s", err)
			}
			if info != fmt.Sprintf("%s:%d", r.ConfParams.IP, r.ConfParams.Port) {
				r.runtime.Logger.Info("convert primary secondary db successfully")
				infoSlice := strings.Split(info, ":")
				r.PrimaryIP = infoSlice[0]
				r.PrimaryPort, _ = strconv.Atoi(infoSlice[1])
				return nil
			}
		}
	}
	return nil
}

// shutdownSourceProcess 关闭源端mongod进程
func (r *MongoDReplace) shutdownSourceProcess() error {
	flag, _, _ := common.CheckMongoService(r.ConfParams.Port)
	if flag == false {
		r.runtime.Logger.Info("source mongod process has been shut")
		return nil
	}
	r.runtime.Logger.Info("start to shutdown source mongod process")
	if err := common.ShutdownMongoProcess(r.OsUser, "mongod", r.BinDir, r.DbpathDir, r.ConfParams.Port); err != nil {
		source := fmt.Sprintf("%s:%d", r.ConfParams.IP, r.ConfParams.Port)
		r.runtime.Logger.Error(fmt.Sprintf("shutdown source:%s fail, error:%s", source, err))
		return fmt.Errorf("shutdown source:%s fail, error:%s", source, err)
	}
	r.runtime.Logger.Info("shutdown source mongod process successfully")
	return nil
}

// removeSource 复制集中移除source
func (r *MongoDReplace) removeSource() error {
	if r.ConfParams.SourceIP == "" {
		return nil
	}
	// 检查source是否存在
	flag, _, _, _, _, _, _ := common.GetNodeInfo(r.Mongo, r.PrimaryIP, r.PrimaryPort,
		r.ConfParams.AdminUsername, r.ConfParams.AdminPassword, r.ConfParams.SourceIP, r.ConfParams.SourcePort)
	if flag == false {
		r.runtime.Logger.Info("source:%s has been remove", strings.Join(
			[]string{r.ConfParams.SourceIP, strconv.Itoa(r.ConfParams.SourcePort)}, ":"))
		return nil
	}
	r.runtime.Logger.Info("start to make remove source script content")
	removeSourceConfScript := strings.Join([]string{
		"rs.remove(",
		fmt.Sprintf("\\\"%s:%d\\\"", r.ConfParams.SourceIP, r.ConfParams.SourcePort),
		")"}, "")
	r.runtime.Logger.Info("make remove source script content successfully")
	r.runtime.Logger.Info("start to execute remove source script")
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\"",
		r.Mongo, r.ConfParams.AdminUsername, r.ConfParams.AdminPassword, r.PrimaryIP,
		r.PrimaryPort, removeSourceConfScript)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		r.runtime.Logger.Error(fmt.Sprintf("execute remove source script fail, error:%s", err))
		return fmt.Errorf("execute remove source script fail, error:%s", err)
	}
	r.runtime.Logger.Info("execute remove source script successfully")
	return nil
}

// checkTargetStatusAndRemoveSource 监控状态并移除
func (r *MongoDReplace) checkTargetStatusAndRemoveSource() error {
	// 下架老节点
	if r.ConfParams.TargetIP == "" && r.ConfParams.SourceDown == false {
		if err := r.shutdownSourceProcess(); err != nil {
			return err
		}
		if err := r.removeSource(); err != nil {
			return err
		}
		return nil
	} else if r.ConfParams.TargetIP == "" && r.ConfParams.SourceDown == true {
		if err := r.removeSource(); err != nil {
			return err
		}
		return nil
	}
	// 先添加新节点再移除老节点，或者添加新节点
	for {
		select {
		// 超时时间
		case <-time.After(50 * time.Second):
			return fmt.Errorf("check target status timeout")
		case status := <-r.StatusCh:
			if status == 2 && r.ConfParams.SourceDown == false {
				if err := r.shutdownSourceProcess(); err != nil {
					return err
				}
				if err := r.removeSource(); err != nil {
					return err
				}
				return nil
			} else if status == 2 && r.ConfParams.SourceDown == true {
				if err := r.removeSource(); err != nil {
					return err
				}
				return nil
			} else if status == 2 && r.ConfParams.SourceIP == "" {
				return nil
			}
		}
	}
}
