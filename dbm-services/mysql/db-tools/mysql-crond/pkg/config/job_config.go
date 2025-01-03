package config

import (
	"bytes"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path"
	"syscall"

	"github.com/go-playground/validator/v10"
	"github.com/robfig/cron/v3"
	"gopkg.in/yaml.v2"
)

type jobsConfig struct {
	Jobs    []*ExternalJob `yaml:"jobs"`
	BkBizId int            `yaml:"bk_biz_id"`
	// ImmuteDomain string         `yaml:"immute_domain"`
	// MachineType  string         `yaml:"machine_type"`
	// Role         *string        `yaml:"role,omitempty"`
}

// ExternalJob TODO
type ExternalJob struct {
	Name     string   `yaml:"name" json:"name" binding:"required" validate:"required"`
	Enable   *bool    `yaml:"enable" json:"enable" binding:"required" validate:"required"`
	Command  string   `yaml:"command" json:"command" binding:"required" validate:"required"`
	Args     []string `yaml:"args" json:"args" binding:"required" validate:"required"`
	Schedule string   `yaml:"schedule" json:"schedule" binding:"required" validate:"required"`
	Creator  string   `yaml:"creator" json:"creator" binding:"required" validate:"required"`
	WorkDir  string   `yaml:"work_dir" json:"work_dir"`
	Overlap  bool     `yaml:"overlap" json:"overlap"` // 是否允许作业重叠执行, 默认 false
	// JobID 这个 id 主要用于追溯哪个 cron job (如果有) 调起本 external job
	JobID cron.EntryID `yaml:"-" json:"-"`
	ch    chan struct{}
}

func (j *ExternalJob) run() {
	cmd := exec.Command(j.Command, j.Args...)
	if j.WorkDir != "" {
		cmd.Dir = j.WorkDir
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if currentUser.Uid != jobsUser.Uid {
		cmd.SysProcAttr = &syscall.SysProcAttr{
			Credential: &syscall.Credential{
				Uid: uint32(JobsUserUid),
				Gid: uint32(JobsUserGid),
			},
		}
	}

	err := cmd.Run()
	if err != nil {
		slog.Error(
			"external job",
			slog.String("error", err.Error()),
			slog.String("name", j.Name),
			slog.String("stderr", stderr.String()),
		)
		err = SendEvent(
			mysqlCrondEventName,
			fmt.Sprintf(
				"execute job %s failed: %s [%s]",
				j.Name, err.Error(), stderr.String(),
			),
			map[string]interface{}{
				"job_name": j.Name,
			},
		)
		if err != nil {
			slog.Error("send event", slog.String("error", err.Error()))
		}
	} else {
		slog.Info(
			"external job",
			slog.String("name", j.Name),
			slog.String("stdout", stdout.String()),
		)
	}
}

// Run TODO
func (j *ExternalJob) Run() {
	slog.Info(
		"run job",
		slog.String("name", j.Name),
		slog.Bool("overlap", j.Overlap),
	)

	if j.Overlap {
		j.run()
	} else {
		select {
		case v := <-j.ch:
			j.run()
			j.ch <- v
		default:
			slog.Warn("skip job", slog.String("name", j.Name))
			err := SendEvent(
				mysqlCrondEventName,
				fmt.Sprintf("%s skipt for last round use too much time", j.Name),
				map[string]interface{}{
					"job_name": j.Name,
				},
			)
			if err != nil {
				slog.Error("send event", slog.String("error", err.Error()))
			}
		}
	}

	slog.Info("finish job", slog.String("name", j.Name))
}

// SetupChannel TODO
func (j *ExternalJob) SetupChannel( /*ip string*/ ) {
	j.ch = make(chan struct{}, 1)
	j.ch <- struct{}{}
}

func (j *ExternalJob) validate() error {
	validate := validator.New()
	return validate.Struct(j)
}

// InitJobsConfig TODO
func InitJobsConfig() error {
	if !path.IsAbs(RuntimeConfig.JobsConfigFile) {
		err := fmt.Errorf("jobs-config need absolute path")
		slog.Error("init jobs config", slog.String("error", err.Error()))
		return err
	}

	_, err := os.Stat(RuntimeConfig.JobsConfigFile)
	if err != nil {
		if os.IsNotExist(err) {
			slog.Info("init jobs config jobs-config file not found, try create it")
			_, err := os.Create(RuntimeConfig.JobsConfigFile)
			if err != nil {
				slog.Error("init jobs config create empty jobs-config file", slog.String("error", err.Error()))
				return err
			}

			err = os.Chown(RuntimeConfig.JobsConfigFile, JobsUserUid, JobsUserGid)
			if err != nil {
				slog.Error("init jobs config chown for jobs config", slog.String("error", err.Error()))
				return err
			}
		} else {
			slog.Error("init jobs config get jobs-config file stat", slog.String("error", err.Error()))
			return err
		}
	}

	content, err := os.ReadFile(RuntimeConfig.JobsConfigFile)
	if err != nil {
		slog.Error("init jobs config", slog.String("error", err.Error()))
		return err
	}

	JobsConfig = &jobsConfig{}
	err = yaml.Unmarshal(content, &JobsConfig)
	if err != nil {
		slog.Error("init jobs config", slog.String("error", err.Error()))
		return err
	}

	for _, j := range JobsConfig.Jobs {
		err := j.validate()
		if err != nil {
			panic(err)
		}

		if !j.Overlap {
			j.SetupChannel()
		}
	}
	return nil
}
