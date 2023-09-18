package externalhandler

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
	"gopkg.in/yaml.v2"

	"celery-service/pkg/config"
)

type externalItem struct {
	Name        string   `yaml:"name" validate:"required"`
	ClusterType string   `yaml:"cluster_type" validate:"required"`
	Language    string   `yaml:"language" validate:"required,oneof=python python2 python3 perl sh bash binary"`
	Executable  string   `yaml:"executable" validate:"required"`
	Args        []string `yaml:"args"`
	Collected   *bool    `yaml:"collected" validate:"required"`
}

var externalItems []*externalItem

func LoadExternal(filePath string) error {
	content, err := os.ReadFile(filePath)
	if err != nil {
		logger.Error("read external task config", slog.String("error", err.Error()))
		return err
	}

	err = yaml.Unmarshal(content, &externalItems)
	if err != nil {
		logger.Error("unmarshal external task config", slog.String("error", err.Error()))
		return err
	}

	validate := validator.New()

	for _, ei := range externalItems {

		// validate
		err := validate.Struct(ei)
		if err != nil {
			logger.Error("validate external task", slog.Any(ei.Name, ei), slog.String("error", err.Error()))
			return errors.Wrap(err, fmt.Sprintf("validate %v", ei))
		}

		if *ei.Collected {
			splitExecutable := strings.Split(ei.Executable, " ")
			if filepath.IsAbs(splitExecutable[0]) {
				err := errors.Errorf("absolute path not allowed: %s", ei.Executable)
				logger.Error("load external", slog.String("error", err.Error()))
				return err
			}

			splitExecutable[0] = filepath.Join(config.CollectDir, splitExecutable[0])
			ei.Executable = strings.Join(splitExecutable, " ")
		}
	}
	return nil
}
