package config

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"golang.org/x/exp/slices"
	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"
	"gopkg.in/yaml.v2"
)

type ExternalTask struct {
	Name         string   `yaml:"name" validate:"required"`
	ClusterType  string   `yaml:"cluster_type" validate:"required"`
	Language     string   `yaml:"language" validate:"required,oneof=python python2 python3 perl sh bash binary"`
	Executable   string   `yaml:"executable" validate:"required"`
	Args         []string `yaml:"args"`
	Collected    *bool    `yaml:"collected" validate:"required"`
	Logger       *slog.Logger
	LatestStderr string
	LatestStdout string
}

var ExternalTasks []*ExternalTask

func LoadExternalTasks(externalTaskConfigFilePath string) error {
	content, err := os.ReadFile(externalTaskConfigFilePath)
	if err != nil {
		return err
	}

	err = yaml.Unmarshal(content, &ExternalTasks)
	if err != nil {
		return err
	}

	validate := validator.New()

	for idx, et := range ExternalTasks {
		// 重名检查
		var leftTasks []*ExternalTask
		leftTasks = append(leftTasks, ExternalTasks[:idx]...)
		leftTasks = append(leftTasks, ExternalTasks[idx+1:]...)

		dup := slices.ContainsFunc(
			leftTasks,
			func(t *ExternalTask) bool {
				return t.Name == et.Name
			})

		if dup {
			return errors.Errorf("duplicate name found: %s", et.Name)
		}

		// validate
		err := validate.Struct(et)
		if err != nil {
			return errors.Wrap(err, fmt.Sprintf("validate %v", et))
		}

		if *et.Collected {
			splitExecutable := strings.Split(et.Executable, " ")
			if filepath.IsAbs(splitExecutable[0]) {
				return fmt.Errorf("absolute path not allowed: %s", et.Executable)
			}

			splitExecutable[0] = filepath.Join(BaseDir, "collect", splitExecutable[0])
			et.Executable = strings.Join(splitExecutable, " ")
		}

		err = os.MkdirAll(filepath.Join(BaseDir, "logs"), 0755)
		if err != nil {
			return err
		}

		et.Logger = slog.New(
			slog.NewTextHandler(
				io.MultiWriter(
					&lumberjack.Logger{
						Filename: filepath.Join(
							BaseDir, "logs",
							strings.ToLower(et.Name),
							fmt.Sprintf("%s.log", strings.ToLower(et.Name))),
						MaxSize:    100,
						MaxAge:     30,
						MaxBackups: 50,
					},
					os.Stdout,
				),
				&slog.HandlerOptions{
					AddSource: true,
				},
			),
		).With("name", et.Name)
	}

	return nil
}
