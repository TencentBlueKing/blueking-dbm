package checker

import (
	"fmt"
	"os"
	"strings"

	"golang.org/x/exp/slog"
)

func (r *Checker) ptPrecheck() error {
	if _, err := os.Stat(r.Config.PtChecksum.Path); err != nil {
		slog.Error("pt pre check", err)
		return err
	}
	return nil
}

func (r *Checker) buildCommandArgs() {
	r.args = append(r.args, r.ptArgsFilters()...)
	r.args = append(r.args, r.ptArgsConnectInfo()...)
	r.args = append(r.args, r.ptArgsReplicate()...)
	r.args = append(r.args, r.ptArgsSwitches()...)
	r.args = append(r.args, r.ptArgsKV()...)
}

func (r *Checker) ptArgsFilters() []string {
	var res []string

	if len(r.Config.Filter.Databases) > 0 {
		res = append(
			res, []string{
				fmt.Sprintf("--databases=%s", strings.Join(r.Config.Filter.Databases, ",")),
			}...,
		)
	}
	if len(r.Config.Filter.Tables) > 0 {
		res = append(
			res, []string{
				fmt.Sprintf("--tables=%s", strings.Join(r.Config.Filter.Tables, ",")),
			}...,
		)
	}
	if len(r.Config.Filter.IgnoreDatabases) > 0 {
		res = append(
			res, []string{
				fmt.Sprintf("--ignore-databases=%s", strings.Join(r.Config.Filter.IgnoreDatabases, ",")),
			}...,
		)
	}
	if len(r.Config.Filter.IgnoreTables) > 0 {
		res = append(
			res, []string{
				fmt.Sprintf("--ignore-tables=%s", strings.Join(r.Config.Filter.IgnoreTables, ",")),
			}...,
		)
	}
	if r.Config.Filter.DatabasesRegex != "" {
		res = append(
			res, []string{
				fmt.Sprintf("--databases-regex=%s", r.Config.Filter.DatabasesRegex),
			}...,
		)
	}
	if r.Config.Filter.TablesRegex != "" {
		res = append(
			res, []string{
				fmt.Sprintf("--tables-regex=%s", r.Config.Filter.TablesRegex),
			}...,
		)
	}
	if r.Config.Filter.IgnoreDatabasesRegex != "" {
		res = append(
			res, []string{
				fmt.Sprintf("--ignore-databases-regex=%s", r.Config.Filter.IgnoreDatabasesRegex),
			}...,
		)
	}
	if r.Config.Filter.IgnoreTablesRegex != "" {
		res = append(
			res, []string{
				fmt.Sprintf("--ignore-tables-regex=%s", r.Config.Filter.IgnoreTablesRegex),
			}...,
		)
	}
	return res
}

func (r *Checker) ptArgsConnectInfo() []string {
	return []string{
		fmt.Sprintf("--host=%s", r.Config.Ip),
		fmt.Sprintf("--port=%d", r.Config.Port),
		fmt.Sprintf("--user=%s", r.Config.User),
		fmt.Sprintf("--password=%s", r.Config.Password),
	}
}

func (r *Checker) ptArgsReplicate() []string {
	return []string{
		fmt.Sprintf("--replicate=%s", r.Config.PtChecksum.Replicate),
	}
}

func (r *Checker) ptArgsSwitches() []string {
	var res []string
	for _, sw := range r.Config.PtChecksum.Switches {
		res = append(res, fmt.Sprintf(`--%s`, sw))
	}
	return res
}

func (r *Checker) ptArgsKV() []string {
	var res []string
	for _, arg := range r.Config.PtChecksum.Args {
		key := arg["name"]
		value := arg["value"]
		switch value := value.(type) {
		case int:
			res = append(res, fmt.Sprintf(`--%s=%d`, key, value))
		default:
			res = append(res, fmt.Sprintf(`--%s=%s`, key, value))
		}
	}
	return res
}
