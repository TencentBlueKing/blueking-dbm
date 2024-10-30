package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/mongo"
)

// instance_op 对单个mongod/mongos进程作一些起停操作

// instOpParams 原子任务参数
type instOpParams struct {
	IP               string `json:"ip"`
	Port             int    `json:"port"`
	AdminUsername    string `json:"adminUsername"`
	AdminPassword    string `json:"adminPassword"`
	Op               string `json:"op"` // start, stop, check_empty_data, start_standalone
	SetName          string `json:"set_name,omitempty"`
	GrantRolesToUser struct {
		Username string   `json:"username,omitempty"`
		Roles    []string `json:"roles,omitempty"`
	} `json:"grantRolesToUser,omitempty"`
}

type instOpJob struct {
	BaseJob
	ConfParams  *instOpParams
	MongoInst   *mymongo.MongoHost
	MongoClient *mongo.Client
}

func (s *instOpJob) Param() string {
	o, _ := json.MarshalIndent(instOpParams{}, "", "\t")
	return string(o)
}

// NewInstOpJob 实例化结构体
func NewInstOpJob() jobruntime.JobRunner {
	return &instOpJob{}
}

// Name 获取原子任务的名字
func (s *instOpJob) Name() string {
	return "mongodb_instance_op"
}

// Run 运行原子任务
func (s *instOpJob) Run() error {
	var op = s.GetInstanceOp()
	s.runtime.Logger.Info("do op " + s.ConfParams.Op)
	switch s.ConfParams.Op {
	case "rs_remove_other_node":
		// remove me from the replica set
		return s.doRemoveOtherMember()
	case "rs_join":
		// add me to the replica set
		return s.doAddMember()
	case "rs_init":
		// exec rs.initiate()
		return s.doInit()
	case "grantRolesToUser":
		// grant roles to user
		return op.GrantRolesToUser(s.ConfParams.GrantRolesToUser.Username, s.ConfParams.GrantRolesToUser.Roles)
	case "stop_dbmon":
		return s.doStopDbmon()
	case "start_dbmon":
		return s.doStartDbmon()
	case "stop":
		return op.DoStop()
	case "start":
		pid, running, err := op.IsRunning()
		if err != nil {
			return errors.Wrap(err, "IsRunning")
		}
		if running {
			s.runtime.Logger.Info("instance is running pid = %d , skip start", pid)
			return nil
		}
		return op.DoStart("auth")
	case "start_as_standalone":
		err := op.DoStop()
		if err != nil {
			return errors.Wrap(err, "DoStop")
		}
		return op.DoStartAsStandAlone()
	case "check_empty_data":
		_, err := op.DoCheckEmptyData()
		if err == nil {
			s.runtime.Logger.Info("is_empty_data: true")
		}
		return err
	case "show_tables":
		// 列出db简单信息. 未实现
		return errors.New("not implemented")
	}

	return errors.New("unknown op " + s.ConfParams.Op)
}

func (s *instOpJob) doStartDbmon() error {
	startSh := "/home/mysql/bk-dbmon/start.sh"
	_, _, _, err := mycmd.New(startSh).Run(time.Second * 60)
	if err != nil {
		return errors.Wrap(err, "start dbmon failed")
	}
	return nil
}

func (s *instOpJob) doStopDbmon() error {
	stopSh := "/home/mysql/bk-dbmon/stop.sh"
	_, _, _, err := mycmd.New(stopSh).Run(time.Second * 600)
	if err != nil {
		return errors.Wrap(err, "stop dbmon failed")
	}
	return nil
}

func (s *instOpJob) doInit() error {
	rsInfo := common.RsConf{}
	rsInfo.Id = s.ConfParams.SetName
	rsInfo.Hosts = append(rsInfo.Hosts, common.RsConfMember{
		Id:   0,
		Host: fmt.Sprintf("%s:%d", s.ConfParams.IP, s.ConfParams.Port),
	})
	rsInfo.Configsvr = strings.HasSuffix(s.ConfParams.SetName, "-conf")

	inst := common.NewInstance(s.ConfParams.IP, s.ConfParams.Port,
		s.ConfParams.AdminUsername, s.ConfParams.AdminPassword, "mongod")

	RsOpHandle := common.NewRsOp()
	out, err := RsOpHandle.Initiate(inst, &rsInfo, 120)
	s.runtime.Logger.Info("Initiate in: %+v, out: %+v, err:%v", &rsInfo, out, err)
	if err != nil || out.Ok != 1 {
		return errors.New("Initiate failed")
	}
	return nil
}

func (s *instOpJob) doRemoveOtherMember() error {
	op := s.GetInstanceOp()
	// 1. set myself as primary
	// if not primary, set myself as primary
	rsInfo, err := op.IsMaster()
	if err != nil {
		return errors.Wrap(err, "IsMaster")
	}
	if rsInfo.Primary == "" {
		return errors.New("no primary, maybe not a replica set")
	}
	s.runtime.Logger.Info("isMaster me:%s primary:%s", rsInfo.Me, rsInfo.Primary)
	RsOpHandle := common.NewRsOp()

	if !rsInfo.IsMaster {
		err = RsOpHandle.SetPriority(op.Instance, rsInfo.Me, 10)
		// wait for new primary
		// conf, err := RsOpHandle.GetRsConf(op.Instance)
		// s.runtime.Logger.Info("get rs conf %+v %v", conf, err)
		for i := 0; i < 10; i++ {
			rsInfo, err = op.IsMaster()
			if err != nil {
				return errors.Wrap(err, "IsMaster")
			}
			if rsInfo.Primary == rsInfo.Me {
				break
			}
			time.Sleep(2 * time.Second)
		}
	}
	conf, err := RsOpHandle.GetRsConf(op.Instance)
	if err != nil {
		return errors.Wrap(err, "GetRsConf")
	}
	s.runtime.Logger.Info("get rs conf %+v", conf)

	newHost := make([]common.RsConfMember, 0)
	for _, m := range conf.Config.Hosts {
		if m.Host == rsInfo.Me {
			newHost = append(newHost, m)
		}
	}
	conf.Config.Hosts = newHost
	out, err := RsOpHandle.ReConfig(op.Instance, &conf.Config, 120)
	if err != nil {
		s.runtime.Logger.Error("ReConfig val  %+v", &conf.Config)
		return errors.Wrap(err, "ReConfig")
	}
	if out.Ok != 1 {
		return errors.New("ReConfig failed")
	}
	time.Sleep(2)
	conf, err = RsOpHandle.GetRsConf(op.Instance)
	if err != nil {
		return errors.Wrap(err, "GetRsConf")
	}
	s.runtime.Logger.Info("get rs conf %+v", conf)
	if len(conf.Config.Hosts) == 1 {
		return nil
	} else {
		return errors.New("remove other member failed")
	}
	return nil
}

func (s *instOpJob) doAddMember() error {
	return nil
	// op := s.GetInstanceOp()
	// return op.DoAddMember()
}

func (s *instOpJob) GetInstanceOp() *common.InstanceOp {
	return common.NewInstanceOp(s.ConfParams.IP,
		s.ConfParams.Port,
		s.ConfParams.AdminUsername,
		s.ConfParams.AdminPassword,
		s.runtime.Logger,
	)
}

// Init 初始化
func (s *instOpJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.OsUser = ""
	if checkIsRootUser() {
		s.runtime.Logger.Error("This job cannot be executed as root user")
		return errors.New("This job cannot be executed as root user")
	}
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		tmpErr := errors.Wrap(err, "payload json.Unmarshal failed")
		s.runtime.Logger.Error(tmpErr.Error())
		return tmpErr
	}
	return nil
}
