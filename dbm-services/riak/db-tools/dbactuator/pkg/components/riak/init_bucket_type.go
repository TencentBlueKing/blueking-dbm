// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
)

// InitBucketComp TODO
type InitBucketComp struct {
	Params *InitBucketParam `json:"extend"`
}

// InitBucketParam TODO
type InitBucketParam struct {
	BucketTypes *[]string `json:"bucket_types" validate:"required"`
}

// InitBucketType 初始化 bucket type
func (i *InitBucketComp) InitBucketType() error {
	basecmds := []string{
		"riak-admin bucket-type create ",
		"riak-admin bucket-type activate ",
		"riak-admin bucket-type status",
	}
	for _, bucket := range *i.Params.BucketTypes {
		for _, basecmd := range basecmds {
			cmd := fmt.Sprintf("%s %s", basecmd, bucket)
			res, err := osutil.ExecShellCommand(false, cmd)
			if err != nil {
				logger.Error("execute shell [%s] error: %s", cmd, err.Error())
				err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
				return err
			} else {
				logger.Info("execute shell [%s] output: %s", cmd, res)
			}
		}
	}
	if len(*i.Params.BucketTypes) > 0 {
		logger.Info("bucket type create success")
	} else {
		logger.Info("bucket type not needed, do nothing")
	}
	return nil
}
