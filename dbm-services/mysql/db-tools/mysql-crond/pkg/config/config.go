// Package config TODO
package config

import (
	"fmt"
	"os"
	"os/user"
	"strconv"

	"github.com/go-playground/validator/v10"
	"golang.org/x/exp/slog"
	"gopkg.in/yaml.v2"
)

// RuntimeConfig TODO
var RuntimeConfig *runtimeConfig

// JobsConfig TODO
var JobsConfig *jobsConfig

var jobsUser *user.User
var currentUser *user.User

// JobsUserUid TODO
var JobsUserUid int

// JobsUserGid TODO
var JobsUserGid int

var mysqlCrondEventName = "mysql-crond-event"

// InitConfig TODO
func InitConfig(configFilePath string) error {
	err := initConfig(configFilePath)
	if err != nil {
		return err
	}

	jobsUser, err = user.Lookup(RuntimeConfig.JobsUser)
	if err != nil {
		slog.Error("init runtimeConfig find jobs user", err)
		return err
	}

	JobsUserUid, _ = strconv.Atoi(jobsUser.Uid)
	JobsUserGid, _ = strconv.Atoi(jobsUser.Gid)

	currentUser, err = user.Current()
	if err != nil {
		slog.Error("init runtimeConfig get current user", err)
		return err
	}

	err = InitJobsConfig()
	if err != nil {
		return err
	}

	return nil
}

func initConfig(configFilePath string) error {
	content, err := os.ReadFile(configFilePath)
	if err != nil {
		slog.Error("init runtimeConfig", err)
		return err
	}

	RuntimeConfig = &runtimeConfig{}
	err = yaml.UnmarshalStrict(content, RuntimeConfig)
	if err != nil {
		slog.Error("init runtimeConfig", err)
		return err
	}

	validate := validator.New()
	err = validate.Struct(RuntimeConfig)
	if err != nil {
		panic(err)
	}

	return nil
}

// GetApiUrlFromConfig TODO
func GetApiUrlFromConfig(configFilePath string) (string, error) {
	if err := initConfig(configFilePath); err != nil {
		return "", err
	}
	return fmt.Sprintf(`http://127.0.0.1:%d`, RuntimeConfig.Port), nil
}
