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

package main

import (
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/handler"

	"github.com/spf13/cobra"
)

func newUpdateCmd(a *app) *cobra.Command {
	updateCmd := &cobra.Command{
		Use:   cmdUseUpdate,
		Short: cmdShortUpdate,
		Long:  cmdLongUpdate,
		RunE: func(cmd *cobra.Command, args []string) error {
			opts, err := newUpdateOptions(cmd)
			if err != nil {
				return err
			}

			return a.withHandler(func(h *handler.Handler) error {
				return h.Update(opts)
			})
		},
	}

	updateCmd.Flags().Int(flagID, defaultIntValue, flagUsageEntryID)
	updateCmd.Flags().Int(flagBkBizID, defaultIntValue, flagUsageBizID)
	updateCmd.Flags().Int(flagBkCloudID, defaultIntValue, flagUsageCloudID)
	updateCmd.Flags().Int(flagClusterID, defaultIntValue, flagUsageClusterID)
	updateCmd.Flags().String(flagClusterName, defaultStringValue, flagUsageClusterName)
	updateCmd.Flags().String(flagSetClusterName, defaultStringValue, flagUsageSetClusterName)
	updateCmd.Flags().String(flagSwitchVersion, defaultStringValue, flagUsageSwitchVersion)
	updateCmd.Flags().String(flagStatus, defaultStringValue, flagUsageStatus)
	updateCmd.Flags().Bool(flagYes, defaultFalseValue, flagUsageYesRisky)

	return updateCmd
}

func newUpdateOptions(cmd *cobra.Command) (handler.UpdateOptions, error) {
	id, err := cmd.Flags().GetInt(flagID)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	bkBizID, err := cmd.Flags().GetInt(flagBkBizID)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	bkCloudID, err := cmd.Flags().GetInt(flagBkCloudID)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	clusterID, err := cmd.Flags().GetInt(flagClusterID)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	clusterName, err := cmd.Flags().GetString(flagClusterName)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	setClusterName, err := cmd.Flags().GetString(flagSetClusterName)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	switchVersion, err := cmd.Flags().GetString(flagSwitchVersion)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	status, err := cmd.Flags().GetString(flagStatus)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	yes, err := cmd.Flags().GetBool(flagYes)
	if err != nil {
		return handler.UpdateOptions{}, err
	}

	return handler.UpdateOptions{
		ID:             id,
		BkBizID:        bkBizID,
		BkCloudID:      bkCloudID,
		ClusterID:      clusterID,
		ClusterName:    clusterName,
		SetClusterName: setClusterName,
		SwitchVersion:  switchVersion,
		Status:         status,
		Yes:            yes,
		Confirm:        confirm,
	}, nil
}
