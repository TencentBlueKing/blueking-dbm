package crond

import (
	"regexp"
	"slices"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-crond/pkg/config"

	"github.com/robfig/cron/v3"
)

// findEntry find active entry by  job name
func findEntry(name string) *cron.Entry {
	for _, entry := range ListEntry() {
		if j, ok := entry.Job.(*config.ExternalJob); !ok {
			continue
		} else {
			if j.Name == name {
				return &entry
			}
		}
	}
	return nil
}

func FindEntryByName(name string) *api.SimpleEntry {
	for _, entry := range ListEntry() {
		if j, ok := entry.Job.(*config.ExternalJob); !ok {
			continue
		} else {
			if j.Name == name {
				return &api.SimpleEntry{ID: int(entry.ID), Job: *j, Next: entry.Next}
			}
		}
	}
	return nil
}

// FindEntryByNameLike search jobs from active and disabled
// if nameMatch is empty, not use regex filter
// if all is true, check disable jobs too
func FindEntryByNameLike(nameMatch string, status string) ([]*api.SimpleEntry, error) {
	var entries []*api.SimpleEntry
	var entriesDisabled []*api.SimpleEntry
	var entriesSchedule []*api.SimpleEntry

	if status == "" {
		status = api.JobStatusEnabled + "," + api.JobStatusDisabled
	} else if status == api.JobStatusAll {
		status = api.JobStatusEnabled + "," + api.JobStatusDisabled + "," + api.JobStatusAll
	}
	statusList := strings.Split(status, ",")
	if nameMatch != "" && !strings.HasPrefix(nameMatch, "^") {
		nameMatch = "^" + nameMatch
	}
	if nameMatch != "" && !strings.HasSuffix(nameMatch, "$") {
		nameMatch = nameMatch + "$"
	}
	regMatch, err := regexp.Compile(nameMatch)
	if err != nil {
		return nil, errors.WithMessagef(err, "invalid regex `%s`", nameMatch)
	}

	if slices.Contains(statusList, api.JobStatusEnabled) {
		for _, entry := range ListEntry() {
			if j, ok := entry.Job.(*config.ExternalJob); !ok {
				if j, ok := entry.Job.(*config.ScheduleJob); ok {
					if nameMatch == "" {
						entriesSchedule = append(entriesSchedule,
							&api.SimpleEntry{ID: int(entry.ID), Job: j.WrappedJob, Next: entry.Next})
					}
				} else {
					continue
				}
			} else {
				if nameMatch == "" {
					entries = append(entries, &api.SimpleEntry{ID: int(entry.ID), Job: *j, Next: entry.Next})
				} else if regMatch.MatchString(j.Name) {
					entries = append(entries, &api.SimpleEntry{ID: int(entry.ID), Job: *j, Next: entry.Next})
				}
			}
		}
	}

	if slices.Contains(statusList, api.JobStatusDisabled) || slices.Contains(statusList, api.JobStatusAll) {
		for _, j := range ListDisabledJob() {
			if nameMatch == "" {
				entriesDisabled = append(entriesDisabled, &api.SimpleEntry{ID: -1, Job: *j})
			} else if regMatch.MatchString(j.Name) {
				entriesDisabled = append(entriesDisabled, &api.SimpleEntry{ID: -1, Job: *j})
			}
		}
		if slices.Contains(statusList, api.JobStatusAll) {
			entries = append(entries, entriesSchedule...)
			entries = append(entries, entriesDisabled...)
		} else {
			for _, se := range entriesSchedule {
				for _, e := range entriesDisabled {
					pauseJobName := e.Job.Name + config.PauseJobSuffix
					if se.Job.Name == pauseJobName {
						e.Next = se.Next
					}
				}
			}
			entries = append(entries, entriesDisabled...)
		}
	}
	return entries, nil
}
