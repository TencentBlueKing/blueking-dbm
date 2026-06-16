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

func newImportCmd(a *app) *cobra.Command {
	importCmd := &cobra.Command{
		Use:   cmdUseImport,
		Short: cmdShortImport,
		Long:  cmdLongImport,
		RunE: func(cmd *cobra.Command, args []string) error {
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

	return importCmd
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
