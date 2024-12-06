package backupexe

import (
	"regexp"
	"strings"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"gopkg.in/ini.v1"
)

// https://github.com/mydumper/mydumper/blob/master/README.md#defaults-file
/*
[mydumper_session_variables]
wait_timeout = 300
sql_mode = ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION

[mydumper_global_variables]
sync_binlog = 0
slow_query_log = OFF

[myloader_session_variables]
long_query_time = 300

[myloader_global_variables]
sync_binlog = 0
innodb_flush_log_at_trx_commit = 0
*/

type MydumperIni struct {
	MydumperSessionVariables map[string]interface{}
	MydumperGlobalVariables  map[string]interface{}
	MyloaderSessionVariables map[string]interface{}
	MyloaderGlobalVariables  map[string]interface{}
}

func (i *MydumperIni) SaveIni(fileName string) error {
	f := ini.Empty()
	var err error
	if i.MydumperSessionVariables != nil {
		section, _ := f.NewSection("mydumper_session_variables")
		for k, v := range i.MydumperSessionVariables {
			section.NewKey(k, cast.ToString(v))
		}
	}
	if i.MydumperGlobalVariables != nil {
		section, _ := f.NewSection("mydumper_global_variables")
		for k, v := range i.MydumperGlobalVariables {
			section.NewKey(k, cast.ToString(v))
		}
	}
	if i.MyloaderSessionVariables != nil {
		section, _ := f.NewSection("myloader_session_variables")
		for k, v := range i.MyloaderSessionVariables {
			section.NewKey(k, cast.ToString(v))
		}
	}
	if i.MyloaderGlobalVariables != nil {
		section, _ := f.NewSection("myloader_global_variables")
		for k, v := range i.MyloaderGlobalVariables {
			section.NewKey(k, cast.ToString(v))
		}
	}
	if err = f.SaveTo(fileName); err != nil {
		return errors.Wrap(err, "create mydumper defaults-file config")
	}
	return nil
}

// SetVariablesToConfigIni return session, global variables from "set global xxx=0; set session yyy='aa'"
func SetVariablesToConfigIni(s string) (map[string]interface{}, map[string]interface{}) {
	//reSpaceSquash := regexp.MustCompile(`\s+`)
	//s = reSpaceSquash.ReplaceAllString(s, " ")
	setVars := strings.Split(s, ";")
	reSetGlobal := regexp.MustCompile(`(?i)(set\s+global\s+)(\w+)\s*=\s*(.*)`)
	reSetSession := regexp.MustCompile(`(?i)(set\s+session\s+)(\w+)\s*=\s*(.*)`)
	reSet := regexp.MustCompile(`(?i)(set\s+)(\w+)\s*=\s*(.*)`)

	var sessionVars = make(map[string]interface{})
	var globalVars = make(map[string]interface{})
	for _, setVar := range setVars {
		setVar = strings.TrimSpace(setVar)
		if setVar == "" {
			continue
		}
		if m := reSetSession.FindStringSubmatch(setVar); len(m) == 4 {
			sessionVars[m[2]] = m[3]
		} else if m := reSet.FindStringSubmatch(setVar); len(m) == 4 {
			sessionVars[m[2]] = m[3]
		} else if m := reSetGlobal.FindStringSubmatch(setVar); len(m) == 4 {
			globalVars[m[2]] = m[3]
		}
	}
	return sessionVars, globalVars
}
