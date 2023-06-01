package commoncmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"
)

// RMLargeFileCmd TODO
type RMLargeFileCmd struct {
	*subcmd.BaseOptions
	Payload RMLargeFileParam
}

// RMLargeFileParam TODO
type RMLargeFileParam struct {
	Filename string `json:"filename" validate:"required"`
	// 删除速度，MB/s，默认 30
	BWLimitMB int `json:"bw_limit_mb" validate:"required,gte=1,lte=1000" default:"30"`
}

// Example TODO
func (p RMLargeFileParam) Example() interface{} {
	comp := RMLargeFileParam{
		Filename:  "xxx",
		BWLimitMB: 30,
	}
	return comp
}

// PreCheck TODO
func (p RMLargeFileParam) PreCheck() error {
	if !cmutil.FileExists(p.Filename) {
		return errors.Errorf("file not exists %s", p.Filename)
	} else if cmutil.IsDirectory(p.Filename) {
		return errors.Errorf("path is directory %s", p.Filename)
	}
	if p.BWLimitMB == 0 {
		p.BWLimitMB = 30
	}
	// writable?
	return nil
}

// Start TODO
func (p RMLargeFileParam) Start() error {
	if err := cmutil.TruncateFile(p.Filename, p.BWLimitMB); err != nil {
		logger.Error(errors.WithStack(err).Error())
		return err
	}
	return nil
}

// RMLargeFileCommand godoc
//
// @Summary      限速删除大文件
// @Tags         common
// @Accept       json
// @Param        body body      RMLargeFileParam  true  "short description"
// @Router       /common/rm-file [post]
func RMLargeFileCommand() *cobra.Command {
	act := RMLargeFileCmd{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "rm-file",
		Short: "限速删除大文件",
		Example: fmt.Sprintf(
			`dbactuator common rm-file %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *RMLargeFileCmd) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
		return err
	}
	if err = d.DeserializeSimple(&d.Payload); err != nil {
		logger.Error("DeserializeSimple err %s", err.Error())
		return err
	}
	return
}

// Validate TODO
func (d *RMLargeFileCmd) Validate() error {
	return nil
}

// Run TODO
func (d *RMLargeFileCmd) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "删除",
			Func:    d.Payload.Start,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("rm file %s successfully", d.Payload.Filename)
	return nil
}
