/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package switchcore

import (
	"context"
	"errors"
	"fmt"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

func checkBeforeSwitch(ins SwitchableInstance) (checkResult SwitchCheckCode, retErr error) {
	checkRes, checkErr := ins.CheckBeforeSwitch()

	switch checkRes {
	case SwitchRequired:
		ins.ReportLogf(switchlogger.SwitchInfo, "check result before switch: switch required")

	case SwitchNotNeeded:
		ins.ReportLogf(switchlogger.SwitchInfo, "check result before switch: no need to switch")

	default:
		errMsg := "check result before switch: check unpass"
		if checkErr != nil {
			errMsg += fmt.Sprintf(", errmsg: %s", checkErr.Error())
		}

		ins.ReportLogf(switchlogger.SwitchError, "%s", errMsg)
		retErr = gerrors.Newf(gerrors.Failure, "%s", errMsg)
	}

	return checkRes, retErr
}

// errIfCtxDoneInInstanceSwitch returns the error if ctx is non-nil
// and the context is canceled or expired, otherwise nil.
func errIfCtxDoneInInstanceSwitch(ctx context.Context, ins SwitchableInstance) error {
	if ctx == nil {
		return nil
	}

	if err := ctx.Err(); err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			ins.ReportLogf(switchlogger.SwitchError, "switching timeout: %s", err.Error())
			return err
		}

		ins.ReportLogf(switchlogger.SwitchError, "switching context done: %s", err.Error())
		return err
	}

	return nil
}

// checkStatusForInstanceSwitch validates instance status before switching.
func checkStatusForInstanceSwitch(ctx context.Context, ins SwitchableInstance) error {
	if err := errIfCtxDoneInInstanceSwitch(ctx, ins); err != nil {
		return err
	}

	if (ins.GetStatus() != dbm.Running) && (ins.GetStatus() != dbm.Available) {
		retErr := gerrors.Newf(gerrors.Failure, "pre-status check unpass for wrong status:%s", ins.GetStatus())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "pre-status check pass with status:%s", ins.GetStatus())
	return nil
}

// setStatusForInstanceSwitch sets the instance unavailable for switching.
func setStatusForInstanceSwitch(ctx context.Context, ins SwitchableInstance) error {
	if err := errIfCtxDoneInInstanceSwitch(ctx, ins); err != nil {
		return err
	}

	if err := ins.SetInstanceUnavailable(); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to set instance unavailable: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully set instance unavailable")
	return nil
}

// doCheckBeforeInstanceSwitch runs checkBeforeSwitch with ctx guard.
func doCheckBeforeInstanceSwitch(ctx context.Context, ins SwitchableInstance) (SwitchCheckCode, error) {
	if err := errIfCtxDoneInInstanceSwitch(ctx, ins); err != nil {
		return SwitchCheckUnpass, err
	}

	return checkBeforeSwitch(ins)
}

// doSwitchInInstanceSwitch invokes DoSwitch after ctx guard.
func doSwitchInInstanceSwitch(ctx context.Context, ins SwitchableInstance) error {
	if err := errIfCtxDoneInInstanceSwitch(ctx, ins); err != nil {
		return err
	}

	if err := ins.DoSwitch(); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to do switch: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully do switch")
	return nil
}

// doUpdateMetaInfoInInstanceSwitch invokes UpdateMetaInfo after ctx guard.
func doUpdateMetaInfoInInstanceSwitch(ctx context.Context, ins SwitchableInstance) error {
	if err := errIfCtxDoneInInstanceSwitch(ctx, ins); err != nil {
		return err
	}

	if err := ins.UpdateMetaInfo(); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to update meta info: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully update meta info")
	return nil
}

// doFinalInInstanceSwitch invokes DoFinal after ctx guard.
func doFinalInInstanceSwitch(ctx context.Context, ins SwitchableInstance) error {
	if err := errIfCtxDoneInInstanceSwitch(ctx, ins); err != nil {
		return err
	}

	if err := ins.DoFinal(); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to do final step: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully do final step")
	return nil
}

// SwitchSingleInstance executes the standardized switching procedure for a single database instance.
func SwitchSingleInstance(ctx context.Context, ins SwitchableInstance) (switchSuccess bool, retErr error) {
	ins.ReportLogf(switchlogger.SwitchInfo, "start to switch single instance: %s", ins.GetInstanceInfo())

	// rollback when error occurs
	defer func() {
		if switchSuccess {
			ins.ReportLogf(switchlogger.SwitchInfo, "successfully switch single instance: %s", ins.GetInstanceInfo())
			return
		}

		if retErr == nil {
			retErr = gerrors.New(gerrors.Failure, "unknown error occurred")
		}

		ins.ReportLogf(switchlogger.SwitchError, "failed to switch single instance: %s", ins.GetInstanceInfo())

		if rollbackErr := ins.RollBack(); rollbackErr != nil {
			ins.ReportLogf(switchlogger.SwitchError, "failed to rollback switch: %s", rollbackErr.Error())
			retErr = gerrors.Newf(gerrors.Failure, "switch errmsg: %s, rollback errmsg: %s",
				retErr.Error(), rollbackErr.Error())
		}
	}()

	if err := checkStatusForInstanceSwitch(ctx, ins); err != nil {
		return false, err
	}

	if err := setStatusForInstanceSwitch(ctx, ins); err != nil {
		return false, err
	}

	if err := errIfCtxDoneInInstanceSwitch(ctx, ins); err != nil {
		return false, err
	}

	// lock the cluster that the instance belongs to
	clusterKey := GenerateClusterKey(ins.GetBkCloudID(), ins.GetClusterID())
	unlock, lockErr := LockClusterWithTimeout(ins.ReportLogf, clusterKey, ClusterLockTimeout())
	if lockErr != nil {
		retErr = lockErr
		return false, retErr
	}
	defer unlock()

	checkRes, checkErr := doCheckBeforeInstanceSwitch(ctx, ins)
	if checkRes == SwitchCheckUnpass {
		return false, checkErr
	}

	if checkRes == SwitchNotNeeded {
		return true, checkErr
	}

	if err := doSwitchInInstanceSwitch(ctx, ins); err != nil {
		return false, err
	}

	if err := doUpdateMetaInfoInInstanceSwitch(ctx, ins); err != nil {
		return false, err
	}

	if err := doFinalInInstanceSwitch(ctx, ins); err != nil {
		return false, err
	}

	return true, nil
}
