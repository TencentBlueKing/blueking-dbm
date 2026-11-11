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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/handler"

	"github.com/spf13/cobra"
)

func newImportCmd(a *app) *cobra.Command {
	importCmd := &cobra.Command{
		Use:   cmdUseImport,
		Short: cmdShortImport,
		Long:  cmdLongImport,
		RunE: func(cmd *cobra.Command, args []string) error {
			if xlsxFlagsChanged(cmd) {
				xlsxOpts, err := newXlsxTemplateOptions(cmd)
				if err != nil {
					return err
				}

				return handler.CreateImportTemplateFromXlsx(xlsxOpts)
			}

			opts, err := newImportOptions(cmd)
			if err != nil {
				return err
			}

			return a.withHandler(func(h *handler.Handler) error {
				return h.Import(opts)
			})
		},
	}

	importCmd.Flags().String(flagFile, defaultStringValue, flagUsageImportFile)
	importCmd.Flags().String(flagCreateTmpl, defaultStringValue, flagUsageCreateTmpl)
	importCmd.Flags().String(flagCreateTmplFromList, defaultStringValue, flagUsageCreateTmplFromList)
	importCmd.Flags().Bool(flagDryRun, defaultFalseValue, flagUsageDryRun)
	importCmd.Flags().Bool(flagUpsert, defaultFalseValue, flagUsageUpsert)
	importCmd.Flags().Bool(flagYes, defaultFalseValue, flagUsageYesRisky)
	importCmd.Flags().String(flagCreateTmplFromXlsx, defaultStringValue, flagUsageCreateTmplFromXlsx)
	importCmd.Flags().String(flagXlsxFile, defaultStringValue, flagUsageXlsxFile)
	importCmd.Flags().Int(flagXlsxBkBizID, defaultIntValue, flagUsageXlsxBkBizID)
	importCmd.Flags().String(flagXlsxSwitchVersion, defaultSwitchVersion, flagUsageXlsxSwitchVersion)
	importCmd.Flags().String(flagXlsxStatus, defaultStatus, flagUsageXlsxStatus)
	importCmd.Flags().String(flagXlsxReport, defaultStringValue, flagUsageXlsxReport)

	return importCmd
}

func xlsxFlagNames() []string {
	return []string{
		flagCreateTmplFromXlsx,
		flagXlsxFile,
		flagXlsxBkBizID,
		flagXlsxSwitchVersion,
		flagXlsxStatus,
		flagXlsxReport,
	}
}

func xlsxFlagsChanged(cmd *cobra.Command) bool {
	for _, name := range xlsxFlagNames() {
		if cmd.Flags().Changed(name) {
			return true
		}
	}

	return false
}

func newXlsxTemplateOptions(cmd *cobra.Command) (handler.XlsxTemplateOptions, error) {
	output, err := cmd.Flags().GetString(flagCreateTmplFromXlsx)
	if err != nil {
		return handler.XlsxTemplateOptions{}, err
	}
	if output == "" {
		return handler.XlsxTemplateOptions{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxFlagsRequireTemplate)
	}

	createTemplate, err := cmd.Flags().GetString(flagCreateTmpl)
	if err != nil {
		return handler.XlsxTemplateOptions{}, err
	}

	createTemplateFromList, err := cmd.Flags().GetString(flagCreateTmplFromList)
	if err != nil {
		return handler.XlsxTemplateOptions{}, err
	}

	if err := handler.ValidateImportTemplateFlags(createTemplate, createTemplateFromList, output); err != nil {
		return handler.XlsxTemplateOptions{}, err
	}

	opts := handler.XlsxTemplateOptions{
		Output:     output,
		BkBizIDSet: cmd.Flags().Changed(flagXlsxBkBizID),
		Out:        cmd.OutOrStdout(),
	}
	if opts.XlsxFile, err = cmd.Flags().GetString(flagXlsxFile); err != nil {
		return handler.XlsxTemplateOptions{}, err
	}
	if opts.BkBizID, err = cmd.Flags().GetInt(flagXlsxBkBizID); err != nil {
		return handler.XlsxTemplateOptions{}, err
	}
	if opts.SwitchVersion, err = cmd.Flags().GetString(flagXlsxSwitchVersion); err != nil {
		return handler.XlsxTemplateOptions{}, err
	}
	if opts.Status, err = cmd.Flags().GetString(flagXlsxStatus); err != nil {
		return handler.XlsxTemplateOptions{}, err
	}
	if opts.Report, err = cmd.Flags().GetString(flagXlsxReport); err != nil {
		return handler.XlsxTemplateOptions{}, err
	}

	return opts, nil
}

func newImportOptions(cmd *cobra.Command) (handler.ImportOptions, error) {
	file, err := cmd.Flags().GetString(flagFile)
	if err != nil {
		return handler.ImportOptions{}, err
	}

	createTemplate, err := cmd.Flags().GetString(flagCreateTmpl)
	if err != nil {
		return handler.ImportOptions{}, err
	}

	createTemplateFromList, err := cmd.Flags().GetString(flagCreateTmplFromList)
	if err != nil {
		return handler.ImportOptions{}, err
	}

	dryRun, err := cmd.Flags().GetBool(flagDryRun)
	if err != nil {
		return handler.ImportOptions{}, err
	}

	upsert, err := cmd.Flags().GetBool(flagUpsert)
	if err != nil {
		return handler.ImportOptions{}, err
	}

	yes, err := cmd.Flags().GetBool(flagYes)
	if err != nil {
		return handler.ImportOptions{}, err
	}

	return handler.ImportOptions{
		File:                   file,
		CreateTemplate:         createTemplate,
		CreateTemplateFromList: createTemplateFromList,
		DryRun:                 dryRun,
		Upsert:                 upsert,
		Yes:                    yes,
		Confirm:                confirm,
	}, nil
}
